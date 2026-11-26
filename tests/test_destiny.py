import sqlite3
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
import memory_graph
import soul_core
import soul_chronicle as c
import soul_saga as s
import soul_omega as o
import soul_destiny as d
from test_omega import chapter

class DestinyTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db);soul_core.init(self.db);self.db.commit()
    def tearDown(self):self.db.close()
    def draft(self,beat=1,day=1,quote=None):
        p=chapter("Вечер без церемоний")
        p.pop("literary")
        p["story"]="Хакурэя и герой отправились из первого царства во второе. В тихом саду они долго обсуждали новую прогулку и обещали встретиться снова."
        evidence="Хакурэя и герой отправились из первого царства во второе."
        p["destiny"]={"beat":beat,"evidence":quote or evidence,"facts":[
            {"kind":"travel","subject":"empress","detail":"Путешествие между двумя царствами","evidence":evidence,"cause":13,"realm":2,"origin":1}]}
        plan=o.enrich_plan(self.db,s.plan(self.db,"future"))
        plan["destiny"]=d.plan(self.db)
        r=c.reserve(self.db,datetime(2099,1,day,tzinfo=timezone.utc),allow_story=True)
        c.finish(self.db,r,p,plan)
        return c.latest_pending(self.db)["id"]
    def test_roadmap(self):
        self.assertEqual(len(d.BEATS),70)
        self.assertEqual(len(d.GRAPH_ITEMS),10)
        self.assertEqual(len(d.ORDER),70)
        self.assertEqual(set(d.ORDER),set(range(1,71)))
        self.assertEqual(d.ORDER[-1],70)
        self.assertLess(d.ORDER.index(50),d.ORDER.index(52))
        self.assertEqual(len(d.CAST),10)
        self.assertIsNone(d.plan(self.db))
        self.assertIn("Ожидает завершения",d.status(self.db))
        self.assertIn("70.",d.status(self.db,True))
        self.assertIn("80.",d.status(self.db,True))
        self.assertIn("Иори",d.characters(self.db))
    def test_approval_and_graph(self):
        with patch.object(d,"ready",return_value=True):
            self.assertEqual(d.plan(self.db)["beat"],1)
            did=self.draft()
            self.assertFalse(d.published(self.db))
            self.assertTrue(c.decide(self.db,did,True))
            self.assertEqual(d.plan(self.db)["beat"],11)
            nodes=memory_graph.snapshot(self.db)
            keys={n["key"] for n in nodes["records"]}
            self.assertIn("destiny:event:1",keys)
            self.assertIn(f"destiny:fact:{did}:0",keys)
            self.assertTrue(any(e["kind"]=="destiny_departure" and e["a"]=="realm:1" for e in nodes["edges"]))
            self.assertTrue(any(e["kind"]=="destiny_cause" and e["a"]=="canon:13" for e in nodes["edges"]))
            self.assertIn("Путешествие",d.timeline(self.db,"travel"))
            self.assertEqual(d.audit(self.db),[])
    def test_reject(self):
        with patch.object(d,"ready",return_value=True):
            did=self.draft()
            self.assertTrue(c.decide(self.db,did,False))
            self.assertEqual(d.plan(self.db)["beat"],1)
            self.assertFalse(d.published(self.db))
    def test_gate(self):
        with self.assertRaises(ValueError):self.draft()
    def test_wrong_beat(self):
        with patch.object(d,"ready",return_value=True):
            with self.assertRaises(ValueError):self.draft(beat=70)
    def test_wrong_quote(self):
        with patch.object(d,"ready",return_value=True):
            with self.assertRaises(ValueError):self.draft(quote="Этой цитаты нет в рассказе.")
    def test_corrupt(self):
        with patch.object(d,"ready",return_value=True):
            did=self.draft()
            self.db.execute("UPDATE destiny_drafts SET checksum='bad'")
            with self.assertRaises(ValueError):c.decide(self.db,did,True)
            self.assertTrue(c.decide(self.db,did,False))
