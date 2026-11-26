import sqlite3
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
import soul_core
import soul_chronicle as c
import soul_director as d
import soul_omega as o
import soul_saga
import memory_graph

def base():
    return {"title":"Открытие в архиве","story":"Хакурэя остановилась у древнего архива. — Мы узнаем причину, а потом решим, как поступить. "*4,
      "tags":["познание"],"emotions":{"wonder":70,"calm":80,"joy":60},"traits":{"patience":2,"curiosity":1,"warmth":-1}}

class DirectorTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db)
        soul_core.init(self.db)
    def tearDown(self):
        self.db.close()
    def plan(self,part=1):
        p=soul_saga.plan(self.db,"future")
        p.update(evolution={"chosen":{"scene":0,"theme":"growth","title":"Текущий эпизод","guide":"Продолжай."},"alternatives":[]},
                 novel={"part":part},living={"theme":"growth","head":{}},infinite={"selected":None})
        # Test the free director after the existing milestone prerequisites are met.
        with patch.object(d.inf,"ready",return_value=True),patch.object(d.inf,"remaining",return_value=[]):
            d.context(self.db,p)
        # Keep test drafts legacy-compatible; the director data itself requires no new output fields.
        for key in ("evolution","novel","living","infinite"):p.pop(key)
        return p
    def test_candidate_variety_and_pacing(self):
        a=d.choose_candidates(30,[{"theme":"love"}]*8,[{"subject":"Письмо","chapter":14}],[])
        self.assertEqual(a[0]["theme"],"mystery")
        self.assertEqual(len({x["theme"] for x in a}),4)
        self.assertEqual(d.pace([{"tension":90},{"tension":70}])[0],"последствия и передышка")
        self.assertEqual(d.phase(24),"выбор и последствия")
    def test_fixed_plan_has_priority(self):
        p=soul_saga.plan(self.db,"past")
        d.context(self.db,p)
        self.assertTrue(p["director"]["fixed"])
        self.assertIsNone(p["director"]["cycle"])
    def test_publication_not_pending_advances_cycle(self):
        p=self.plan()
        self.assertEqual(p["director"]["cycle"]["part"],1)
        self.assertEqual(p["director"]["number"],14)
        self.assertEqual(len(p["director"]["forecast"]),3)
        r=c.reserve(self.db,datetime(2099,1,1,tzinfo=timezone.utc),allow_story=True)
        self.assertIsNotNone(r)
        c.finish(self.db,r,base(),p)
        self.assertEqual(d.published(self.db),[])
        self.assertEqual(d.graph(self.db),([],[]))
        self.assertEqual(self.plan()["director"]["cycle"]["part"],1)
        self.assertTrue(c.decide(self.db,1,True))
        self.db.execute("UPDATE evolution_settings SET spoilers=0")
        self.assertEqual(d.published(self.db)[0][0],14)
        self.assertEqual(self.plan()["director"]["cycle"]["part"],2)
        nodes,edges=d.graph(self.db)
        self.assertTrue(any(x["kind"]=="director_saga" for x in nodes))
        self.assertTrue(any(x["kind"]=="director_part" and x["b"]=="c:1" for x in edges))
        self.assertIn("Том 2",d.report(self.db,"forecast"))
        self.assertIn("Причина выбора",d.report(self.db,"decision"))
        self.assertIn("аннотация",d.report(self.db,"annotation"))
        self.db.execute("UPDATE evolution_settings SET spoilers=1")
        self.assertEqual(d.graph(self.db),([],[]))
        self.db.execute("UPDATE story_director SET checksum='damaged'")
        with self.assertRaises(ValueError):d.read(self.db,1)
        self.assertEqual(d.graph(self.db),([],[]))
