import sqlite3
import unittest
from datetime import datetime, timezone
import memory_graph
import soul_core
import soul_chronicle as c
import soul_saga as s
import soul_omega as o
import soul_genesis as g
import soul_romance as r
from test_omega import chapter

class RomanceTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db);soul_core.init(self.db);self.db.commit()
    def tearDown(self): self.db.close()
    def draft(self,day=1,value=None):
        plan=r.enrich(self.db,g.enrich(self.db,o.enrich_plan(self.db,s.plan(self.db,"love"))))
        reservation=c.reserve(self.db,datetime(2099,1,day,tzinfo=timezone.utc),allow_story=True)
        self.assertIsNotNone(reservation)
        c.finish(self.db,reservation,value or chapter(),plan)
        return c.latest_pending(self.db)["id"]
    def test_index_and_planning(self):
        self.assertEqual(len(list(r.memory(self.db))),13)
        self.assertEqual(r.choose(self.db,"past")["romance"],"без романтики до встречи")
        old=r.choose(self.db,"love")
        did=self.draft()
        self.assertEqual(r.choose(self.db,"love"),old)
        self.assertTrue(c.decide(self.db,did,True))
        self.assertNotEqual(r.choose(self.db,"love"),old)
        self.assertEqual(len(list(r.memory(self.db))),14)
        self.assertTrue(r.report(self.db,did)["words"]>0)
    def test_repeat_detection(self):
        story="Она внимательно изучала древнюю книгу и вдруг заметила в конце страницы незнакомый знак старого царства."
        raw=o.dump(r.profile("Исследование",story))
        self.db.execute("UPDATE romance_scenes SET payload=?,checksum=? WHERE number=1",(raw,o.digest(raw)))
        with self.assertRaises(ValueError):
            r.review(self.db,"Другой заголовок","Вступление. "+story+" Последствие.")
    def test_cycle(self):
        self.assertTrue(r.start_cycle(self.db,"романтическая","love"))
        self.assertFalse(r.start_cycle(self.db,"большая","love"))
        did=self.draft()
        self.assertFalse(r.parts(self.db,1))
        self.assertFalse(r.close_cycle(self.db))
        self.assertTrue(c.decide(self.db,did,True))
        self.assertEqual(len(r.parts(self.db,1)),1)
        self.assertIn("Серебряный архив",r.read_cycle(self.db,1))
        p=r.enrich(self.db,s.plan(self.db,"love"))["romance"]
        self.assertEqual(p["part"],2)
        self.assertEqual(p["continuation"]["chapter"],14)
        graph=memory_graph.snapshot(self.db)
        self.assertIn("romance-cycle:1",{n["key"] for n in graph["records"]})
        self.assertTrue(r.close_cycle(self.db))
        self.assertIsNone(r.current_cycle(self.db))
    def test_rejection_and_integrity(self):
        self.assertTrue(r.start_cycle(self.db,"обычная","love"))
        did=self.draft()
        self.db.execute("UPDATE romance_drafts SET checksum='bad'")
        with self.assertRaises(ValueError):c.decide(self.db,did,True)
        self.assertTrue(c.decide(self.db,did,False))
        self.assertFalse(r.parts(self.db,1))
        self.assertEqual(len(list(r.memory(self.db))),13)
    def test_target_completion(self):
        r.start_cycle(self.db,"обычная","love")
        self.db.execute("UPDATE romance_cycles SET target=1")
        did=self.draft()
        self.assertTrue(c.decide(self.db,did,True))
        self.assertIsNone(r.current_cycle(self.db))
        self.assertEqual(self.db.execute("SELECT status FROM romance_cycles").fetchone()[0],"complete")
