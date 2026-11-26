import sqlite3
import unittest
from datetime import datetime, timezone
import memory_graph
import soul_core
import soul_chronicle as c
import soul_saga as s
import soul_omega as o
import soul_guardians as g
import soul_shadow as sh
from test_omega import chapter

class GuardiansTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db);soul_core.init(self.db);self.db.commit()
    def tearDown(self):self.db.close()
    def seed_shadow(self):
        p=chapter()
        p["shadow"]={"step":0,"evidence":"Хакурэя открыла дверь серебряного архива."}
        plan=o.enrich_plan(self.db,s.plan(self.db,"future"))
        plan["shadow"]=sh.plan(self.db)
        r=c.reserve(self.db,datetime(2099,1,1,tzinfo=timezone.utc),allow_story=True)
        c.finish(self.db,r,p,plan)
        c.decide(self.db,c.latest_pending(self.db)["id"],True)
    def draft(self,day=2,step=0,quote=None):
        text="Рэйка и Токихана обсуждали ночной распорядок. Императрица спокойно выслушала обеих и объявила, что вечером её покои останутся закрытыми."
        p=chapter("Ночной распорядок")
        p["story"]=text
        p.pop("literary")
        p["guardians"]={"step":step,"evidence":quote or "Рэйка и Токихана обсуждали ночной распорядок.","memories":[
            {"actor":"reika","summary":"Обсудила распорядок с Токиханой","evidence":"Рэйка и Токихана обсуждали ночной распорядок.","other":"tokihana","relation":"сотрудничество"}]}
        plan=o.enrich_plan(self.db,s.plan(self.db,"future"))
        plan["guardians"]=g.plan(self.db)
        r=c.reserve(self.db,datetime(2099,1,day,tzinfo=timezone.utc),allow_story=True)
        c.finish(self.db,r,p,plan)
        return c.latest_pending(self.db)["id"]
    def test_cast_and_prerequisite(self):
        self.assertEqual(len(g.CAST),9)
        self.assertEqual(len({p[2] for p in g.CAST}),9)
        self.assertEqual(len(g.STEPS),30)
        self.assertIsNone(g.plan(self.db))
        self.seed_shadow()
        self.assertEqual(g.plan(self.db)["step"],0)
        self.assertIn("Рэйка",g.profiles(self.db))
        self.assertIn("Холод",g.profiles(self.db,"рэйка"))
        self.assertEqual(g.knowledge(8)["love"],"скрыта")
        self.assertEqual(g.knowledge(9)["love"],"известна свидетелям")
        self.assertEqual(g.knowledge(10)["love"],"известна всем девяти")
        self.assertEqual(g.knowledge(20)["identity"],"скрыта от хранительниц")
        self.assertEqual(g.knowledge(21)["identity"],"известна девяти")
        self.assertGreaterEqual(g.STEPS[20][0],16)
    def test_publish_graph(self):
        self.seed_shadow();did=self.draft()
        self.assertFalse(g.published(self.db))
        self.assertTrue(c.decide(self.db,did,True))
        self.assertEqual(g.plan(self.db)["step"],1)
        self.assertEqual(g.published(self.db)[0][1],15)
        self.assertIn("Обсудила распорядок",g.profiles(self.db,"рэйка"))
        graph=memory_graph.snapshot(self.db)
        nodes={n["key"]:n for n in graph["records"]}
        self.assertEqual(sum(n["kind"]=="guardian_character" for n in nodes.values()),9)
        self.assertIn("guardian:stage:0",nodes)
        self.assertIn(f"guardian:memory:{did}:0",nodes)
        self.assertTrue(any(e["kind"]=="guardian_bond" for e in graph["edges"]))
        self.assertEqual(g.audit(self.db),[])
        self.assertEqual(graph,memory_graph.snapshot(self.db))
    def test_rejection(self):
        self.seed_shadow();did=self.draft()
        self.assertTrue(c.decide(self.db,did,False))
        self.assertEqual(g.plan(self.db)["step"],0)
    def test_invalid_step(self):
        self.seed_shadow()
        with self.assertRaises(ValueError):self.draft(step=5)
    def test_invalid_quote(self):
        self.seed_shadow()
        with self.assertRaises(ValueError):self.draft(quote="Такого фрагмента нет в главе.")
    def test_integrity(self):
        self.seed_shadow();did=self.draft()
        self.db.execute("UPDATE guardian_drafts SET checksum='bad'")
        with self.assertRaises(ValueError):c.decide(self.db,did,True)
        self.assertTrue(c.decide(self.db,did,False))
