import json
import sqlite3
import unittest
from datetime import datetime, timezone
import soul_core
import soul_chronicle as c
import soul_lore
import memory_graph

def draft():
    return {"title":"Новое открытие","story":"Хакурэя изучала устройство человеческих машин. "*5,
            "tags":["познание","достоинство"],"emotions":{"wonder":70,"calm":80,"joy":60},
            "traits":{"patience":2,"curiosity":1,"warmth":-1}}

class ChronicleTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db)
        soul_core.init(self.db)
    def tearDown(self):
        self.db.close()
    def reviews(self,start=1):
        for i in range(start,start+5):
            soul_core.review_response(self.db,i,"Ответ")
        self.assertEqual(c.collect(self.db),1)
    def test_diary_and_approval(self):
        initial=soul_lore.canon()
        self.reviews()
        self.assertEqual(c.collect(self.db),0)
        reservation=c.reserve(self.db)
        self.assertIsNotNone(reservation)
        self.assertIsNone(c.reserve(self.db))
        c.finish(self.db,reservation,draft())
        self.assertEqual(c.profile(self.db),c.BASE)
        self.assertEqual(len(c.approved(self.db)),0)
        self.assertTrue(c.decide(self.db,1,True))
        self.assertFalse(c.decide(self.db,1,True))
        self.assertEqual(c.profile(self.db)["patience"],52)
        self.assertEqual(soul_lore.canon(),initial)
        graph=memory_graph.snapshot(self.db)
        self.assertEqual({n["key"] for n in graph["records"]},{"d:1","c:1"})
        self.assertTrue(any(e["kind"]=="chronicle" for e in graph["edges"]))
        self.assertEqual(len([n for n in c.biography_graph(self.db)["nodes"] if n["kind"]=="fictional_chapter"]),13)
    def test_validation_and_failure(self):
        self.reviews()
        r=c.reserve(self.db)
        bad=draft()
        bad["traits"]["patience"]=100
        with self.assertRaises(ValueError):
            c.finish(self.db,r,bad)
        c.fail(self.db,r)
        self.assertIsNone(c.reserve(self.db))
        next_day=datetime(2099,1,1,tzinfo=timezone.utc)
        r=c.reserve(self.db,next_day)
        self.assertIsNotNone(r)
        c.finish(self.db,r,draft())
        self.db.execute("UPDATE chronicle_drafts SET checksum='bad'")
        with self.assertRaises(ValueError):
            c.decide(self.db,1,True)
        self.assertEqual(c.profile(self.db),c.BASE)
        self.assertTrue(c.decide(self.db,1,False))
    def test_canon_and_profile(self):
        self.reviews()
        soul_core.observe_user(self.db,99,"отвечай кратко")
        before=soul_core.current(self.db)
        self.db.execute("UPDATE soul_lore_versions SET checksum='invalid'")
        self.assertFalse(c.canon_ok(self.db))
        self.assertIsNone(c.reserve(self.db))
        self.assertEqual(soul_core.current(self.db),before)
    def test_prompt_no_chat_content(self):
        self.reviews()
        r=c.reserve(self.db)
        self.assertNotIn("Ответ",json.dumps(c.prompt(r,c.BASE),ensure_ascii=False))
        self.assertIn("не события легенды",c.prompt(r,c.BASE)[1]["content"])
