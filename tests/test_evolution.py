import sqlite3
import unittest
from unittest.mock import patch
from datetime import datetime,timezone
import soul_core
import memory_graph
import soul_chronicle as c
import soul_omega as o
import soul_saga as s
import soul_evolution as e
import soul_reader
from test_omega import chapter

class EvolutionTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db);soul_core.init(self.db);self.db.commit()
    def tearDown(self):self.db.close()
    def draft(self,bad=False,scene=0):
        p=chapter("Судьба серебряного архива")
        p["evolution"]={"scene":scene,"evidence":"Хакурэя открыла дверь серебряного архива." if scene else "","facts":[{
            "kind":"promise","subject":"Хакурэя","key":"archive","detail":"Обещание изучить архив","evidence":"Несуществующая цитата." if bad else "Хакурэя открыла дверь серебряного архива.",
            "cause":5,"state":"open","knows":[]}]}
        plan=o.enrich_plan(self.db,s.plan(self.db,"future"))
        e.enrich(self.db,plan)
        r=c.reserve(self.db,datetime(2099,1,1,tzinfo=timezone.utc),allow_story=True)
        c.finish(self.db,r,p,plan)
        return c.latest_pending(self.db)["id"]
    def test_plan(self):
        self.assertEqual([x[0] for x in e.SCENES],list(range(11,51)))
        self.assertFalse(e.ready(self.db))
        self.assertEqual(e.settings(self.db),("баланс",1))
        e.style(self.db,"романтика")
        e.preference(self.db,"world")
        self.assertEqual(e.candidates(self.db,[])[0]["theme"],"world")
        with patch.object(e,"ready",return_value=True):
            p=e.enrich(self.db,s.plan(self.db,"future"))["evolution"]
            self.assertTrue(p["unlocked"])
            self.assertEqual(len(p["alternatives"]),2)
    def test_publish_and_spoilers(self):
        did=self.draft()
        self.assertEqual(e.state(self.db),{})
        self.assertTrue(c.decide(self.db,did,True))
        self.assertEqual(len(e.state(self.db)),1)
        self.assertNotIn("Обещание изучить",e.profile(self.db,"Хакурэя"))
        soul_reader.move(self.db,"chapter",14)
        self.assertIn("Обещание изучить",e.profile(self.db,"Хакурэя"))
        self.assertIn("Судьба серебряного архива",e.annotation(self.db,2))
        self.assertTrue(any(x["key"]==f"evolution:fact:{did}:0" for x in memory_graph.snapshot(self.db)["records"]))
    def test_bad_quote(self):
        with self.assertRaises(ValueError):self.draft(bad=True)
    def test_early_scene(self):
        with self.assertRaises(ValueError):self.draft(scene=11)
    def test_reject(self):
        did=self.draft()
        self.assertTrue(c.decide(self.db,did,False))
        self.assertEqual(e.state(self.db),{})
    def test_budget(self):
        e.set_budget(self.db,"writer",10000,50000,10000)
        ok,details=e.budget_check(self.db,"writer",[{"content":"тест"}],1800,"2099-01-01")
        self.assertTrue(ok)
        e.reserve_cost(self.db,"2099-01-01","writer",details)
        e.settle_cost(self.db,"2099-01-01",{"usage":{"prompt_tokens":1000,"completion_tokens":1000}})
        self.assertEqual(self.db.execute("SELECT actual_kopecks FROM evolution_cost").fetchone()[0],60)
        self.assertFalse(e.budget_check(self.db,"other",[],1800,"2099-01-02")[0])
        e.set_budget(self.db,"writer",10000,50000,1)
        self.assertFalse(e.budget_check(self.db,"writer",[],1800,"2099-01-02")[0])
