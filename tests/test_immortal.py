import sqlite3
import unittest
from unittest.mock import patch
from datetime import datetime,timezone
import memory_graph
import soul_core
import soul_chronicle as c
import soul_saga as s
import soul_immortal as im
import soul_reader as r
from test_omega import chapter

class ImmortalTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db);soul_core.init(self.db);self.db.commit()
    def tearDown(self):self.db.close()
    def draft(self,day=1,step=None,facts=None,story=None):
        p=chapter("Глава архива "+str(day));p.pop("literary")
        if story:p["story"]=story
        quote=p["story"][:45].rstrip()
        p["immortal"]={"step":step,"evidence":quote if step is not None else "","facts":facts or []}
        plan=im.enrich(self.db,s.plan(self.db,"future"))
        reservation=c.reserve(self.db,datetime(2099,1,day,tzinfo=timezone.utc),allow_story=True)
        c.finish(self.db,reservation,p,plan)
        return c.latest_pending(self.db)["id"]
    def fact(self,kind,key,detail,cause=None,delay=0):
        return {"kind":kind,"key":key,"detail":detail,"evidence":"Хакурэя открыла дверь серебряного архива.","cause":cause,"delay":delay}
    def test_plan(self):
        self.assertEqual(len(im.SAGAS),10)
        self.assertEqual(len(im.DAILY),10)
        self.assertEqual(len(im.ORDER),50)
        self.assertEqual(len(set(im.ORDER)),50)
        self.assertFalse(im.ready(self.db))
        self.assertIsNone(im.enrich(self.db,s.plan(self.db,"future"))["immortal"]["step"])
        with patch.object(im,"ready",return_value=True):
            self.assertEqual(im.enrich(self.db,s.plan(self.db,"future"))["immortal"]["step"],[0,0])
            did=self.draft(step=[0,0])
            self.assertTrue(c.decide(self.db,did,True))
            self.assertEqual(im.enrich(self.db,s.plan(self.db,"future"))["immortal"]["step"],[1,0])
            self.assertEqual(im.audit(self.db),[])
    def test_wrong_step(self):
        with self.assertRaises(ValueError):self.draft(step=[0,0])
    def test_clue_delay(self):
        did=self.draft(facts=[self.fact("clue","silver","Символ неизвестной силы",delay=3)])
        self.assertTrue(c.decide(self.db,did,True))
        with self.assertRaises(ValueError):self.draft(day=2,facts=[self.fact("reveal","silver","Символ объяснён",cause=14)])
    def test_law_conflict(self):
        did=self.draft(facts=[self.fact("law","space","Дар ограничен расстоянием")])
        self.assertTrue(c.decide(self.db,did,True))
        with self.assertRaises(ValueError):self.draft(day=2,facts=[self.fact("law","space","Дар не имеет ограничений")])
    def test_quality_and_graph(self):
        did=self.draft(facts=[self.fact("love","archive","Совместное исследование",cause=5)])
        self.assertIn("короткая сцена",im.read(self.db,did)["quality"]["warnings"])
        self.assertTrue(c.decide(self.db,did,True))
        self.assertNotIn(f"immortal:fact:{did}:0",{x["key"] for x in memory_graph.snapshot(self.db)["records"]})
        r.move(self.db,"chapter",14)
        self.assertIn(f"immortal:fact:{did}:0",{x["key"] for x in memory_graph.snapshot(self.db)["records"]})
        self.assertIn("индекс напряжения",im.quality_text(self.db,2))
        g=im.volume_graph(self.db,2)
        self.assertIn(f"c:{did}",{x["key"] for x in g["records"]})
        self.assertIn(f"immortal:fact:{did}:0",{x["key"] for x in g["records"]})
    def test_rejection_does_not_advance(self):
        with patch.object(im,"ready",return_value=True):
            did=self.draft(step=[0,0])
            self.assertTrue(c.decide(self.db,did,False))
            self.assertEqual(im.enrich(self.db,s.plan(self.db,"future"))["immortal"]["step"],[0,0])
    def test_indexed_volume_range_large_archive(self):
        # Synthetic index-only load test; not a browser performance claim.
        self.db.executemany("INSERT INTO omega_index VALUES(?,'future','Synthetic','Text','fixture',NULL)",((n,) for n in range(14,100001)))
        with patch.object(s,"read",return_value="Художественная глава 999. Text\n\nText"):
            g=im.volume_graph(self.db,8000)
        self.assertEqual(len(g["records"]),13)
        self.assertTrue(all(x["group"]==4 for x in g["records"]))
