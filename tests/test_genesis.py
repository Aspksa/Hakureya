import sqlite3
import unittest
from datetime import datetime, timezone
import soul_core
import soul_chronicle as c
import soul_omega as o
import soul_saga as s
import soul_genesis as g
import memory_graph
from test_omega import chapter

class GenesisTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db);soul_core.init(self.db)
        self.db.commit()
    def tearDown(self):self.db.close()
    def make(self,alternate=False):
        val=chapter()
        val["world"]={"places":[{"name":"серебряного архива","realm":3,"description":"Хранилище древних записей","evidence":"Хакурэя открыла дверь серебряного архива."}],
                      "letter":"Я помню этот день.","perspective":"Герой смотрел на знак."}
        plan=g.enrich(self.db,o.enrich_plan(self.db,s.plan(self.db,"love")))
        plan["alternative"]=alternate
        if alternate:
            val["alternative"]={"title":"Путь к морю","story":"Утренний прибой напоминал о давно забытых путешествиях. Императрица остановилась перед водою. — Сегодня мы исследуем этот берег, — произнесла она.",
              "tags":["познание"],"emotions":{"wonder":60,"calm":70,"joy":40},"traits":{"patience":1,"curiosity":1,"warmth":0}}
        r=c.reserve(self.db,datetime(2099,1,1,tzinfo=timezone.utc),allow_story=True)
        c.finish(self.db,r,val,plan)
        return c.latest_pending(self.db)["id"]
    def test_plan_and_recall(self):
        plan=g.roadmap(self.db)
        self.assertEqual(len(plan),100)
        self.assertEqual(plan[0]["number"],14)
        self.assertEqual(plan[-1]["number"],113)
        self.assertEqual({p["arc"] for p in plan},set(o.ARCS))
        self.assertTrue(g.recall(self.db,"объятия"))
        self.assertIn("Царство 9",g.atlas(self.db))
        self.assertEqual(g.audit(self.db),[])
    def test_approval_and_graph(self):
        did=self.make()
        self.assertFalse(g.state(self.db)["places"])
        self.assertTrue(c.decide(self.db,did,True))
        self.assertEqual(g.state(self.db)["places"][0]["realm"],3)
        self.assertEqual(g.state(self.db)["consequences"][0]["from"],5)
        self.assertIn("Я помню",g.extras(self.db,14,"letter"))
        self.assertTrue(any(p["number"]==14 for p in g.recall(self.db,"серебряный архив")))
        self.assertIn("14.",g.read_arc(self.db,"love"))
        graph=memory_graph.snapshot(self.db)
        nodes={n["key"]:n for n in graph["records"]}
        self.assertEqual(nodes[f"c:{did}"]["sector"],"love")
        self.assertIn("segment:love:2",nodes)
        self.assertIn("realm:3",nodes)
        self.assertIn("law:immunity",nodes)
        self.assertEqual(g.audit(self.db),[])
        self.db.execute("UPDATE omega_index SET story='damaged' WHERE number=14")
        self.assertTrue(g.audit(self.db))
    def test_variant_selection(self):
        did=self.make(True)
        self.assertIn("Путь к морю",g.variants(self.db))
        self.assertTrue(g.select_variant(self.db,2))
        self.assertEqual(c.latest_pending(self.db)["title"],"Путь к морю")
        self.assertEqual(g.world(self.db,did)["places"],[])
        self.assertTrue(g.select_variant(self.db,1))
        self.assertEqual(c.latest_pending(self.db)["title"],"Серебряный архив")
        self.assertTrue(c.decide(self.db,did,True))
        self.assertFalse(g.select_variant(self.db,2))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM genesis_edits").fetchone()[0],2)
    def test_world_contradiction(self):
        did=self.make();c.decide(self.db,did,True)
        story="Хакурэя открыла дверь серебряного архива."
        w={"places":[{"name":"серебряного архива","realm":4,"description":"Архив","evidence":story}],"letter":"","perspective":""}
        with self.assertRaises(ValueError):g.validate_world(self.db,story,w)
    def test_corrupted_world_blocks_publication(self):
        did=self.make()
        self.db.execute("UPDATE genesis_world SET checksum='invalid'")
        with self.assertRaises(ValueError):c.decide(self.db,did,True)
        self.assertTrue(c.decide(self.db,did,False))
