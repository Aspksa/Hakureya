import json, tempfile, threading, unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
import server

class ServerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = server.DB
        server.DB = Path(self.temp.name) / "test.sqlite3"
        server.CONFIG.update(key="",model="")
        self.http = ThreadingHTTPServer(("127.0.0.1",0),server.Handler)
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True)
        self.thread.start()
        self.url=f"http://127.0.0.1:{self.http.server_address[1]}/api/"
    def tearDown(self):
        self.http.shutdown()
        self.thread.join()
        self.http.server_close()
        server.DB=self.old
        self.temp.cleanup()
    def request(self,path,data=None,headers=None):
        h={"Content-Type":"application/json"}
        h.update(headers or {})
        with urlopen(Request(self.url+path,data=None if data is None else json.dumps(data).encode(),headers=h),timeout=5) as r:
            return json.load(r)
    def test_local_persistence(self):
        self.assertEqual(self.request("history")["messages"],[])
        self.assertFalse(self.request("chat",{"content":"Привет"})["connected"])
        self.assertEqual(self.request("history")["messages"][0]["content"],"Привет")
        self.assertEqual(len(self.request("history")["messages"]),2)
    def test_consent_and_cross_origin(self):
        with self.assertRaises(HTTPError) as e:
            self.request("config",{"key":"key","model":"model","consent":False})
        self.assertEqual(e.exception.code,400)
        with self.assertRaises(HTTPError) as e:
            self.request("history",headers={"Origin":"https://example.com"})
        self.assertEqual(e.exception.code,403)
