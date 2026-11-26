import json
import sqlite3
import unittest
from datetime import datetime, timezone
import writer_volume as v
import soul_chronicle as c
import soul_core
import memory_graph
import soul_evolution as e

class WriterVolumeTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db)
        soul_core.init(self.db)
        self.day="2099-01-01"
        self.now=datetime(2099,1,1,tzinfo=timezone.utc)

    def test_legacy_and_multiple_attempt_ids(self):
        a=c.reserve(self.db,self.now,allow_story=True)
        self.assertEqual(a[0],self.day)
        self.assertIsNone(c.reserve(self.db,self.now,allow_story=True))
        c.fail(self.db,a)
        self.assertIsNone(c.reserve(self.db,self.now,allow_story=True))
        v.set_target(self.db,15)
        self.assertTrue(v.auto_block(self.db,self.day))
        b=c.reserve(self.db,self.now,allow_story=True)
        self.assertEqual(b[0],self.day+"#0002")
        self.assertNotEqual(a[1],b[1])
        self.assertIsNone(c.reserve(self.db,self.now,allow_story=True))
        c.recover(self.db)
        self.assertEqual(len(v.attempts(self.db,self.day)),2)
        self.assertEqual(v.attempts(self.db,self.day)[1][1],"interrupted")

    def test_budget_per_attempt(self):
        v.set_target(self.db,15)
        e.set_budget(self.db,"writer",1000,2000,100000)
        for key in (self.day,self.day+"#0002"):
            allowed,details=e.budget_check(self.db,"writer",[{"content":"chapter"}],1800,key)
            self.assertTrue(allowed)
            e.reserve_cost(self.db,key,"writer",details)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM evolution_cost").fetchone()[0],2)

    def test_only_published_prose_counts(self):
        v.set_target(self.db,15)
        self.db.execute("INSERT INTO chronicle_drafts(diary_id,canon_hash,payload,checksum,status,decided) VALUES(?,?,?,?,?,?)",(-100,"hash",json.dumps({"story":"a"*27000}),"sum","pending",self.day))
        self.assertEqual(v.published_chars(self.db,self.day),0)
        self.db.execute("UPDATE chronicle_drafts SET status='approved'")
        self.assertEqual(v.published_chars(self.db,self.day),27000)
        self.assertIsNone(v.next_id(self.db,self.day))
        self.assertEqual(v.next_id(self.db,self.day,editor=True),self.day)

    def test_safety_ceiling(self):
        v.set_target(self.db,15)
        for i in range(v.MAX_ATTEMPTS):
            key=v.next_id(self.db,self.day)
            self.assertIsNotNone(key)
            self.db.execute("INSERT INTO chronicle_attempts(day,diary_id,status) VALUES(?,?,'failed')",(key,-i-1))
        self.assertIsNone(v.next_id(self.db,self.day))
