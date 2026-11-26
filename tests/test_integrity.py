import sqlite3
import tempfile
import unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
import instance_guard
import memory_graph
import soul_core
import soul_chronicle as c
import soul_intelligence as li
import soul_reader as reader
import soul_evolution as ev
import soul_saga as saga
import soul_novel as novel
from test_chronicle import draft

class SystemIntegrityTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db);soul_core.init(self.db);self.db.commit()
    def tearDown(self):self.db.close()
    def make(self,day=1,story=None,approve=True,plan=None,extra=None):
        p=draft()
        if story:p["story"]=story
        if extra is not None:p["intelligence"]=extra
        reservation=c.reserve(self.db,datetime(2099,6,day,tzinfo=timezone.utc),allow_story=True)
        c.finish(self.db,reservation,p,plan or saga.plan(self.db,"future"))
        did=c.latest_pending(self.db)["id"]
        if approve:self.assertTrue(c.decide(self.db,did,True))
        return did
    def test_failed_index_does_not_publish_even_if_caller_commits(self):
        did=self.make(approve=False)
        with self.db:
            with patch.object(li,"refresh",side_effect=ValueError("bad index")):
                with self.assertRaises(ValueError):c.decide(self.db,did,True)
        self.assertEqual(self.db.execute("SELECT status FROM chronicle_drafts WHERE id=?",(did,)).fetchone()[0],"pending")
        self.assertIsNone(self.db.execute("SELECT number FROM saga_arcs WHERE draft_id=?",(did,)).fetchone()[0])
        self.assertIsNone(self.db.execute("SELECT 1 FROM omega_index WHERE draft_id=?",(did,)).fetchone())
        self.assertTrue(c.decide(self.db,did,True))
    def test_instance_guard(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"test.sqlite3"
            with instance_guard.exclusive(path):
                with self.assertRaises(RuntimeError):
                    with instance_guard.exclusive(path):pass
            with instance_guard.exclusive(path):pass
    def test_graph_aliases_and_limit(self):
        nodes=[{"key":"actor:old","content":"Герой","kind":"character"},{"key":"character:hero","content":"Герой легенды","kind":"character"},{"key":"event:1","content":"Событие","kind":"event"}]
        combined,edges=memory_graph.reconcile_actors(nodes,[{"a":"actor:old","b":"event:1","kind":"character"}])
        self.assertEqual({x["key"] for x in combined},{"character:hero","event:1"})
        self.assertEqual(edges[0]["a"],"character:hero")
        graph=memory_graph.snapshot(self.db,60)
        self.assertLessEqual(len(graph["records"]),60)
        self.assertEqual(len({x["key"] for x in graph["records"]}),len(graph["records"]))
        self.assertEqual(sum(x["key"].startswith("canon:") for x in graph["records"]),13)
    def test_old_prefix_bookmark_and_contiguous_coverage(self):
        first="Хакурэя открыла серебряные двери. "*85
        second="Герой осмотрел древнюю башню и услышал колокольный звон. "*12
        self.make(1,first,plan=novel.enrich(self.db,saga.plan(self.db,"future")))
        reader.move(self.db,"chapter",14)
        d=reader.document(self.db)
        reader.position(self.db,d["hash"],len(d["text"])-40,len(d["text"]))
        self.assertFalse(ev.readable(self.db,14))
        self.make(2,second,plan=novel.enrich(self.db,saga.plan(self.db,"future")))
        reader.position(self.db,d["hash"],50,100)
        self.assertEqual(reader.document(self.db)["offset"],50)
        reader.position(self.db,d["hash"],0,len(d["text"]))
        self.assertTrue(ev.readable(self.db,14))
    def test_index_sweep_and_optional_fact_quarantine(self):
        li.refresh(self.db)
        self.db.execute("UPDATE lit_index SET checksum='bad' WHERE number=1")
        self.assertEqual(li.sweep(self.db),1)
        self.assertEqual(li.audit_text(self.db),"целостность подтверждена")
        plan=li.prepare(self.db,saga.plan(self.db,"future"))
        did=self.make(approve=False,plan=plan,extra=[{"bad":"not evidence"}])
        self.assertIsNotNone(self.db.execute("SELECT 1 FROM lit_rejections WHERE draft_id=?",(did,)).fetchone())
        self.assertEqual(li.extra(self.db,did),[])
        self.assertTrue(c.decide(self.db,did,True))
