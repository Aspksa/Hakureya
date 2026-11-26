import sqlite3
import unittest
from datetime import datetime, timezone
import memory_graph
import soul_core
import soul_chronicle as c
import soul_saga as s
import soul_omega as o
import soul_shadow as sh
from test_omega import chapter

class ShadowTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db);soul_core.init(self.db);self.db.commit()
    def tearDown(self):self.db.close()
    def draft(self,day=1,step=0,quote="Хакурэя открыла дверь серебряного архива."):
        p=chapter()
        p["shadow"]={"step":step,"evidence":quote}
        plan=o.enrich_plan(self.db,s.plan(self.db,"future"))
        plan["shadow"]=sh.plan(self.db)
        r=c.reserve(self.db,datetime(2099,1,day,tzinfo=timezone.utc),allow_story=True)
        c.finish(self.db,r,p,plan)
        return c.latest_pending(self.db)["id"]
    def test_order_and_graph(self):
        self.assertEqual(len(sh.STEPS),18)
        self.assertEqual(sh.plan(self.db)["step"],0)
        did=self.draft()
        self.assertEqual(sh.plan(self.db)["step"],0)
        self.assertFalse(any(n["key"].startswith("shadow:event:") for n in memory_graph.snapshot(self.db)["records"]))
        self.assertTrue(c.decide(self.db,did,True))
        self.assertEqual(sh.plan(self.db)["step"],1)
        graph=memory_graph.snapshot(self.db)
        self.assertIn("shadow:event:0",{n["key"] for n in graph["records"]})
        self.assertTrue(any(e["a"]==f"c:{did}" and e["b"]=="shadow:event:0" for e in graph["edges"]))
        self.assertEqual(sh.audit(self.db),[])
    def test_rejection(self):
        did=self.draft()
        self.assertTrue(c.decide(self.db,did,False))
        self.assertEqual(sh.plan(self.db)["step"],0)
    def test_wrong_step(self):
        with self.assertRaises(ValueError):self.draft(step=5)
    def test_false_evidence(self):
        with self.assertRaises(ValueError):self.draft(quote="Такого фрагмента в главе нет.")
    def test_corruption(self):
        did=self.draft()
        self.db.execute("UPDATE shadow_drafts SET checksum='bad'")
        with self.assertRaises(ValueError):c.decide(self.db,did,True)
        self.assertTrue(c.decide(self.db,did,False))
