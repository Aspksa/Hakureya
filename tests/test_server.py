import json, tempfile, threading, unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
import server
from unittest.mock import patch, MagicMock
from contextlib import closing
import soul_core

class ServerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = server.DB
        server.DB = Path(self.temp.name) / "test.sqlite3"
        server.CONFIG.update(key="",model="")
        server.CHRONICLE.update(enabled=False,epoch=0,last_activity=0)
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
        self.assertEqual(len(self.request("history")["messages"]),1)
    def test_consent_and_cross_origin(self):
        with self.assertRaises(HTTPError) as e:
            self.request("config",{"key":"key","model":"model","consent":False})
        self.assertEqual(e.exception.code,400)
        with self.assertRaises(HTTPError) as e:
            self.request("history",headers={"Origin":"https://example.com"})
        self.assertEqual(e.exception.code,403)

    def test_real_graph_and_notes(self):
        initial=self.request("graph")
        self.assertEqual(len([n for n in initial["records"] if n["key"].startswith("canon:")]),13)
        self.assertTrue(all(n["group"]==4 for n in initial["records"]))
        self.request("chat",{"content":"проверка двигателя автомобиля"})
        self.request("note",{"kind":1,"content":"проверка двигателя автомобиля"})
        graph=self.request("graph")
        self.assertEqual(graph["total"],initial["total"]+2)
        self.assertEqual({n["group"] for n in graph["records"]},{0,1,4})
        self.assertTrue(any(e["kind"]=="keywords" for e in graph["edges"]))
        self.assertEqual(graph,self.request("graph"))
        with self.assertRaises(HTTPError):
            self.request("note",{"kind":2,"content":"invalid"})

    def test_persona_used_in_chat_without_paid_call(self):
        self.request("chat",{"content":"отвечай кратко"})
        self.request("config",{"key":"test-key","model":"test-model","consent":True})
        fake=MagicMock()
        fake.__enter__.return_value.read.return_value=json.dumps({"choices":[{"message":{"content":"Готово."}}]}).encode()
        with patch.object(server,"urlopen",return_value=fake) as remote:
            result=self.request("chat",{"content":"Проверка"})
            self.assertTrue(result["connected"])
            payload=json.loads(remote.call_args.args[0].data)
            self.assertEqual(payload["model"],"test-model")
            self.assertEqual(payload["messages"][0]["role"],"system")
            self.assertIn("Hakureya",payload["messages"][0]["content"])
            self.assertIn("Кратко",payload["messages"][0]["content"])
        with closing(server.connect()) as db:
            snap=soul_core.snapshot(db)
            self.assertEqual(snap["history"]["events"]["response_review"],1)
            self.assertEqual(snap["history"]["events"]["model_selected"],1)

    def test_chronicle_cloud_draft_opt_in(self):
        import soul_chronicle as c
        from test_chronicle import draft
        for i in range(5):
            server.store("assistant","Ответ")
        with patch.object(server,"urlopen") as remote:
            self.assertIn("Дневник",self.request("chat",{"content":"летопись: статус"})["reply"])
            self.assertIn("Cloud.ru",self.request("chat",{"content":"летопись: создать"})["reply"])
            remote.assert_not_called()
        self.request("config",{"key":"test-key","model":"test-model","consent":True})
        with patch.object(server,"urlopen") as remote:
            server.generate_chronicle(background=True)
            remote.assert_not_called()
        fake=MagicMock()
        fake.__enter__.return_value.read.return_value=json.dumps({"choices":[{"message":{"content":json.dumps(draft(),ensure_ascii=False)}}]}).encode()
        with patch.object(server,"urlopen",return_value=fake) as remote:
            self.assertIn("Черновик создан",self.request("chat",{"content":"летопись: создать"})["reply"])
            self.assertEqual(remote.call_count,1)
            sent=json.loads(remote.call_args.args[0].data)
            self.assertEqual(sent["max_tokens"],1800)
            self.assertIn("Черновик",self.request("chat",{"content":"летопись: черновик"})["reply"].replace("черновик","Черновик"))
            self.assertFalse(any(n["key"].startswith("c:") for n in self.request("graph")["records"]))
            self.assertTrue(any(n["key"]=="draft:1" and n["kind"]=="draft" for n in self.request("graph")["records"]))
            self.assertIn("Решение сохранено",self.request("chat",{"content":"летопись: принять 1"})["reply"])
            self.assertTrue(any(n["key"]=="c:1" for n in self.request("graph")["records"]))
            self.assertEqual(self.request("chronicle")["status"]["approved"],1)
            self.request("chat",{"content":"летопись: создать"})
            self.assertEqual(remote.call_count,1)

    def test_real_activity_during_network_and_error(self):
        from urllib.error import URLError
        self.request("chat",{"content":"Локально"})
        self.assertEqual(self.request("activity")["active"],[])
        self.request("config",{"key":"test-key","model":"test-model","consent":True})
        fake=MagicMock()
        fake.__enter__.return_value.read.return_value=json.dumps({"choices":[{"message":{"content":"Ответ"}}]}).encode()
        def remote(*args,**kwargs):
            events=self.request("activity")
            self.assertEqual(len(events["active"]),1)
            self.assertEqual(events["active"][0]["kind"],"chat")
            self.assertEqual(events["active"][0]["stage"],"waiting")
            self.assertNotIn("test-key",json.dumps(events))
            return fake
        with patch.object(server,"urlopen",side_effect=remote):
            self.request("chat",{"content":"Вопрос"})
        events=self.request("activity")
        self.assertEqual(events["active"],[])
        self.assertTrue(any(e["stage"]=="done" for e in events["recent"]))
        with patch.object(server,"urlopen",side_effect=URLError("offline")):
            with self.assertRaises(HTTPError):
                self.request("chat",{"content":"Ошибка"})
        self.assertEqual(self.request("activity")["active"],[])
        self.assertTrue(any(e["stage"]=="error" for e in self.request("activity")["recent"]))


    def test_saga_reading_and_writing_without_diary(self):
        from test_chronicle import draft
        with patch.object(server,"urlopen") as remote:
            self.assertIn("Глава V.",self.request("chat",{"content":"прочитай главу 5"})["reply"])
            self.assertIn("оглавление",self.request("chat",{"content":"оглавление"})["reply"])
            remote.assert_not_called()
        self.request("config",{"key":"test-key","model":"test-model","consent":True})
        fake=MagicMock()
        fake.__enter__.return_value.read.return_value=json.dumps({"choices":[{"message":{"content":json.dumps(draft(),ensure_ascii=False)}}]}).encode()
        with patch.object(server,"urlopen",return_value=fake) as remote:
            result=self.request("chat",{"content":"продолжи нашу историю любви"})
            self.assertIn("Черновик создан",result["reply"])
            self.assertIn("История любви",result["reply"])
            self.assertIn(draft()["story"].strip(),result["reply"])
            sent=json.loads(remote.call_args.args[0].data)
            self.assertIn("романтическую связь",sent["messages"][0]["content"])
            self.assertIn("Глава 14",self.request("chat",{"content":"летопись: принять 1"})["reply"])
            self.assertIn("Новое открытие",self.request("chat",{"content":"летопись: читать 14"})["reply"])
            self.assertEqual(remote.call_count,1)
        graph=self.request("graph")
        self.assertTrue(any(e["a"]=="arc:love" and e["b"]=="c:1" for e in graph["edges"]))
        self.assertFalse(any(n["key"].startswith("d:") for n in graph["records"]))


    def test_shadow_saga_and_simple_chat(self):
        from test_omega import chapter
        with patch.object(server,"urlopen") as remote:
            self.assertIn("Оглавление",self.request("chat",{"content":"Летопись!"})["reply"])
            self.assertIn("0/18",self.request("chat",{"content":"Что дальше по сюжету?"})["reply"])
            self.assertIn("Нет ожидающей",self.request("chat",{"content":"Принять главу"})["reply"])
            remote.assert_not_called()
        self.request("config",{"key":"test-key","model":"test-model","consent":True})
        draft=chapter()
        draft["shadow"]={"step":0,"evidence":"Хакурэя открыла дверь серебряного архива."}
        fake=MagicMock()
        fake.__enter__.return_value.read.return_value=json.dumps({"choices":[{"message":{"content":json.dumps(draft,ensure_ascii=False)}}]}).encode()
        with patch.object(server,"urlopen",return_value=fake) as remote:
            self.assertIn("Черновик создан",self.request("chat",{"content":"Продолжи сагу"})["reply"])
            self.assertIn("Глава 14 сохранена",self.request("chat",{"content":"Принять главу."})["reply"])
            self.assertIn("1/18",self.request("chat",{"content":"Что дальше по сюжету?"})["reply"])
            self.assertEqual(remote.call_count,1)
        self.assertTrue(any(n["key"]=="shadow:event:0" for n in self.request("graph")["records"]))


    def test_page_reader_offline(self):
        with patch.object(server,"urlopen") as remote:
            first=self.request("chat",{"content":"Прочитай главу 5"})["reply"]
            second=self.request("chat",{"content":"Дальше!"})["reply"]
            self.assertIn("Страница 2/",second)
            self.assertEqual(self.request("chat",{"content":"Продолжить чтение"})["reply"],second)
            self.assertEqual(self.request("chat",{"content":"Назад"})["reply"],first)
            self.assertIn("страница 1",self.request("chat",{"content":"Остановить чтение"})["reply"])
            self.assertEqual(self.request("chat",{"content":"Читать книгу"})["reply"],first)
            remote.assert_not_called()


    def test_guardians_chat_local(self):
        with patch.object(server,"urlopen") as remote:
            reply=self.request("chat",{"content":"Девять хранительниц"})["reply"]
            self.assertIn("Рэйка",reply)
            self.assertIn("Амацука",reply)
            self.assertIn("Холод",self.request("chat",{"content":"летопись: хранительница Рэйка"})["reply"])
            self.request("config",{"key":"test-key","model":"test-model","consent":True})
            self.assertIn("Ожидает развития Тени",self.request("chat",{"content":"Продолжи историю хранительниц"})["reply"])
            remote.assert_not_called()


    def test_destiny_local_plan(self):
        with patch.object(server,"urlopen") as remote:
            reply=self.request("chat",{"content":"Новые герои"})["reply"]
            self.assertIn("Иори",reply)
            self.assertIn("Орум",reply)
            self.assertIn("0/70",self.request("chat",{"content":"За пределами девяти небес"})["reply"])
            self.assertIn("80.",self.request("chat",{"content":"План судьбы"})["reply"])
            self.request("config",{"key":"test-key","model":"test-model","consent":True})
            self.assertIn("Ожидает завершения",self.request("chat",{"content":"Продолжи судьбу"})["reply"])
            remote.assert_not_called()
