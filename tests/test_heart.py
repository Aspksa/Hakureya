import sqlite3
import unittest
from datetime import datetime, timezone
import memory_graph
import soul_core
import soul_chronicle as c
import soul_heart as h
import soul_saga as s
import soul_omega as o
import soul_genesis as g
from test_omega import chapter

def value():
    p=chapter()
    p["heart"]={"moments":[{"topic":"trust","title":"Совместное открытие архива",
        "evidence":"Хакурэя открыла дверь серебряного архива.","before":"любопытство" if False else "удивление",
        "after":"доверие","cause":7,"effect":"На странице сиял неизвестный символ.",
        "thread":{"key":"archive-choice","action":"open","title":"Доверие в архиве"}}]}
    return p

class HeartTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db);soul_core.init(self.db);self.db.commit()
    def tearDown(self):self.db.close()
    def create(self,p=None,arc="love"):
        r=c.reserve(self.db,datetime(2099,1,1,tzinfo=timezone.utc),allow_story=True)
        plan=h.enrich(self.db,o.enrich_plan(self.db,s.plan(self.db,arc)))
        c.finish(self.db,r,p or value(),plan)
        return c.latest_pending(self.db)["id"]
    def test_canon(self):
        self.assertEqual(len(list(h.canon_events(self.db))),9)
        self.assertIn("Я люблю тебя.",h.timeline(self.db))
        self.assertEqual(h.choose(self.db,"past")["topic"],"memory")
        graph=memory_graph.snapshot(self.db)
        keys={n["key"] for n in graph["records"]}
        self.assertIn("heart:root",keys)
        self.assertIn("heart:canon:5",keys)
        self.assertTrue(all(n["group"]==4 for n in graph["records"]))
    def test_approval_and_stable_slots(self):
        did=self.create()
        self.assertFalse(h.threads(self.db))
        self.assertFalse(any(p["source"]=="approved" for p in h.published(self.db)))
        before=memory_graph.snapshot(self.db)
        self.assertTrue(c.decide(self.db,did,True))
        after=memory_graph.snapshot(self.db)
        key=f"heart:moment:{did}:0"
        self.assertIn(key,{n["key"] for n in after["records"]})
        self.assertTrue(any(e["a"]=="canon:7" and e["b"]==key and e["kind"]=="heart_cause" for e in after["edges"]))
        self.assertTrue(any(e["a"]==key and e["kind"]=="heart_effect" for e in after["edges"]))
        self.assertEqual(h.threads(self.db)["archive-choice"]["opened"],14)
        self.assertIn("глава 14",h.thread_text(self.db))
        self.assertIn("Совместное открытие",h.timeline(self.db,"trust"))
        slots={n["key"]:n["heart_slot"] for n in before["records"] if "heart_slot" in n}
        self.assertTrue(all(n["heart_slot"]==slots[n["key"]] for n in after["records"] if n["key"] in slots))
        self.assertEqual(after,memory_graph.snapshot(self.db))
    def test_false_evidence(self):
        p=value();p["heart"]["moments"][0]["effect"]="Не было написано"
        with self.assertRaises(ValueError):self.create(p)
    def test_past_no_romantic_moment(self):
        with self.assertRaises(ValueError):self.create(arc="past")
    def test_bad_reference(self):
        p=value();p["heart"]["moments"][0]["cause"]=999
        with self.assertRaises(ValueError):self.create(p)
    def test_corruption_and_rejection(self):
        did=self.create()
        self.db.execute("UPDATE heart_drafts SET checksum='bad'")
        with self.assertRaises(ValueError):c.decide(self.db,did,True)
        self.assertTrue(c.decide(self.db,did,False))
        self.assertFalse(h.threads(self.db))
    def test_variant_metadata(self):
        import soul_romance
        p=value()
        p["alternative"]={"title":"Путь к морю","story":"Утренний прибой напоминал о давно забытых путешествиях. Императрица остановилась перед водою. — Сегодня мы исследуем этот берег, — произнесла она.",
          "tags":["познание"],"emotions":{"wonder":60,"calm":70,"joy":40},"traits":{"patience":1,"curiosity":1,"warmth":0}}
        plan=h.enrich(self.db,soul_romance.enrich(self.db,g.enrich(self.db,o.enrich_plan(self.db,s.plan(self.db,"love")))))
        plan["alternative"]=True
        reservation=c.reserve(self.db,datetime(2099,1,1,tzinfo=timezone.utc),allow_story=True)
        c.finish(self.db,reservation,p,plan)
        did=c.latest_pending(self.db)["id"]
        self.assertTrue(g.select_variant(self.db,2))
        self.assertEqual(h.read(self.db,did)["moments"],[])
        self.assertTrue(g.select_variant(self.db,1))
        self.assertEqual(len(h.read(self.db,did)["moments"]),1)
        self.assertTrue(c.decide(self.db,did,True))
