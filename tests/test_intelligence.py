import sqlite3
import unittest
from datetime import datetime,timezone
import memory_graph
import soul_core
import soul_chronicle as c
import soul_saga as saga
import soul_intelligence as li
import soul_evolution as ev
import graph_activity as ga
from test_chronicle import draft

class IntelligenceTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db);soul_core.init(self.db);self.db.commit()
    def tearDown(self):self.db.close()
    def test_brains_and_index_recovery(self):
        p=li.prepare(self.db,saga.plan(self.db,"future"))
        self.assertEqual(p["intelligence"]["completed"],[k for k,_ in li.BRAINS])
        self.assertLessEqual(p["intelligence"]["bytes"],4200)
        self.assertEqual(li.metrics(self.db)["chapters"],13)
        self.assertEqual(li.audit_text(self.db),"целостность подтверждена")
        self.db.execute("UPDATE lit_index SET checksum='bad' WHERE number=1")
        self.assertIn("глава 1",li.audit_text(self.db))
        self.assertEqual(li.refresh(self.db,force=True),13)
        self.assertEqual(li.audit_text(self.db),"целостность подтверждена")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM chronicle_attempts").fetchone()[0],0)
    def make(self,day=1,approve=True):
        q="Лиара и Нэйрин заключили союз у серебряных ворот."
        p=draft();p["story"]=q+" Хакурэя внимательно посмотрела на них. Затем она предложила отправиться вместе к далёкой обсерватории."
        p["intelligence"]=[{"kind":"ally","subject":"Лиара","object":"Нэйрин","value":"заключили союз","quote":q,"cause":5}]
        plan=li.prepare(self.db,saga.plan(self.db,"future"))
        res=c.reserve(self.db,datetime(2099,5,day,tzinfo=timezone.utc),allow_story=True)
        c.finish(self.db,res,p,plan)
        did=c.latest_pending(self.db)["id"]
        if approve:self.assertTrue(c.decide(self.db,did,True))
        return did
    def test_source_and_spoilers(self):
        did=self.make()
        self.assertEqual(len(li.extra(self.db,did)),1)
        actors,relations=li.registry(list(li.rows(self.db)))
        self.assertIn("лиара",actors);self.assertIn("нэйрин",actors)
        self.assertEqual(len(relations),1)
        self.assertNotIn("Лиара",li.characters_text(self.db))
        ev.mark_read(self.db,14)
        self.assertIn("Лиара",li.characters_text(self.db))
        self.assertIn("Нэйрин",li.relations_text(self.db))
        self.assertIn("заключили союз",li.dossier(self.db,"Лиара"))
        self.assertEqual(li.metrics(self.db)["cross_volume"],1)
        graph=memory_graph.snapshot(self.db)
        self.assertIn("brain:coordinator",{x["key"] for x in graph["records"]})
        self.assertTrue(any(x["kind"]=="lit_rel_ally" for x in graph["edges"]))
    def test_unapproved_not_indexed_and_bad_evidence(self):
        did=self.make(approve=False)
        self.assertNotIn("лиара",li.registry(list(li.rows(self.db)))[0])
        self.assertTrue(c.decide(self.db,did,False))
        self.assertEqual(li.metrics(self.db)["chapters"],13)
        q="Лиара увидела серебряные ворота."
        with self.assertRaises(ValueError):
            li.validate(self.db,q,[{"kind":"family","subject":"Лиара","object":"Нэйрин","value":"сёстры","quote":q,"cause":None}])
    def test_brain_stage_history_keeps_all_completed_modules(self):
        with ga.track("chronicle") as key:
            for brain,_ in li.BRAINS:ga.update(key,"brain:"+brain,"brain:"+brain)
            ga.update(key,"waiting");ga.update(key,"received");ga.update(key,"saved","draft:1")
        item=next(x for x in ga.snapshot()["recent"] if x["id"]==key)
        self.assertEqual([x["stage"] for x in item["events"] if x["stage"].startswith("brain:")],["brain:"+x for x,_ in li.BRAINS])
