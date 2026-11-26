import json
import sqlite3
import unittest
from datetime import datetime, timezone
import graph_activity as ga
import memory_graph
import soul_core
import soul_chronicle as c
import soul_evolution as ev
import soul_saga as saga
import writer_activity as wa
from test_chronicle import draft

class WriterActivityTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db);soul_core.init(self.db);self.db.commit()
    def tearDown(self):self.db.close()
    def test_context_contains_only_selected_safe_keys(self):
        p={"arc":"future","guardians":{"actors":["reika","mikage"]},"genesis":{"recall":[{"number":5,"story":"secret text"}]},
           "infinite":{"selected":{"theme":"power"}},"novel":{"older_volumes":[{"chapter":1}]}}
        keys=wa.context_keys(self.db,p,[{"number":6,"story":"private prose"}])
        for k in ("arc:future","guardians:root","guardian:reika","guardian:mikage","character:hero","canon:5","canon:1","canon:6","book:1"):
            self.assertIn(k,keys)
        self.assertNotIn("guardian:seirana",keys)
        self.assertNotIn("secret text",json.dumps(keys))
    def test_bounded_real_event_history_and_copy(self):
        with ga.track("chronicle","root",["guardian:reika","book:1","invalid key with spaces"]) as key:
            for stage in ("context","waiting","received","validating","saving"):
                ga.update(key,stage)
            active=next(a for a in ga.snapshot()["active"] if a["id"]==key)
            self.assertEqual([x["stage"] for x in active["events"]],["request","context","waiting","received","validating","saving"])
            active["sources"].clear();active["events"].clear()
            self.assertEqual(len(next(a for a in ga.snapshot()["active"] if a["id"]==key)["events"]),6)
            ga.update(key,"saved","draft:42")
        end=next(a for a in ga.snapshot()["recent"] if a["id"]==key)
        self.assertEqual(end["stage"],"saved");self.assertEqual(end["target"],"draft:42")
        self.assertNotIn("invalid key with spaces",json.dumps(end))
        self.assertEqual(len(end["events"]),7)
    def test_publication_metadata_only_after_approval(self):
        self.assertIsNone(memory_graph.snapshot(self.db)["publication"])
        plan=saga.plan(self.db,"future")
        reservation=c.reserve(self.db,datetime(2099,4,1,tzinfo=timezone.utc),allow_story=True)
        c.finish(self.db,reservation,draft(),plan)
        did=c.latest_pending(self.db)["id"]
        self.assertIsNone(memory_graph.snapshot(self.db)["publication"])
        self.assertTrue(c.decide(self.db,did,True))
        self.db.commit()
        pub=memory_graph.snapshot(self.db)["publication"]
        self.assertEqual((pub["number"],pub["volume"],pub["key"]),(14,2,f"c:{did}"))
        self.assertTrue(pub["first"]);self.assertFalse(pub["complete"]);self.assertFalse(pub["details"])
        ev.mark_read(self.db,14)
        self.assertTrue(memory_graph.snapshot(self.db)["publication"]["details"])
