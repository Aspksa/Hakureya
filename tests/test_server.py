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
    def test_local_neural_diagnostic_and_focused_graph(self):
        with patch.object(server,"urlopen") as remote:
            before=self.request("graph/network")
            self.assertTrue(before["network"])
            self.assertIsNone(before["neural_trace"])
            reply=self.request("chat",{"content":"Проверить 10 мозгов"})["reply"]
            self.assertIn("10/10",reply)
            self.assertIn("31 проверенных зависимостей",reply)
            graph=self.request("graph/network")
            self.assertEqual(graph["trace_origin"],"diagnostic")
            self.assertEqual(len(graph["neural_trace"]["events"]),10)
            self.assertEqual(len([r for r in graph["records"] if r["kind"]=="lit_brain"]),10)
            with closing(server.connect()) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM chronicle_attempts").fetchone()[0],0)
            remote.assert_not_called()

    def test_dynasty_commands_and_single_writer_request(self):
        from test_dynasty import base
        with patch.object(server,"urlopen") as remote:
            self.assertIn("0 из 70",self.request("chat",{"content":"Династия вечности"})["reply"])
            self.assertIn("11. Приговорённая к казни",self.request("chat",{"content":"План династии"})["reply"])
            self.assertIn("Нет доступных",self.request("chat",{"content":"История горничной"})["reply"])
            remote.assert_not_called()
        self.request("config",{"key":"test-key","model":"test-model","consent":True})
        payload={**base(),"dynasty":{"step":11,"evidence":"Маюри была приговорена к казни."}}
        fake=MagicMock()
        fake.__enter__.return_value.read.return_value=json.dumps({"choices":[{"message":{"content":json.dumps(payload,ensure_ascii=False)}}]}).encode()
        with patch.object(server,"urlopen",return_value=fake) as remote:
            self.assertIn("Черновик создан",self.request("chat",{"content":"Продолжи династию"})["reply"])
            self.assertEqual(remote.call_count,1)
            sent=json.loads(remote.call_args.args[0].data)
            self.assertEqual(sent["max_tokens"],1800)
            self.assertIn("Eternal Dynasty",sent["messages"][0]["content"])
            self.assertIn("Маюри",sent["messages"][0]["content"])
            self.assertIn("0 из 70",self.request("chat",{"content":"Династия вечности"})["reply"])
            self.assertIn("Глава 14",self.request("chat",{"content":"Принять главу"})["reply"])
            self.assertIn("1 из 70",self.request("chat",{"content":"Династия вечности"})["reply"])
            self.assertIn("завершите текущую главу Династии",self.request("chat",{"content":"летопись: цикл обычная"})["reply"])
            self.assertEqual(remote.call_count,1)

    def test_writer_transport_failure_releases_reservation(self):
        from http.client import IncompleteRead
        self.request("config",{"key":"test-key","model":"test-model","consent":True})
        def interrupted(response,progress,preview):
            preview('{"story":"Полученный фрагмент')
            raise IncompleteRead(b"")
        with patch.object(server,"urlopen",return_value=MagicMock()) as remote, patch.object(server.writer_stream,"read_response",side_effect=interrupted):
            reply=self.request("chat",{"content":"Продолжи династию"})["reply"]
            self.assertIn("Черновик не создан",reply)
            self.assertEqual(remote.call_count,1)
            with closing(server.connect()) as db:
                self.assertEqual(db.execute("SELECT status FROM chronicle_attempts").fetchone()[0],"failed")
                self.assertEqual(db.execute("SELECT COUNT(*) FROM chronicle_drafts").fetchone()[0],0)
            self.assertIn("Полученный фрагмент",self.request("chat",{"content":"Восстановить фрагмент"})["reply"])
            self.assertIn("Укажите запрос",self.request("chat",{"content":"Поиск сцены"})["reply"])
            self.assertEqual(remote.call_count,1)

    def test_universe_local_panel_and_export(self):
        with patch.object(server,"urlopen") as remote:
            data=self.request("universe/1")
            self.assertEqual(data["chapters"],13)
            self.assertGreater(data["scenes"],13)
            self.assertEqual(data["volume_groups"],[{"volume":1,"count":13}])
            self.assertIn("Глава",self.request("chat",{"content":"Поиск сцены первое прикосновение"})["reply"])
            self.assertFalse(self.request("writer/preview")["active"])
            self.assertIn("подтверждена",self.request("chat",{"content":"Проверить индекс сцен"})["reply"])
            remote.assert_not_called()
        for kind in ("epub","docx","html"):
            with urlopen(self.url+"universe/export/"+kind,timeout=5) as res:
                self.assertEqual(res.status,200)
                self.assertTrue(res.read())
        self.request("config",{"key":"test-key","model":"test-model","consent":True})
        data=self.request("writer",{"mode":"draft","interval":30,"consent":True,"target_pages":30,"chapter_pages":20,"budget":{"monthly":1000,"input":100,"output":200}})
        self.assertEqual(data["target_pages"],30)
        self.assertEqual(data["chapter_pages"],20)
        self.assertEqual(self.request("writer")["chapter_pages"],20)

    def test_one_shot_without_budget_after_legacy_attempt(self):
        self.request("config",{"key":"test-key","model":"test-model","consent":True})
        with closing(server.connect()) as db, db:
            reservation=server.soul_chronicle.reserve(db,allow_story=True)
            server.soul_chronicle.fail(db,reservation)
        data={"mode":"once","interval":20,"target_pages":5,"consent":True}
        with patch.object(server,"urlopen") as remote:
            with self.assertRaises(HTTPError):self.request("writer",{**data,"consent":False})
            state=self.request("writer",data)
            self.assertEqual(state["mode"],"auto")
            self.assertEqual(state["job"]["state"],"active")
            self.assertEqual(state["job"]["pages"],5)
            self.assertEqual(state["job"]["attempts"],0)
            self.assertEqual(state["daily_limit"],20)
            self.assertEqual(state["max_tokens"],4096)
            self.assertEqual(state["wait_seconds"],0)
            self.assertIsNone(state["budget_settings"])
            self.assertEqual(self.request("writer")["job"]["state"],"active")
            remote.assert_not_called()
        from urllib.error import URLError
        with patch.object(server,"urlopen",side_effect=URLError("test")) as remote:
            server.generate_chronicle(background=True)
            self.assertEqual(remote.call_count,1)
            sent=json.loads(remote.call_args.args[0].data)
            self.assertEqual(sent["max_tokens"],4096)
            self.assertIn("Разовое задание",sent["messages"][0]["content"])
            state=self.request("writer")
            self.assertEqual(state["mode"],"off")
            self.assertEqual(state["job"]["state"],"error")
            self.assertEqual(state["job"]["attempts"],1)
            self.assertIn("соединения",state["reason"])
            server.generate_chronicle(background=True)
            self.assertEqual(remote.call_count,1)
        self.request("writer",data)
        state=self.request("writer",{"mode":"off","interval":20,"target_pages":0})
        self.assertEqual(state["job"]["state"],"stopped")
        self.assertEqual(state["mode"],"off")

    def test_writer_panel_persistence_and_consent(self):
        st=self.request("writer")
        self.assertEqual(st["mode"],"off")
        self.assertEqual(st["published"],13)
        self.assertFalse(st["connected"])
        with self.assertRaises(HTTPError) as err:
            self.request("writer",{"mode":"auto","interval":20,"consent":False})
        self.assertEqual(err.exception.code,400)
        self.request("config",{"key":"test-key","model":"test-model","consent":True})
        st=self.request("writer",{"mode":"auto","interval":30,"consent":True,"start_now":True})
        self.assertEqual(st["mode"],"auto")
        self.assertEqual(st["interval"],30)
        self.assertEqual(st["wait_seconds"],0)
        self.assertEqual(self.request("writer")["mode"],"auto")
        self.assertEqual(self.request("writer")["daily_limit"],1)
        self.assertFalse(self.request("config/forget",{})["connected"])
        self.assertEqual(self.request("writer")["mode"],"off")

    def test_opt_in_vault_restore(self):
        import cloud_vault
        if not cloud_vault.supported():
            self.skipTest("Windows DPAPI only")
        secret="test-key-not-plaintext"
        self.request("config",{"key":secret,"model":"test-model","consent":True,"remember":True})
        path=server.DB.parent/"cloud.dpapi"
        self.assertTrue(path.is_file())
        self.assertNotIn(secret.encode(),path.read_bytes())
        self.assertNotIn(secret.encode(),server.DB.read_bytes())
        server.CONFIG.update(key="",model="")
        self.assertTrue(server.restore_connection())
        self.assertEqual(server.CONFIG["key"],secret)
        self.assertTrue(self.request("writer")["saved_connection"])
        self.request("config/forget",{})
        self.assertFalse(path.exists())
        self.assertFalse(server.restore_connection())

    def test_local_persistence(self):
        self.assertEqual(self.request("history")["messages"],[])
        self.assertFalse(self.request("chat",{"content":"Привет"})["connected"])
        self.assertEqual(self.request("history")["messages"][0]["content"],"Привет")
        self.assertEqual(len(self.request("history")["messages"]),1)
    def test_consent_and_cross_origin(self):
        with self.assertRaises(HTTPError) as e:
            self.request("config",{"key":"key","model":"model","consent":False})
        self.assertEqual(e.exception.code,400)
        self.assertIn("Подтвердите согласие",json.load(e.exception)["error"])
        with self.assertRaises(HTTPError) as e:
            self.request("history",headers={"Origin":"https://example.com"})
        self.assertEqual(e.exception.code,403)

    def test_cloud_catalog_and_connection_without_generation(self):
        key="test-cloud-key-memory-only"
        model="vendor/Chat-Model"
        fake=MagicMock()
        fake.__enter__.return_value.read.return_value=json.dumps({"object":"list","data":[
            {"id":model,"metadata":{"type":"llm"}},
            {"id":"vendor/Embedding-Model","metadata":{"type":"embedder"}},
            {"id":model},
        ]}).encode()
        with patch.object(server,"urlopen",return_value=fake) as remote:
            self.assertEqual(self.request("config/models",{}),{"models":[model]})
            self.assertIsNone(remote.call_args.args[0].get_header("Authorization"))
            self.assertEqual(self.request("config/models",{"key":f"\t{key}\n"}),{"models":[model]})
            outgoing=remote.call_args.args[0]
            self.assertEqual(outgoing.get_method(),"GET")
            self.assertIsNone(outgoing.data)
            self.assertEqual(outgoing.get_header("Authorization"),f"Bearer {key}")
            self.assertFalse(self.request("history")["connected"])
            self.assertEqual(server.CONFIG["key"],"")
            config={"key":f"\t{key}\n","model":"","consent":True}
            with self.assertRaises(HTTPError) as e:
                self.request("config",config)
            self.assertEqual(e.exception.code,400)
            self.assertIn("Выберите модель",json.load(e.exception)["error"])
            self.assertEqual(self.request("config",{**config,"model":model}),{"connected":True})
            self.assertEqual(remote.call_count,2)
        self.assertEqual(server.CONFIG,{"key":key,"model":model})
        self.assertNotIn(key.encode(),server.DB.read_bytes())

    def test_cloud_catalog_errors_leave_connection_untouched(self):
        with patch.object(server,"urlopen",side_effect=HTTPError(server.cloud_writer.MODELS_URL,401,"private detail",None,None)) as remote:
            with self.assertRaises(HTTPError) as e:
                self.request("config/models",{"key":"invalid-key"})
            self.assertEqual(e.exception.code,401)
            body=json.load(e.exception)["error"]
            self.assertIn("Проверьте API-ключ",body)
            self.assertNotIn("private detail",body)
            self.assertNotIn("invalid-key",body)
            with self.assertRaises(HTTPError) as e:
                self.request("config/models",{"key":"bad\nkey"})
            self.assertEqual(e.exception.code,400)
            self.assertIn("формат API-ключа",json.load(e.exception)["error"])
            self.assertEqual(remote.call_count,1)
        self.assertEqual(server.CONFIG,{"key":"","model":""})

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


    def test_living_controls_are_local(self):
        with patch.object(server,"urlopen") as remote:
            self.assertIn("выключено",self.request("chat",{"content":"Статус развития"})["reply"])
            self.assertIn("черновики",self.request("chat",{"content":"Развивай историю сама"})["reply"])
            self.assertIn("автопубликация",self.request("chat",{"content":"Включи автопубликацию глав"})["reply"])
            self.assertIn("остановлено",self.request("chat",{"content":"Останови развитие"})["reply"])
            self.assertIn("выключено",self.request("chat",{"content":"Статус развития"})["reply"])
            remote.assert_not_called()


    def test_independent_writer_model(self):
        self.request("config",{"key":"test-key","model":"test-chat","consent":True})
        fake=MagicMock()
        fake.__enter__.return_value.read.return_value=json.dumps({"data":[{"id":"zai-org/GLM-5.3"}]}).encode()
        with patch.object(server,"urlopen",return_value=fake) as remote:
            self.assertIn("zai-org/GLM-5.3",self.request("chat",{"content":"Подключи писателя"})["reply"])
            self.assertEqual(remote.call_args.args[0].get_method(),"GET")
            self.assertEqual(server.CONFIG["model"],"test-chat")
            self.assertIn("zai-org/GLM-5.3",self.request("chat",{"content":"Модель писателя"})["reply"])
            self.assertEqual(remote.call_count,1)
            self.assertIn("не найдена",self.request("chat",{"content":"Модель писателя missing"})["reply"])
            self.assertIn("zai-org/GLM-5.3",self.request("chat",{"content":"Модель писателя"})["reply"])
        from test_omega import chapter
        fake.__enter__.return_value.read.return_value=json.dumps({"choices":[{"message":{"content":json.dumps(chapter(),ensure_ascii=False)}}],"usage":{"prompt_tokens":1800,"completion_tokens":500}}).encode()
        with patch.object(server,"urlopen",return_value=fake) as remote:
            self.assertIn("Черновик создан",self.request("chat",{"content":"Продолжи сагу"})["reply"])
            payload=json.loads(remote.call_args.args[0].data)
            self.assertEqual(payload["model"],"zai-org/GLM-5.3")
            self.assertEqual(payload["max_tokens"],1800)
            self.assertEqual(remote.call_count,1)
            self.assertIn("выход 500",self.request("chat",{"content":"Расход писателя"})["reply"])


    def test_evolution_local_budget(self):
        self.request("config",{"key":"test-key","model":"test-model","consent":True})
        with patch.object(server,"urlopen") as remote:
            self.assertIn("романтика",self.request("chat",{"content":"Стиль романа романтика"})["reply"])
            self.assertIn("сохранено",self.request("chat",{"content":"Больше магии"})["reply"])
            self.assertIn("Империя чёрной луны",self.request("chat",{"content":"Новые сюжеты"})["reply"])
            self.assertIn("1.00",self.request("chat",{"content":"Бюджет писателя 1 тариф 999999 999999"})["reply"])
            self.assertIn("остановлен",self.request("chat",{"content":"Продолжи сагу"})["reply"])
            self.assertIn("4000",self.request("chat",{"content":"Формат главы большая"})["reply"])
            remote.assert_not_called()


    def test_book_reader_api_is_offline(self):
        with patch.object(server,"urlopen") as remote:
            self.assertIsNone(self.request("reader")["reader"])
            first=self.request("chat",{"content":"Читать с начала"})["reader"]
            self.assertEqual(first["chapter"],1)
            self.assertEqual(first["page"],1)
            self.assertNotIn("Художественный канон",first["text"])
            next_page=self.request("reader",{"action":"next"})["reader"]
            self.assertNotEqual(next_page,first)
            self.assertEqual(self.request("reader",{"action":"back"})["reader"],first)
            self.assertEqual(self.request("reader")["reader"],first)
            self.assertIsNone(self.request("reader",{"action":"pause"})["reader"])
            self.assertEqual(self.request("reader",{"action":"resume"})["reader"],first)
            self.assertIn("Императрица человеческого мира",self.request("chat",{"content":"Новые саги"})["reply"])
            self.assertEqual(self.request("graph/volume/1")["volume"],1)
            self.assertIn("30 минут",self.request("chat",{"content":"Интервал писателя 30"})["reply"])
            remote.assert_not_called()


    def test_independent_editor_uses_existing_daily_quota(self):
        import soul_chronicle as c
        from datetime import datetime,timezone
        from test_omega import chapter
        self.request("config",{"key":"test-key","model":"test-model","consent":True})
        with closing(server.connect()) as db, db:
            reservation=c.reserve(db,datetime(2099,1,1,tzinfo=timezone.utc),allow_story=True)
            c.finish(db,reservation,chapter())
            pending=c.latest_pending(db)
        fake=MagicMock()
        report={"score":80,"verdict":"revise","notes":[{"kind":"pace","issue":"Сцена слишком быстро заканчивается","evidence":"Хакурэя открыла дверь серебряного архива.","suggestion":"Добавить реакцию героини на открытие."}]}
        fake.__enter__.return_value.read.return_value=json.dumps({"choices":[{"message":{"content":json.dumps(report,ensure_ascii=False)}}],"usage":{"prompt_tokens":1000,"completion_tokens":200}}).encode()
        with patch.object(server,"urlopen",return_value=fake) as remote:
            self.assertIn("80/100",self.request("chat",{"content":"Проверить черновик редактором"})["reply"])
            self.assertIn("Суточная попытка",self.request("chat",{"content":"Проверить черновик редактором"})["reply"])
            self.assertIn("80/100",self.request("chat",{"content":"Отчёт редактора"})["reply"])
            self.assertEqual(remote.call_count,1)
            payload=json.loads(remote.call_args.args[0].data)
            self.assertEqual(payload["max_tokens"],1800)
        with closing(server.connect()) as db:
            self.assertEqual(c.latest_pending(db)["story"],pending["story"])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM chronicle_drafts WHERE status='approved'").fetchone()[0],0)


    def test_reader_presence_and_offsets_are_local(self):
        import time
        with patch.object(server,"urlopen") as remote:
            result=self.request("chat",{"content":"Читать с начала"})["reader"]
            d=result["document"]
            self.assertTrue(self.request("reader",{"action":"position","hash":d["hash"],"start":3,"end":40})["ok"])
            self.assertEqual(self.request("reader",{"action":"presence"})["reader"]["document"]["offset"],3)
            with closing(server.connect()) as db,db:
                self.assertFalse(server.reading_window(db))
                server.soul_living.set_mode(db,"draft")
                server.soul_reader.move(db,"latest")
                server.CHRONICLE["reader_seen"]=time.monotonic()
                self.assertTrue(server.reading_window(db))
                server.CHRONICLE["reader_seen"]=time.monotonic()-120
                self.assertFalse(server.reading_window(db))
            remote.assert_not_called()


    def test_infinite_reference_commands_are_offline(self):
        with patch.object(server,"urlopen") as remote:
            self.assertIn("0/60",self.request("chat",{"content":"Бесконечная судьба"})["reply"])
            self.assertIn("Империя разбитых созвездий",self.request("chat",{"content":"Новые великие саги"})["reply"])
            self.assertIn("страница 20/20",self.request("chat",{"content":"План романа 1000 20"})["reply"])
            self.assertIn("Глава 1",self.request("chat",{"content":"Хронология романа"})["reply"])
            self.assertIn("не установлен",self.request("chat",{"content":"Досье персонажа Герой"})["reply"])
            self.assertIn("Хакурэя",self.request("chat",{"content":"Энциклопедия романа"})["reply"])
            remote.assert_not_called()


    def test_chat_network_does_not_block_local_reader(self):
        self.request("config",{"key":"test-key","model":"test-model","consent":True})
        fake=MagicMock()
        fake.__enter__.return_value.read.return_value=json.dumps({"choices":[{"message":{"content":"Ответ"}}]}).encode()
        def remote(*args,**kwargs):
            self.assertEqual(self.request("history")["messages"][-1]["content"],"Вопрос")
            self.assertIsNone(self.request("reader")["reader"])
            with self.assertRaises(HTTPError) as err:
                self.request("chat",{"content":"Другой запрос"})
            self.assertEqual(err.exception.code,409)
            return fake
        with patch.object(server,"urlopen",side_effect=remote):
            self.assertEqual(self.request("chat",{"content":"Вопрос"})["reply"],"Ответ")
