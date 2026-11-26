from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError
import argparse, json, sqlite3, threading, webbrowser, os
from contextlib import closing
import memory_graph
import soul_core
import soul_chronicle
import time, re
import base64, binascii

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "hakureya.sqlite3"
API = "https://foundation-models.api.cloud.ru/v1/chat/completions"
LOCK = threading.Lock()
CONFIG = {"key": "", "model": ""}
CHRONICLE = {"enabled": False, "last_activity": time.monotonic(), "epoch": 0}


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=10)
    db.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, role TEXT NOT NULL, content TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP)")
    memory_graph.init(db)
    soul_core.init(db)
    db.commit()
    return db

def history(limit=200):
    with closing(connect()) as db:
        rows = db.execute("SELECT role,content FROM messages ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [{"role": r, "content": c} for r,c in reversed(rows)]

def store(role, content):
    with closing(connect()) as db, db:
        cursor = db.execute("INSERT INTO messages(role,content) VALUES(?,?)", (role,content))
        message_id = cursor.lastrowid
        if role == "user":
            soul_core.observe_user(db,message_id,content)
        elif role == "assistant":
            soul_core.review_response(db,message_id,content)
            soul_chronicle.collect(db)
        return message_id

def generate_chronicle(background=False):
    # Reserve quota and snapshot under lock; do not block chat during network I/O.
    with LOCK:
        if not CONFIG["key"] or (background and (not CHRONICLE["enabled"] or time.monotonic()-CHRONICLE["last_activity"]<1200)):
            return "Cloud.ru не подключён или фоновый сон не разрешён."
        with closing(connect()) as db, db:
            soul_chronicle.collect(db)
            reservation=soul_chronicle.reserve(db)
            traits=soul_chronicle.profile(db)
        if not reservation:
            return "Нет новой записи дневника, есть ожидающий черновик, нарушена целостность канона или исчерпан дневной лимит."
        key, model, epoch=CONFIG["key"],CONFIG["model"],CHRONICLE["epoch"]
    try:
        payload={"model":model,"messages":soul_chronicle.prompt(reservation,traits),"max_tokens":1800,"stream":False}
        req=Request(API,data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
        with urlopen(req,timeout=60) as res:
            result=json.loads(res.read(1_000_000))
        raw=result["choices"][0]["message"]["content"]
        if not isinstance(raw,str) or len(raw)>24000:
            raise ValueError("invalid draft")
        value=json.loads(raw)
        with LOCK, closing(connect()) as db, db:
            if CHRONICLE["epoch"]!=epoch:
                soul_chronicle.fail(db,reservation)
                return "Настройки изменились; черновик отброшен."
            soul_chronicle.finish(db,reservation,value)
        return "Черновик создан. Введите «летопись: черновик» для чтения и решения."
    except (URLError,TimeoutError,ValueError,KeyError,IndexError,TypeError,OSError,sqlite3.Error):
        with LOCK, closing(connect()) as db, db:
            soul_chronicle.fail(db,reservation)
        return "Черновик не создан: ответ модели не прошёл проверку или запрос завершился ошибкой. Дневная попытка учтена."

def chronicle_command(content):
    q=content.strip().casefold()
    decision=re.fullmatch(r"летопись: (принять|отклонить) ([1-9][0-9]{0,8})",q)
    if q not in soul_chronicle.COMMANDS and not decision and q!="летопись: главы":
        return None
    if q=="летопись: создать":
        with LOCK, closing(connect()) as db, db:
            soul_chronicle.control(db,"manual_request")
        return generate_chronicle()
    with LOCK, closing(connect()) as db, db:
        if q=="летопись: включить сон":
            if not CONFIG["key"]:
                return "Сначала подключите Cloud.ru. Сон не включён."
            CHRONICLE.update(enabled=True,epoch=CHRONICLE["epoch"]+1)
            soul_chronicle.control(db,"background_enabled")
            return "Сон включён до закрытия сервера: не чаще одной попытки UTC в сутки, после 20 минут тишины, только при новой записи дневника. В Cloud.ru передаются канон и счётчики, не текст чата. Отключение: летопись: выключить сон."
        if q=="летопись: выключить сон":
            CHRONICLE.update(enabled=False,epoch=CHRONICLE["epoch"]+1)
            soul_chronicle.control(db,"background_disabled")
            return "Сон отключён. Уже начатый сетевой запрос может завершиться, но его черновик будет отброшен."
        if decision:
            i=int(decision[2])
            try:
                ok=soul_chronicle.decide(db,i,decision[1]=="принять")
            except ValueError:
                ok=False
            return "Решение сохранено." if ok else "Черновик не найден, повреждён или уже обработан."
        if q=="летопись: дневник":
            return soul_chronicle.diary_text(db)
        if q=="летопись: черновик":
            try:
                p=soul_chronicle.latest_pending(db)
            except ValueError:
                return "Черновик повреждён; публикация заблокирована."
            if not p:
                return "Нет ожидающего черновика."
            return f"Художественный черновик №{p['id']}: {p['title']}\n\n{p['story']}\n\nМодельные эмоции: {p['emotions']}\nПредлагаемые изменения характера: {p['traits']}\n\nлетопись: принять {p['id']} / летопись: отклонить {p['id']}"
        if q=="летопись: главы":
            rows=soul_chronicle.approved(db,5)
            return "\n\n".join(f"Вымышленная глава №{p['id']}: {p['title']}\n{p['story']}" for p in rows) or "Новых утверждённых глав пока нет."
        st=soul_chronicle.status(db)
        return f"Канон: {st['canon_chapters']} глав, целостность: {st['canon_ok']}. Дневник: {st['diary_entries']}. Новые главы: {st['approved']}. Черновики: {st['pending']}. Сон: {'включён' if CHRONICLE['enabled'] else 'выключен'}. Параметры персонажа: {st['traits']}."

def chronicle_worker(stop):
    while not stop.wait(60):
        try:
            with LOCK, closing(connect()) as db, db:
                soul_chronicle.collect(db)
            if CHRONICLE["enabled"]:
                generate_chronicle(background=True)
        except (sqlite3.Error,ValueError,OSError):
            # Keep foreground server available; no secret or prompt logging.
            continue

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "dist"), **kwargs)

    def log_message(self, fmt, *args):
        # No request body or secret is logged.
        super().log_message(fmt, *args)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()

    def respond(self, data, status=200):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def local(self):
        port = self.server.server_address[1]
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        return host in (f"127.0.0.1:{port}", f"localhost:{port}") and (origin is None or origin == f"http://{host}") and self.headers.get("Sec-Fetch-Site") not in ("cross-site", "same-site")

    def do_GET(self):
        if not self.local():
            return self.respond({"error":"Доступ только локально"},403)
        if self.path == "/api/chronicle":
            with closing(connect()) as db:
                return self.respond({"status":soul_chronicle.status(db),"graph":soul_chronicle.biography_graph(db)})
        if self.path == "/api/graph":
            with closing(connect()) as db:
                return self.respond(memory_graph.snapshot(db))
        if self.path.split("?",1)[0] == "/api/avatar":
            path = ROOT / "data" / "avatar.png"
            if not path.is_file():
                return self.respond({"error":"Аватар не выбран"},404)
            raw = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type","image/png")
            self.send_header("Content-Length",str(len(raw)))
            self.send_header("Cache-Control","no-store")
            self.end_headers()
            self.wfile.write(raw)
            return
        if self.path == "/api/history":
            with LOCK:
                return self.respond({"messages":history(), "connected":bool(CONFIG["key"])})
        if self.path.startswith("/api/"):
            return self.respond({"error":"Не найдено"},404)
        super().do_GET()

    def do_POST(self):
        if not self.local():
            return self.respond({"error":"Доступ только локально"},403)
        try:
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Требуется JSON")
            length = int(self.headers.get("Content-Length","0"))
            if not 0 < length <= (12_000_000 if self.path == "/api/avatar" else 100000):
                raise ValueError("Недопустимый размер запроса")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Некорректный JSON")
            if self.path == "/api/avatar":
                raw = base64.b64decode(data.get("png",""),validate=True)
                if not 33 <= len(raw) <= 8_000_000 or raw[:8] != b"\x89PNG\r\n\x1a\n" or raw[12:16] != b"IHDR":
                    raise ValueError("PNG required")
                width,height = int.from_bytes(raw[16:20],"big"),int.from_bytes(raw[20:24],"big")
                if not 0 < width <= 4096 or not 0 < height <= 4096:
                    raise ValueError("Invalid dimensions")
                with LOCK:
                    target = ROOT / "data" / "avatar.png"
                    target.parent.mkdir(parents=True,exist_ok=True)
                    tmp = target.with_suffix(".tmp")
                    tmp.write_bytes(raw)
                    tmp.replace(target)
                return self.respond({"ok":True})
            if self.path == "/api/note":
                with closing(connect()) as db, db:
                    memory_graph.add_note(db,data.get("kind"),data.get("content"))
                return self.respond({"ok":True})
            if self.path == "/api/config":
                key, model = data.get("key"),data.get("model")
                if data.get("consent") is not True or not isinstance(key,str) or not isinstance(model,str) or not key.strip() or not model.strip() or len(key)>4096 or len(model)>200 or any(ord(c)<32 or ord(c)>126 for c in key):
                    raise ValueError("Укажите ключ, модель и подтвердите разрешение")
                with LOCK:
                    with closing(connect()) as db, db:
                        soul_core.record_model(db,model.strip())
                    CONFIG.update(key=key.strip(), model=model.strip())
                    CHRONICLE.update(enabled=False,epoch=CHRONICLE["epoch"]+1)
                return self.respond({"connected":True})
            if self.path != "/api/chat":
                return self.respond({"error":"Не найдено"},404)
            content = data.get("content")
            if not isinstance(content,str) or not content.strip() or len(content)>12000:
                raise ValueError("Введите сообщение до 12000 символов")
            with LOCK:
                CHRONICLE["last_activity"]=time.monotonic()
            command=chronicle_command(content)
            if command is not None:
                return self.respond({"reply":command,"connected":bool(CONFIG["key"])})
            with LOCK:
                store("user",content.strip())
                if not CONFIG["key"]:
                    reply = "Сообщение сохранено локально. Для ответа подключите Cloud.ru через меню аватара."
                    return self.respond({"reply":reply,"connected":False})
                with closing(connect()) as db:
                    persona = soul_core.system_prompt(db, CONFIG["model"], content.strip())
                payload = {"model":CONFIG["model"],"messages":[{"role":"system","content":persona}]+history(24),"max_tokens":1200,"stream":False}
                req = Request(API, data=json.dumps(payload).encode(), headers={"Authorization":"Bearer "+CONFIG["key"],"Content-Type":"application/json"}, method="POST")
                try:
                    with urlopen(req,timeout=60) as res:
                        body = json.loads(res.read(4_000_000))
                    reply = body["choices"][0]["message"]["content"]
                    if not isinstance(reply,str) or not reply.strip():
                        raise ValueError("empty response")
                except (URLError, TimeoutError, ValueError, KeyError, IndexError, TypeError, OSError):
                    return self.respond({"error":"Cloud.ru не вернул ответ. Сообщение сохранено; проверьте модель и ключ."},502)
                store("assistant",reply)
                CHRONICLE["last_activity"]=time.monotonic()
                return self.respond({"reply":reply,"connected":True})
        except (ValueError, UnicodeError, TypeError, binascii.Error) as e:
            return self.respond({"error":"Некорректные данные запроса"},400)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if not (ROOT / "dist" / "index.html").is_file():
        raise SystemExit("Frontend not built: npm install && npm run build")
    with closing(connect()) as db, db:
        soul_chronicle.recover(db)
        soul_chronicle.collect(db)
    stop=threading.Event()
    worker=threading.Thread(target=chronicle_worker,args=(stop,),daemon=True)
    worker.start()
    with ThreadingHTTPServer(("127.0.0.1",args.port),Handler) as server:
        url = f"http://127.0.0.1:{server.server_address[1]}"
        print("Hakureya: "+url,flush=True)
        if not args.no_browser:
            threading.Timer(.3,lambda:webbrowser.open(url)).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()

if __name__ == "__main__":
    main()
