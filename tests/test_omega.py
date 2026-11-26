import sqlite3
import unittest
from datetime import datetime, timezone
import soul_core
import soul_chronicle as c
import soul_saga as saga
import soul_omega as o
import memory_graph

def chapter(title="Серебряный архив"):
    story="Хакурэя открыла дверь серебряного архива. — Как странно, — произнесла она, изучая древние записи. Герой ждал у окна. На странице сиял неизвестный символ."
    return {"title":title,"story":story,"tags":["познание","любовь"],
            "emotions":{"wonder":80,"calm":50,"joy":30},
            "traits":{"patience":1,"curiosity":2,"warmth":1},
            "literary":{"events":[{"summary":"Открытие серебряного архива","evidence":"Хакурэя открыла дверь серебряного архива.","characters":["Хакурэя"],"cause":5}],
                         "mysteries":[{"key":"silver-mark","action":"open","question":"Что означает серебряный символ?","evidence":"На странице сиял неизвестный символ."}],
                         "diary":"Сегодня я впервые увидела знак, которого не знала."}}

class OmegaTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db);soul_core.init(self.db)
        self.db.commit()
    def tearDown(self): self.db.close()
    def create(self,day,arc="love",value=None):
        r=c.reserve(self.db,datetime(2099,1,day,tzinfo=timezone.utc),allow_story=True)
        self.assertIsNotNone(r)
        plan=o.enrich_plan(self.db,saga.plan(self.db,arc))
        c.finish(self.db,r,value or chapter(),plan)
        return c.latest_pending(self.db)["id"]
    def test_canon_and_plan(self):
        self.assertEqual(len(o.roadmap(self.db)),24)
        self.assertEqual({p["arc"] for p in o.roadmap(self.db)},set(o.ARCS))
        self.assertEqual(o.mysteries(self.db)["protection"]["opened"],5)
        self.assertEqual(o.volume(13),1);self.assertEqual(o.volume(14),2);self.assertEqual(o.volume(26),3)
        self.assertTrue(o.search(self.db,"императрица"))
    def test_publication_and_evidence(self):
        did=self.create(1)
        self.assertNotIn("silver-mark",o.mysteries(self.db))
        self.assertIsNotNone(o.metadata(self.db,did))
        self.assertFalse(any(p["number"]>13 for p in o.search(self.db,"серебряный архив")))
        self.assertTrue(c.decide(self.db,did,True))
        self.assertEqual(o.mysteries(self.db)["silver-mark"]["opened"],14)
        self.assertEqual(o.search(self.db,"серебряный архив")[0]["number"],14)
        self.assertIn("Хакурэя открыла",o.read_volume(self.db,2))
        self.assertIn("Сегодня я",o.diary(self.db,14))
        o.mark(self.db,14);self.assertEqual(o.bookmark(self.db),14)
        self.assertIn("Том 2",o.books(self.db))
        graph=memory_graph.snapshot(self.db)
        keys={p["key"] for p in graph["records"]}
        self.assertTrue({"book:2","era:love","mystery:silver-mark",f"event:{did}:0",f"c:{did}"}.issubset(keys))
        self.assertTrue(any(e["a"]=="canon:5" and e["b"]==f"event:{did}:0" for e in graph["edges"]))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM omega_history").fetchone()[0],2)
        self.assertEqual(c.status(self.db)["diary_entries"],0)
    def test_duplicate_and_false_evidence(self):
        did=self.create(1);c.decide(self.db,did,True);self.db.commit()
        with self.assertRaises(ValueError): self.create(2,value=chapter())
        self.db.rollback()
        bad=chapter("Другая глава")
        bad["literary"]["events"][0]["evidence"]="Событие, отсутствующее в тексте"
        with self.assertRaises(ValueError): self.create(3,value=bad)
        self.db.rollback()
        self.assertEqual(len(saga.reading_rows(self.db)),1)
    def test_metadata_corruption_and_rejection(self):
        did=self.create(1)
        self.db.execute("UPDATE omega_meta SET checksum='bad'")
        with self.assertRaises(ValueError): c.decide(self.db,did,True)
        self.assertTrue(c.decide(self.db,did,False))
        self.assertEqual(len(saga.reading_rows(self.db)),0)
    def test_mystery_resolve_requires_known_source(self):
        bad=chapter()
        bad["literary"]["mysteries"][0].update(key="protection",action="resolve")
        with self.assertRaises(ValueError): self.create(1,value=bad)
    def test_bounded_book_graph(self):
        # Synthetic index rows test aggregation math, not invented production history.
        self.db.executemany("INSERT INTO omega_index VALUES(?,?,?,?,?,NULL)",[(n,"future",f"Глава {n}","Текст","test") for n in range(14,10014)])
        nodes,_=o.graph(self.db)
        self.assertLessEqual(len([n for n in nodes if n["kind"]=="book"]),122)
        self.assertIn("book:archive",{n["key"] for n in nodes})
