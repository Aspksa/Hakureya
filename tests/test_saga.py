import sqlite3
import unittest
from datetime import datetime, timezone
import soul_core
import soul_chronicle as c
import soul_saga as s
import soul_lore
import memory_graph
from test_chronicle import draft

class SagaTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db)
        soul_core.init(self.db)
    def tearDown(self):
        self.db.close()
    def create(self,day,arc):
        reservation=c.reserve(self.db,datetime(2099,1,day,tzinfo=timezone.utc),allow_story=True)
        self.assertIsNotNone(reservation)
        plan=s.plan(self.db,arc)
        c.finish(self.db,reservation,draft(),plan)
        return c.latest_pending(self.db)["id"]
    def test_growth_without_fabricated_diary(self):
        original=soul_lore.canon()
        self.assertIsNone(c.reserve(self.db))
        did=self.create(1,"love")
        self.assertEqual(c.status(self.db)["diary_entries"],0)
        self.assertIn("не найдена",s.read(self.db,14))
        self.assertTrue(c.decide(self.db,did,True))
        self.assertIn("Глава",s.read(self.db,5))
        self.assertIn("глава 14",s.read(self.db,14))
        self.assertIn("История любви",s.contents(self.db))
        self.assertEqual(s.plan(self.db,"love")["parent"],did)
        graph=memory_graph.snapshot(self.db)
        self.assertTrue(any(e["a"]=="arc:love" and e["b"]==f"c:{did}" for e in graph["edges"]))
        self.assertFalse(any(n["key"].startswith("d:") for n in graph["records"]))
        self.assertEqual(soul_lore.canon(),original)
        self.assertIn("Утверждённые художественные продолжения",soul_core.system_prompt(self.db,"test","наша история любви"))
    def test_rejection_and_numbering(self):
        a=self.create(1,"past")
        c.decide(self.db,a,False)
        b=self.create(2,"meeting")
        c.decide(self.db,b,True)
        self.assertEqual(s.reading_rows(self.db)[0]["number"],14)
        self.assertEqual(s.reading_rows(self.db)[0]["id"],b)
        soul_core.init(self.db)
        self.assertEqual(s.reading_rows(self.db)[0]["number"],14)
        self.assertIsNone(c.reserve(self.db,datetime(2099,1,2,tzinfo=timezone.utc),allow_story=True))
    def test_cross_day_reservation_and_canon(self):
        r=c.reserve(self.db,datetime(2099,1,1,tzinfo=timezone.utc),allow_story=True)
        self.assertIsNone(c.reserve(self.db,datetime(2099,1,2,tzinfo=timezone.utc),allow_story=True))
        c.fail(self.db,r)
        self.db.execute("UPDATE soul_lore_versions SET checksum='bad'")
        self.assertIsNone(c.reserve(self.db,datetime(2099,1,2,tzinfo=timezone.utc),allow_story=True))
        self.assertIn("нарушена",s.read(self.db,1))
    def test_migrate_previous_chapters(self):
        did=self.create(1,"future")
        c.decide(self.db,did,True)
        self.db.execute("DELETE FROM saga_arcs")
        soul_core.init(self.db)
        self.assertEqual(s.reading_rows(self.db)[0]["number"],14)
        self.assertEqual(s.reading_rows(self.db)[0]["id"],did)
