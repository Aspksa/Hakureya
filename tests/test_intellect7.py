import sqlite3
import unittest
from datetime import datetime,timezone
from unittest.mock import patch
import soul_core
import soul_chronicle as ch
import soul_intellect as i
import soul_intelligence as li
import soul_universe as u
import soul_saga
import soul_evolution as ev
import soul_atlas
import memory_graph
import graph_activity
import writer_stream
from test_chronicle import draft
from test_writer_stream import Response,chunk

class Intellect7Test(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db);soul_core.init(self.db);self.db.commit()

    def publish(self,day,quote,fact):
        plan=li.prepare(self.db,soul_saga.plan(self.db,"future"))
        payload=draft()
        payload["title"]="Новая сцена "+str(day)
        payload["story"]=quote+" Затем путники остановились возле дальнего входа. За воротами их ожидали новые открытия и непростые разговоры."
        payload["intelligence"]=[dict(fact,quote=quote)]
        res=ch.reserve(self.db,datetime(2099,5,day,tzinfo=timezone.utc),allow_story=True)
        ch.finish(self.db,res,payload,plan)
        did=ch.latest_pending(self.db)["id"]
        self.assertTrue(ch.decide(self.db,did,True))
        return did

    def test_exact_canon_and_recovery(self):
        self.assertEqual(i.refresh(self.db),13)
        self.assertEqual(i.refresh(self.db),0)
        facts=i.rows(self.db,li.actor_key("Хакурэя"))
        self.assertTrue(any(f["kind"]=="voice" for f in facts))
        self.assertTrue(any(f["kind"]=="artifact" for f in facts))
        self.assertTrue(any(f["kind"]=="origin" for f in facts))
        self.assertIn("целостность подтверждена",i.audit(self.db))
        eid=facts[0]["id"]
        self.db.execute("DELETE FROM intellect_evidence WHERE id=?",(eid,))
        self.assertIn("Неполный",i.audit(self.db))
        self.assertIn("целостность подтверждена",i.report(self.db,"repair"))
        self.assertIn("Канон: OK",i.module_audit(self.db))

    def test_context_is_bounded_and_exact(self):
        plan=soul_saga.plan(self.db,"future")
        plan["universe"]={"title":"подарок и первая снежинка","lens":"прошлое"}
        ctx=i.prepare(self.db,plan)
        self.assertLessEqual(len(li.o.dump(ctx).encode()),3800)
        self.assertTrue(ctx["refs"])
        for r in ctx["refs"]:
            source=self.db.execute("SELECT story FROM omega_index WHERE number=?",(r["chapter"],)).fetchone()[0]
            self.assertIn(r["quote"],source)
        self.assertIn("Eternal Intelligence",i.instruction(plan))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM chronicle_attempts").fetchone()[0],0)

    def test_same_name_and_spoiler_separation(self):
        q1="Лиара была хранительницей северных ворот."
        q2="Лиара была лекарем из южного царства."
        for day,q,value in ((1,q1,"хранительницей северных ворот"),(2,q2,"лекарем из южного царства")):
            self.publish(day,q,{"kind":"biography","subject":"Лиара","object":"","value":value,"cause":None})
        i.refresh(self.db)
        self.assertFalse(i.rows(self.db,li.actor_key("Лиара")))
        ev.mark_read(self.db,14);ev.mark_read(self.db,15)
        a=i.create_identity(self.db,"Лиара",14,q1)
        b=i.create_identity(self.db,"Лиара",15,q2)
        self.assertNotEqual(a,b)
        for f in i.rows(self.db,li.actor_key("Лиара"),"biography"):
            i.assign_identity(self.db,f["id"],a if f["chapter"]==14 else b)
        self.assertIn(q1,i.report(self.db,"profile",a))
        self.assertNotIn(q2,i.report(self.db,"profile",a))
        self.assertIn(q2,i.report(self.db,"profile",b))
        nodes=memory_graph.snapshot(self.db)["records"]
        self.assertTrue({a,b}.issubset({n["key"] for n in nodes}))

    def test_knowledge_transfer_and_world_time(self):
        q="Лиара сообщила Нэйрин о тайном входе."
        self.publish(1,q,{"kind":"knowledge_transfer","subject":"Лиара","object":"Нэйрин","value":"о тайном входе","cause":None})
        self.assertNotIn("Лиара",i.report(self.db,"knowledge"))
        ev.mark_read(self.db,14)
        self.assertIn("Лиара → Нэйрин",i.report(self.db,"knowledge"))
        with self.assertRaises(ValueError):
            li.validate(self.db,q,[{"kind":"knowledge_transfer","subject":"Лиара","object":"","value":"о тайном входе","quote":q,"cause":None}])

    def test_atlas_100000_synthetic_index_rows(self):
        # This is deliberately an aggregate/range scaling fixture, not 100000 genuine chapters.
        self.db.execute("""WITH RECURSIVE seq(n) AS (SELECT 14 UNION ALL SELECT n+1 FROM seq WHERE n<100000)
            INSERT INTO omega_index SELECT n,'future','fixture','fixture','fixture',n FROM seq""")
        root=soul_atlas.snapshot(self.db)
        self.assertEqual(root["total"],100000)
        self.assertLessEqual(len(root["records"]),96)
        self.assertEqual(sum(r["chapter_count"] for r in root["records"]),100000)
        key=root["records"][0]["key"]
        self.assertTrue(key.startswith("atlas:"))
        _,a,b=key.split(":")
        child=soul_atlas.snapshot(self.db,int(a),int(b))
        self.assertLessEqual(len(child["records"]),96)
        self.assertEqual(sum(r["chapter_count"] for r in child["records"]),root["records"][0]["chapter_count"])
        with self.assertRaises(ValueError):soul_atlas.snapshot(self.db,0,1)

    def test_safe_interrupted_checkpoint(self):
        res=ch.reserve(self.db,allow_story=True)
        u.save_fragment(self.db,res[0],"Не завершённая сцена","stream_checkpoint")
        ch.recover(self.db)
        self.assertEqual(self.db.execute("SELECT reason FROM universe_fragments").fetchone()[0],"interrupted")
        self.assertEqual(self.db.execute("SELECT status FROM chronicle_attempts").fetchone()[0],"interrupted")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM chronicle_drafts").fetchone()[0],0)

    def test_stream_deadline_and_measured_activity(self):
        with patch.object(writer_stream,"monotonic",side_effect=[0,301]):
            with self.assertRaises(TimeoutError):writer_stream.read_response(Response(chunk("text","stop")),lambda *_:None)
        with graph_activity.track("chronicle") as key:
            graph_activity.update(key,"brain:memory","brain:memory",2.5)
            graph_activity.update(key,"waiting")
            graph_activity.progress(key,100,2)
            graph_activity.prose(key,73)
            st=next(x for x in graph_activity.snapshot()["active"] if x["id"]==key)
            self.assertEqual(st["prose_chars"],73)
            self.assertEqual(next(x for x in st["events"] if x["stage"]=="brain:memory")["duration_ms"],2.5)
            self.assertIn("age_seconds",st)
            self.assertNotIn("_heartbeat",st)
