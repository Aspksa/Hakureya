import sqlite3
import unittest
from datetime import datetime, timezone
import memory_graph
import soul_core
import soul_chronicle as c
import soul_saga as saga
import soul_novel as novel
import soul_reader as reader
from test_omega import chapter

class NovelTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db);soul_core.init(self.db);self.db.commit()
    def tearDown(self):self.db.close()
    def make(self,day,story,approve=True):
        plan=novel.enrich(self.db,saga.plan(self.db,"future"))
        value=chapter("Новая часть "+str(day))
        value.pop("literary")
        value["story"]=story
        res=c.reserve(self.db,datetime(2099,2,day,tzinfo=timezone.utc),allow_story=True)
        c.finish(self.db,res,value,plan)
        did=c.latest_pending(self.db)["id"]
        if approve:self.assertTrue(c.decide(self.db,did,True))
        return did,plan
    def test_published_parts_join_and_append_without_losing_bookmark(self):
        first="Хакурэя коснулась холодного камня. Сверху донёсся голос, и она подняла голову, удивлённая внезапным сиянием.\n\n— Ты видишь это? — спросила она."
        second="Из темноты показался светлый силуэт. Герой шагнул ближе и услышал тихий звон, похожий на отголосок старинной мелодии."
        did,plan=self.make(1,first)
        self.assertEqual(plan["novel"]["part"],1)
        reader.move(self.db,"chapter",14)
        d=reader.document(self.db);reader.position(self.db,d["hash"],25,70)
        did2,plan2=self.make(2,second)
        self.assertEqual(plan2["novel"]["part"],2)
        self.assertEqual(plan2["novel"]["ending"],first)
        d=reader.document(self.db)
        self.assertEqual(d["text"],first+"\n\n"+second)
        self.assertEqual(d["offset"],25)
        self.assertEqual(d["last_chapter"],15)
        self.assertEqual(d["parts"],2)
        self.assertEqual(novel.audit(self.db),[])
        self.assertIn(f"c:{did2}",{n["key"] for n in memory_graph.snapshot(self.db)["records"]})
        reader.position(self.db,d["hash"],len(first)+2,len(d["text"]))
        self.assertEqual(reader.bookmark(self.db)[0],15)
        self.assertEqual(reader.document(self.db)["offset"],len(first)+2)
    def test_rejected_part_does_not_advance(self):
        first="Хакурэя осторожно вошла в зал. Вдали мерцал огонёк, и герой предложил осмотреть неизвестную дверь вместе."
        did,_=self.make(1,first,False)
        self.assertEqual(novel.group_for(self.db,14),[])
        self.assertTrue(c.decide(self.db,did,False))
        p=novel.enrich(self.db,saga.plan(self.db,"future"))["novel"]
        self.assertEqual((p["start"],p["part"]),(14,1))
    def test_duplicate_boundary_rejected(self):
        first="На далёком горизонте тихого города сияла необычная звезда, и Хакурэя впервые заметила странный золотой отблеск."
        self.make(1,first)
        with self.assertRaises(ValueError):
            with self.db:self.make(2,first+" Затем она улыбнулась.")
    def test_forecast_does_not_publish(self):
        q=novel.forecast(self.db)
        self.assertEqual(len(q["items"]),100)
        self.assertEqual(q["items"][0]["title"],"Два мира одной императрицы")
        self.assertEqual(q["items"][0]["number"],14)
        self.assertEqual(q["items"][-1]["number"],113)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM chronicle_attempts").fetchone()[0],0)
        self.assertEqual(novel.forecast(self.db),q)
