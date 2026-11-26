import sqlite3
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import soul_core
import soul_chronicle as c
import soul_saga
import soul_dynasty as d
import soul_intelligence as li
import memory_graph

def base():
    return {"title":"Приговор Маюри","story":"Маюри была приговорена к казни. Перед ней закрылись двери зала, и она услышала шаги стражи. Она не понимала, чем заслужила столь страшный приговор.",
      "tags":["познание"],"emotions":{"wonder":70,"calm":80,"joy":60},"traits":{"patience":2,"curiosity":1,"warmth":-1}}

class DynastyTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db)
        soul_core.init(self.db)
    def tearDown(self):
        self.db.close()
    def plan(self,start=14,part=1):
        p=soul_saga.plan(self.db,"future")
        p.update(dynasty_lane=True,novel={"start":start,"part":part},living={"theme":"growth","head":{}},evolution={"chosen":{},"alternatives":[]})
        d.context(self.db,p)
        for key in ("novel","living","evolution"):p.pop(key)
        return p
    def test_all_stages_and_opening(self):
        self.assertEqual(len(d.BEATS),70)
        self.assertEqual(set(d.ORDER),set(range(1,71)))
        self.assertEqual(d.ORDER[:6],(11,12,13,14,15,32))
        self.assertLess(d.ORDER.index(32),d.ORDER.index(16))
        self.assertLess(d.ORDER.index(5),d.ORDER.index(6))
        self.assertTrue(d.choose_lane(self.db))
        p=self.plan()
        self.assertEqual(p["dynasty"]["selected"]["id"],11)
        self.assertIn("казни",d.instruction(p))
        self.assertIn("Маюри",d.instruction(p))
    def test_exact_quote_and_uncertainty(self):
        with self.assertRaises(ValueError):d.check(base()["story"],11,"Маюри не была приговорена к казни.")
        q="Маюри увидела человека."
        with self.assertRaises(ValueError):d.check(q,13,q)
        story=q+" Она дрожала от страха и не понимала, кто перед ней."
        self.assertEqual(d.check(story,13,q),q)
    def test_rejection_and_publication_only(self):
        p=self.plan()
        payload={**base(),"dynasty":{"step":11,"evidence":"Маюри была приговорена к казни."}}
        r=c.reserve(self.db,datetime(2099,1,1,tzinfo=timezone.utc),allow_story=True)
        c.finish(self.db,r,payload,p)
        self.assertEqual(d.completed(self.db),[])
        self.assertEqual(d.graph(self.db),([],[]))
        self.assertTrue(c.decide(self.db,1,False))
        self.assertEqual(d.next_step(self.db)["id"],11)
        r=c.reserve(self.db,datetime(2099,1,2,tzinfo=timezone.utc),allow_story=True)
        c.finish(self.db,r,payload,self.plan())
        self.assertTrue(c.decide(self.db,2,True))
        self.assertEqual(d.completed(self.db),[11])
        self.assertEqual(d.next_step(self.db)["id"],12)
        self.assertEqual(d.graph(self.db),([],[]))
        self.db.execute("UPDATE evolution_settings SET spoilers=0")
        nodes,edges=d.graph(self.db)
        self.assertTrue(any(x["key"]=="dynasty:root" for x in nodes))
        actor=next(x for x in nodes if x["key"]==li.actor_key(d.MAID))
        self.assertEqual(actor["dynasty_role"],"Приговорённая кицунэ")
        self.assertFalse(any(x["key"]==li.actor_key(d.SISTER) for x in nodes))
        self.assertFalse(any(x["kind"]=="dynasty_love" for x in edges))
        self.assertIn("Маюри была приговорена",d.character_text(self.db,"maid"))
        self.assertIsNone(self.plan(start=14,part=2)["dynasty"]["selected"])
        self.assertEqual(self.plan(start=15)["dynasty"]["selected"]["id"],12)
        self.db.execute("UPDATE dynasty_records SET checksum='damaged' WHERE draft_id=2")
        self.assertTrue(d.audit(self.db))
        self.assertEqual(d.graph(self.db),([],[]))
    def test_wrong_marker_preserves_draft_without_advancement(self):
        payload={**base(),"dynasty":{"step":12,"evidence":"Маюри была приговорена к казни."}}
        r=c.reserve(self.db,datetime(2099,1,1,tzinfo=timezone.utc),allow_story=True)
        c.finish(self.db,r,payload,self.plan())
        record=d.read(self.db,1)
        self.assertEqual(record["step"],0)
        self.assertTrue(record["warning"])
        self.assertTrue(c.decide(self.db,1,True))
        self.assertEqual(d.completed(self.db),[])
