import sqlite3
import unittest
from unittest.mock import patch
import soul_core
import soul_saga
import soul_intelligence as li
import soul_intellect
import soul_network as net
import memory_graph
import graph_activity
import soul_omega as o

class NeuralNetworkTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db);soul_core.init(self.db)
    def prepare(self,arc="future"):
        plan=soul_saga.plan(self.db,arc)
        soul_intellect.prepare(self.db,plan)
        return li.prepare(self.db,plan)["intelligence"]
    def test_all_modules_and_actual_handoffs(self):
        p=self.prepare()
        trace=net.validate_trace(p["network"])
        self.assertEqual(p["completed"],list(net.ORDER))
        self.assertEqual(set(p["context"]),set(net.ORDER[:-1]))
        self.assertEqual(net.size(p["context"]),trace["context_bytes"])
        self.assertLessEqual(trace["context_bytes"],4200)
        self.assertEqual(sum(len(e["inputs"]) for e in trace["events"]),len(net.edges()))
        self.assertEqual(len(net.edges()),31)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM chronicle_attempts").fetchone()[0],0)
        self.assertEqual(tuple(x["from"] for x in trace["events"][-1]["inputs"]),net.ORDER[:-1])
        li.record_run(self.db,"test",{"intelligence":p})
        self.assertEqual(net.latest(self.db),trace)
        graph=net.snapshot(self.db,li.BRAINS)
        self.assertEqual(sum(n["kind"]=="lit_brain" for n in graph["records"]),10)
        self.assertEqual(len([e for e in graph["edges"] if e["kind"]=="neural_input"]),31)
        self.assertEqual(graph["trace_origin"],"writer")
        self.assertEqual(len([e for e in memory_graph.snapshot(self.db)["edges"] if e["kind"]=="neural_input"]),31)
    def test_wrong_order_and_packet_rejected(self):
        n=net.Network()
        with self.assertRaises(ValueError):n.begin("memory")
        n.begin("plot")
        with self.assertRaises(ValueError):n.finish("plot",{"theme":"power","open":"invalid","guide":"test"})
        n.finish("plot",{"theme":"power","open":[],"guide":"test"})
        parents=n.begin("characters")
        parents["plot"]["theme"]="changed"
        self.assertEqual(n.outputs["plot"]["theme"],"power")
        with self.assertRaises(ValueError):n.finish("characters",{"recent":[]})
    def test_tampered_transfer_and_checksum(self):
        trace=self.prepare()["network"]
        trace["events"][1]["inputs"][0]["bytes"]+=1
        with self.assertRaises(ValueError):net.validate_trace(trace)
        trace=self.prepare()["network"]
        net.record_diagnostic(self.db,trace)
        self.assertEqual(net.snapshot(self.db,li.BRAINS)["trace_origin"],"diagnostic")
        self.db.execute("UPDATE neural_diagnostic SET checksum='damaged'")
        with self.assertRaises(ValueError):net.snapshot(self.db,li.BRAINS)
    def test_history_scope_memory(self):
        p=self.prepare("past")
        for r in p["context"]["memory"]:
            self.assertEqual(self.db.execute("SELECT arc FROM omega_index WHERE number=?",(r["number"],)).fetchone()[0],"past")
    def test_actual_handoff_event(self):
        with graph_activity.track("chronicle") as key:
            graph_activity.update(key,"brain:relations","brain:relations",1.3,["plot","characters","unknown"],1024,True)
            e=graph_activity.snapshot()["active"][-1]["events"][-1]
            self.assertEqual(e["inputs"],["plot","characters"])
            self.assertEqual(e["output_bytes"],1024)
            self.assertTrue(e["included"])
