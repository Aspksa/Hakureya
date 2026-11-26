import sqlite3
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
import memory_graph
import soul_core
import soul_chronicle as c
import soul_saga as s
import soul_omega as o
import soul_living as l
from test_omega import chapter

class LivingTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"data.sqlite3"
        self.db=self.connect()
    def connect(self):
        db=sqlite3.connect(self.path)
        db.execute("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(db);soul_core.init(db);db.commit()
        return db
    def tearDown(self):
        self.db.close();self.tmp.cleanup()
    def draft(self,background=False,quote=None):
        p=chapter("Новая глава из архива")
        p["living"]={"facts":[{"kind":"goal","name":"Хакурэя","detail":"Исследование древнего архива","evidence":quote or "Хакурэя открыла дверь серебряного архива.","cause":13}]}
        plan=o.enrich_plan(self.db,s.plan(self.db,"future"))
        l.enrich(self.db,plan,background)
        r=c.reserve(self.db,datetime(2099,1,1,tzinfo=timezone.utc),allow_story=True)
        c.finish(self.db,r,p,plan)
        return c.latest_pending(self.db)["id"]
    def test_defaults_restart_queue(self):
        self.assertEqual(l.mode(self.db),"off")
        q=l.queue(self.db)
        self.assertEqual(len(q["items"]),100)
        self.assertEqual(q["items"][0]["title"],"Два мира одной императрицы")
        self.assertEqual(q["items"][1]["title"],"Девять хранительниц возвращаются")
        self.assertEqual(q["items"][0]["number"],14)
        l.set_mode(self.db,"draft")
        self.db.commit();self.db.close();self.db=self.connect()
        self.assertEqual(l.mode(self.db),"draft")
        self.assertEqual(q,l.queue(self.db))
        l.set_mode(self.db,"off")
        self.assertEqual(l.mode(self.db),"off")
    def test_manual_and_graph(self):
        did=self.draft()
        l.set_mode(self.db,"auto")
        self.assertFalse(l.publish_if_allowed(self.db,did))
        self.assertFalse(list(l.published(self.db)))
        self.assertTrue(c.decide(self.db,did,True))
        self.assertEqual(len(list(l.published(self.db))),1)
        self.assertEqual(l.queue(self.db)["items"][0]["number"],15)
        graph=memory_graph.snapshot(self.db)
        self.assertIn(f"living:fact:{did}:0",{n["key"] for n in graph["records"]})
        self.assertTrue(any(e["kind"]=="living_cause" for e in graph["edges"]))
    def test_auto_gate_and_savepoint(self):
        did=self.draft(True)
        l.set_mode(self.db,"auto")
        self.assertFalse(l.eligible(self.db,did))
        with patch.object(l,"eligible",return_value=True):
            self.assertTrue(l.publish_if_allowed(self.db,did))
        self.assertEqual(len(list(l.published(self.db))),1)
        self.assertIn("14.",l.news(self.db))
    def test_bad_quote(self):
        with self.assertRaises(ValueError):self.draft(quote="Такой цитаты нет в главе.")
    def test_backup(self):
        l.set_mode(self.db,"draft");self.db.commit()
        folder=Path(self.tmp.name)/"backups"
        name=l.backup(self.path,folder)
        self.assertTrue((folder/name).is_file())
        restored=sqlite3.connect(folder/name)
        try:
            self.assertEqual(l.mode(restored),"draft")
            self.assertEqual(restored.execute("PRAGMA quick_check").fetchone()[0],"ok")
        finally:restored.close()
        self.assertEqual(l.backup(self.path,folder),name)
    def test_damaged_record(self):
        did=self.draft()
        self.db.execute("UPDATE living_records SET checksum='bad'")
        with self.assertRaises(ValueError):c.decide(self.db,did,True)
        self.assertTrue(c.decide(self.db,did,False))
