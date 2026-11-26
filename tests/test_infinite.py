import sqlite3
import unittest
from datetime import datetime,timezone
from unittest.mock import patch
import memory_graph
import soul_core
import soul_chronicle as c
import soul_saga as saga
import soul_infinite as inf
import soul_evolution as ev
import soul_novel as novel
from test_omega import chapter

class InfiniteTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db);soul_core.init(self.db);self.db.commit()
    def tearDown(self):self.db.close()
    def make(self,day,story,facts=(),step=0,approve=True):
        p=chapter("Новая сцена "+str(day))
        p.pop("literary");p["story"]=story
        p["infinite"]={"step":step,"evidence":story.split(".")[0]+"." if step else "","facts":list(facts)}
        plan=inf.context(self.db,saga.plan(self.db,"future"))
        res=c.reserve(self.db,datetime(2099,3,day,tzinfo=timezone.utc),allow_story=True)
        c.finish(self.db,res,p,plan)
        did=c.latest_pending(self.db)["id"]
        if approve:self.assertTrue(c.decide(self.db,did,True))
        return did
    def fact(self,kind,subject,key,value,quote,cause=None,delay=0):
        return dict(kind=kind,subject=subject,key=key,value=value,quote=quote,cause=cause,delay=delay)
    def test_roadmap_is_proposals_only(self):
        self.assertEqual(len(inf.BEATS),30)
        self.assertEqual(len(inf.SAGAS),6)
        self.assertEqual(set(inf.ORDER),set(range(1,61)))
        self.assertFalse(inf.ready(self.db))
        q=inf.forecast(self.db)
        self.assertEqual(len(q["items"]),1000)
        self.assertEqual(q["items"][0]["title"],"Два мира одной императрицы")
        self.assertEqual(q["items"][0]["number"],14)
        self.assertEqual(q["items"][-1]["number"],1013)
        self.assertEqual(sum(x["theme"]=="fixed" for x in q["items"]),118)
        self.assertTrue(all(x["proposal"] for x in q["items"]))
        self.assertIn(inf.stage(31)["title"],[x["title"] for x in q["items"]])
        self.assertEqual(len(novel.forecast(self.db)["items"]),100)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM chronicle_attempts").fetchone()[0],0)
    def test_long_clue_and_visible_graph(self):
        q="Хакурэя нашла серебряную печать на древней карте."
        story=q+" Она попросила героя сохранить находку до того дня, когда они сумеют прочитать надпись."
        f=self.fact("clue","Хакурэя","seal","Серебряная печать",q,5,240)
        did=self.make(1,story,[f])
        self.assertEqual(inf.audit(self.db),[])
        key=f"infinite:fact:{did}:0"
        self.assertNotIn(key,{x["key"] for x in memory_graph.snapshot(self.db)["records"]})
        ev.mark_read(self.db,14)
        g=memory_graph.snapshot(self.db)
        self.assertIn(key,{x["key"] for x in g["records"]})
        self.assertTrue(any(e["kind"]=="infinite_cross_volume" and e["b"]==key for e in g["edges"]))
        quote="Хакурэя объяснила тайну серебряной печати."
        f2=self.fact("reveal","Хакурэя","seal","Тайна раскрыта",quote,14)
        rows=list(inf.published(self.db))
        with self.assertRaises(ValueError):inf.check_facts(self.db,quote,[f2],rows,253)
        self.assertEqual(len(inf.check_facts(self.db,quote,[f2],rows,254)),1)
    def test_exact_quote_and_state_consistency(self):
        q="Герой сказал, что его предел — три шага."
        story=q+" Хакурэя остановилась и внимательно следила за тем, как он открывал проход между двумя стенами."
        f=self.fact("limit","Герой","distance","три шага",q)
        self.make(1,story,[f])
        ev.mark_read(self.db,14)
        self.assertIn("три шага",inf.character_text(self.db,"Герой"))
        self.assertIn("не установлен",inf.character_text(self.db,"Герой"))
        q2="Герой сказал, что его предел — пять шагов."
        f2=self.fact("limit","Герой","distance","пять шагов",q2,14)
        with self.assertRaises(ValueError):inf.check_facts(self.db,q2,[f2],list(inf.published(self.db)),15)
        f3=self.fact("age","Герой","age","9000",q)
        with self.assertRaises(ValueError):inf.check_facts(self.db,q,[f3],[],15)
    def test_location_and_knowledge_require_linked_change(self):
        q="Хакурэя находилась в серебряном дворце."
        self.make(1,q+" Она услышала голос хранительницы и направилась к окну, чтобы выяснить причину неожиданного шума.",
                  [self.fact("location","Хакурэя","place","серебряном дворце",q)])
        q2="Хакурэя находилась в человеческом доме."
        f=self.fact("location","Хакурэя","place","человеческом доме",q2)
        with self.assertRaises(ValueError):inf.check_facts(self.db,q2,[f],list(inf.published(self.db)),15)
        f["cause"]=14
        self.assertEqual(len(inf.check_facts(self.db,q2,[f],list(inf.published(self.db)),15)),1)
    def test_stage_is_not_advanced_by_rejected_draft(self):
        story="Хакурэя нашла запечатанное письмо. Герой положил его в ящик и решил, что они откроют его только после возвращения домой."
        with patch.object(inf,"ready",return_value=True):
            self.assertEqual(inf.remaining(self.db)[0]["id"],inf.ORDER[0])
            did=self.make(1,story,step=inf.ORDER[0],approve=False)
            self.assertTrue(c.decide(self.db,did,False))
            self.assertEqual(inf.remaining(self.db)[0]["id"],inf.ORDER[0])
            self.make(2,story,step=inf.ORDER[0])
            self.assertEqual(inf.remaining(self.db)[0]["id"],inf.ORDER[1])
            self.assertEqual(inf.audit(self.db),[])
