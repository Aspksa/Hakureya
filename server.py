from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError
import argparse, json, sqlite3, threading, webbrowser, os
from contextlib import closing

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "hakureya.sqlite3"
API = "https://foundation-models.api.cloud.ru/v1/chat/completions"
LOCK = threading.Lock()
CONFIG = {"key": "", "model": ""}
PERSONA = "Ты Hakureya, белоснежная императрица кицунэ. Отвечай по-русски, точно, спокойно и уважительно. Не выдумывай факты. Помогай пользователю решать задачи."

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=10)
    db.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, role TEXT NOT NULL, content TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP)")
    db.commit()
    return db

def history(limit=200):
    with closing(connect()) as db:
        rows = db.execute("SELECT role,content FROM messages ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [{"role": r, "content": c} for r,c in reversed(rows)]

def store(role, content):
    with closing(connect()) as db, db:
        db.execute("INSERT INTO messages(role,content) VALUES(?,?)", (role,content))

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
            if not 0 < length <= 100000:
                raise ValueError("Недопустимый размер запроса")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Некорректный JSON")
            if self.path == "/api/config":
                key, model = data.get("key"),data.get("model")
                if data.get("consent") is not True or not isinstance(key,str) or not isinstance(model,str) or not key.strip() or not model.strip() or len(key)>4096 or len(model)>200 or any(ord(c)<32 or ord(c)>126 for c in key):
                    raise ValueError("Укажите ключ, модель и подтвердите разрешение")
                with LOCK:
                    CONFIG.update(key=key.strip(), model=model.strip())
                return self.respond({"connected":True})
            if self.path != "/api/chat":
                return self.respond({"error":"Не найдено"},404)
            content = data.get("content")
            if not isinstance(content,str) or not content.strip() or len(content)>12000:
                raise ValueError("Введите сообщение до 12000 символов")
            with LOCK:
                store("user",content.strip())
                if not CONFIG["key"]:
                    reply = "Сообщение сохранено локально. Для ответа подключите Cloud.ru через меню аватара."
                    store("assistant",reply)
                    return self.respond({"reply":reply,"connected":False})
                payload = {"model":CONFIG["model"],"messages":[{"role":"system","content":PERSONA}]+history(24),"max_tokens":1200,"stream":False}
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
                return self.respond({"reply":reply,"connected":True})
        except (ValueError, UnicodeError) as e:
            return self.respond({"error":"Некорректные данные запроса"},400)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if not (ROOT / "dist" / "index.html").is_file():
        raise SystemExit("Frontend not built: npm install && npm run build")
    with closing(connect()):
        pass
    with ThreadingHTTPServer(("127.0.0.1",args.port),Handler) as server:
        url = f"http://127.0.0.1:{server.server_address[1]}"
        print("Hakureya: "+url,flush=True)
        if not args.no_browser:
            threading.Timer(.3,lambda:webbrowser.open(url)).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
