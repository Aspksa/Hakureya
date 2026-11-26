from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError
import argparse, json, sqlite3, threading, webbrowser, os
from contextlib import closing
import memory_graph
import soul_core
import soul_chronicle
import soul_saga
import soul_omega
import graph_activity
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

def generate_chronicle(background=False, arc=None):
    # Reserve quota and snapshot under lock; do not block chat during network I/O.
    with LOCK:
        if not CONFIG["key"] or (background and (not CHRONICLE["enabled"] or time.monotonic()-CHRONICLE["last_activity"]<1200)):
            return "Cloud.ru не подключён или фоновый сон не разрешён."
        with closing(connect()) as db, db:
            soul_chronicle.collect(db)
            reservation=soul_chronicle.reserve(db,allow_story=True)
            traits=soul_chronicle.profile(db)
            plan=soul_omega.enrich_plan(db,soul_saga.plan(db,arc)) if reservation else None
            rows=soul_saga.reading_rows(db) if reservation else []
            same=[p for p in rows if p["arc"]==plan["arc"]] if plan else []
            previous=[{"number":p["number"],"title":p["title"],"story":p["story"][:1800],"tags":p["tags"]} for p in same[-2:]]
            if rows: previous.append({"published_titles":[p["title"] for p in rows[-12:]]})
        if not reservation:
            return "Есть незавершённая попытка или ожидающий черновик, нарушена целостность канона либо исчерпан дневной лимит."
        key, model, epoch=CONFIG["key"],CONFIG["model"],CHRONICLE["epoch"]
    with graph_activity.track("chronicle",(f"d:{reservation[1]}" if reservation[1]>0 else "arc:"+plan["arc"])) as activity:
        return execute_chronicle(reservation,traits,previous,key,model,epoch,activity,plan)

def execute_chronicle(reservation,traits,previous,key,model,epoch,activity,plan):
    try:
        payload={"model":model,"messages":soul_chronicle.prompt(reservation,traits,previous,plan),"max_tokens":1800,"stream":False}
        req=Request(API,data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
        graph_activity.update(activity,"waiting")
        with urlopen(req,timeout=60) as res:
            result=json.loads(res.read(1_000_000))
        graph_activity.update(activity,"validating","hub:4")
        raw=result["choices"][0]["message"]["content"]
        if not isinstance(raw,str) or len(raw)>24000:
            raise ValueError("invalid draft")
        value=json.loads(raw)
        with LOCK, closing(connect()) as db, db:
            if CHRONICLE["epoch"]!=epoch:
                soul_chronicle.fail(db,reservation)
                graph_activity.update(activity,"discarded")
                return "Настройки изменились; черновик отброшен."
            soul_chronicle.finish(db,reservation,value,plan)
            pending=soul_chronicle.latest_pending(db)
            editorial=soul_omega.metadata(db,pending["id"])
        graph_activity.update(activity,"done",f"draft:{pending['id']}" if pending else "hub:4")
        return "Черновик создан. "+soul_saga.ARC_LABELS[plan["arc"]]+".\n\n"+pending["title"]+"\n\n"+pending["story"]+"\n\nОценка редактора (эвристика): "+str(editorial["score"])+"/100. "+", ".join(editorial["warnings"])+"\n\nлетопись: принять "+str(pending["id"])+" / летопись: отклонить "+str(pending["id"])
    except (URLError,TimeoutError,ValueError,KeyError,IndexError,TypeError,OSError,sqlite3.Error):
        with LOCK, closing(connect()) as db, db:
            soul_chronicle.fail(db,reservation)
        graph_activity.update(activity,"error")
        return "Черновик не создан: ответ модели не прошёл проверку или запрос завершился ошибкой. Дневная попытка учтена."

def chronicle_command(content):
    q=content.strip().casefold()
    aliases={"оглавление":"летопись: содержание","покажи оглавление":"летопись: содержание","прочитать последнюю главу":"летопись: последняя","покажи последнюю главу":"летопись: последняя","создай новую главу":"летопись: создать","продолжи нашу историю любви":"летопись: создать любовь"}
    q=aliases.get(q,q)
    read_match=re.fullmatch(r"(?:летопись: читать|прочитай главу|читать главу) ([1-9][0-9]{0,8})",q)
    create_match=re.fullmatch(r"летопись: создать(?: (прошлое|встреча|любовь|будущее))?",q)
    omega_read=re.fullmatch(r"летопись: (том|читать том|дневник героини) ([1-9][0-9]{0,8})",q)
    omega_search=re.fullmatch(r"летопись: (поиск|персонаж) (.{2,200})",q)
    omega_commands=("летопись: книги","летопись: продолжить чтение","летопись: план","летопись: загадки","летопись: качество","летопись: дневник героини","летопись: хронология")
    decision=re.fullmatch(r"летопись: (принять|отклонить) ([1-9][0-9]{0,8})",q)
    if q not in soul_chronicle.COMMANDS and not decision and not read_match and not create_match and not omega_read and not omega_search and q not in omega_commands and q not in ("летопись: главы","летопись: содержание","летопись: последняя"):
        return None
    if create_match:
        with LOCK, closing(connect()) as db, db:
            soul_chronicle.control(db,"manual_request")
        return generate_chronicle(arc=soul_saga.ALIASES.get(create_match[1]))
    with LOCK, closing(connect()) as db, db:
        if (omega_read or omega_search or q in omega_commands or read_match or q in ("летопись: содержание","летопись: последняя","летопись: главы")) and not soul_chronicle.canon_ok(db):
            return "Целостность исходной летописи нарушена; чтение заблокировано."
        if read_match or q=="летопись: продолжить чтение":
            n=int(read_match[1]) if read_match else soul_omega.bookmark(db)
            result=soul_saga.read(db,n)
            if result.startswith(("Художественный канон","Художественная глава")): soul_omega.mark(db,n)
            return result
        if omega_read:
            n=int(omega_read[2])
            if omega_read[1]=="читать том": return soul_omega.read_volume(db,n)
            return soul_omega.book(db,n) if omega_read[1]=="том" else soul_omega.diary(db,n)
        if omega_search:
            term=omega_search[2]
            if omega_search[1]=="персонаж": return soul_omega.character(db,term)
            rows=soul_omega.search(db,term,12)
            return "Найденные главы (по словам):\n"+"\n".join(f"{p['number']}. {p['title']}" for p in rows) if rows else "Ничего не найдено."
        if q=="летопись: книги": return soul_omega.books(db)
        if q=="летопись: дневник героини": return soul_omega.diary(db)
        if q=="летопись: качество": return soul_omega.quality(db)
        if q=="летопись: план":
            return "Предварительный план (не канон):\n"+"\n".join(f"{i}. {soul_saga.ARC_LABELS[p['arc']]} — {p['beat']}" for i,p in enumerate(soul_omega.roadmap(db),1))
        if q=="летопись: загадки":
            return "Загадки художественного мира:\n"+"\n".join(f"{v['question']} — глава {v['opened']}; "+(f"раскрыта в главе {v['closed']}" if v['closed'] else "открыта") for v in soul_omega.mysteries(db).values())
        if q=="летопись: хронология":
            return "Художественные эпохи (главы в порядке публикации внутри эпохи):\n"+"\n\n".join(soul_omega.ERA[a]+":\n"+"\n".join(f"{n}. {t}" for n,t in db.execute("SELECT number,title FROM omega_index WHERE arc=? ORDER BY number",(a,))) for a in soul_omega.ARCS)
        if q=="летопись: содержание": return soul_saga.contents(db)
        if q=="летопись: последняя":
            n=db.execute("SELECT MAX(number) FROM omega_index").fetchone()[0] or 13
            result=soul_saga.read(db,n)
            if result.startswith(("Художественный канон","Художественная глава")): soul_omega.mark(db,n)
            return result
        if q=="летопись: включить сон":
            if not CONFIG["key"]:
                return "Сначала подключите Cloud.ru. Сон не включён."
            CHRONICLE.update(enabled=True,epoch=CHRONICLE["epoch"]+1)
            soul_chronicle.control(db,"background_enabled")
            return "Сон включён до закрытия сервера: не чаще одной попытки UTC в сутки, после 20 минут тишины, даже без новой записи дневника, по очереди сюжетных веток. В Cloud.ru передаются канон, утверждённые художественные главы и счётчики (если есть), не текст чата. Отключение: летопись: выключить сон."
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
            if ok and decision[1]=="принять":
                n=db.execute("SELECT number FROM saga_arcs WHERE draft_id=?",(i,)).fetchone()[0]
                return f"Решение сохранено. Глава {n} добавлена в летопись и граф. Читать: летопись: читать {n}."
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
            rows=soul_saga.reading_rows(db)[-5:]
            return "\n\n".join(f"Вымышленная глава №{p['number']}: {p['title']}\n{p['story']}" for p in rows) or "Новых утверждённых глав пока нет."
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
        if self.path == "/api/activity":
            return self.respond(graph_activity.snapshot())
        if self.path == "/api/chronicle":
            with closing(connect()) as db:
                return self.respond({"status":soul_chronicle.status(db),"graph":soul_chronicle.biography_graph(db)})
        if self.path == "/api/graph":
            with closing(connect()) as db, db:
                data=memory_graph.snapshot(db)
            return self.respond(data)
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
                user_id=store("user",content.strip())
                if not CONFIG["key"]:
                    reply = "Сообщение сохранено локально. Для ответа подключите Cloud.ru через меню аватара."
                    return self.respond({"reply":reply,"connected":False})
                with closing(connect()) as db:
                    persona = soul_core.system_prompt(db, CONFIG["model"], content.strip())
                payload = {"model":CONFIG["model"],"messages":[{"role":"system","content":persona}]+history(24),"max_tokens":1200,"stream":False}
                req = Request(API, data=json.dumps(payload).encode(), headers={"Authorization":"Bearer "+CONFIG["key"],"Content-Type":"application/json"}, method="POST")
                with graph_activity.track("chat",f"m:{user_id}") as activity:
                    try:
                        graph_activity.update(activity,"waiting")
                        with urlopen(req,timeout=60) as res:
                            body = json.loads(res.read(4_000_000))
                        graph_activity.update(activity,"received")
                        reply = body["choices"][0]["message"]["content"]
                        if not isinstance(reply,str) or not reply.strip():
                            raise ValueError("empty response")
                    except (URLError, TimeoutError, ValueError, KeyError, IndexError, TypeError, OSError):
                        graph_activity.update(activity,"error")
                        return self.respond({"error":"Cloud.ru не вернул ответ. Сообщение сохранено; проверьте модель и ключ."},502)
                    answer_id=store("assistant",reply)
                    graph_activity.update(activity,"done",f"m:{answer_id}")
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
