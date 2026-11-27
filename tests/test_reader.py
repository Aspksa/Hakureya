import sqlite3
import tempfile
import unittest
from pathlib import Path
import memory_graph
import soul_core
import soul_reader as r
import soul_saga
import soul_omega

class ReaderTest(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.path=Path(self.folder.name)/"reader.sqlite3"
        self.db=self.connect()
    def connect(self):
        db=sqlite3.connect(self.path)
        db.execute("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(db);soul_core.init(db);db.commit()
        return db
    def tearDown(self):
        self.db.close();self.folder.cleanup()
    def test_pagination_preserves_source(self):
        text=soul_saga.canonical_chapters()[4][2]
        pages=r.paginate(text)
        self.assertGreater(len(pages),1)
        self.assertEqual("".join(pages),text)
        self.assertTrue(all(0<len(p)<=r.PAGE_SIZE for p in pages))
    def test_restart_and_resume(self):
        first=r.move(self.db,"chapter",5)
        second=r.move(self.db,"next")
        self.assertNotEqual(first,second)
        self.assertIn("Страница 2/",second)
        self.db.commit();self.db.close();self.db=self.connect()
        self.assertEqual(r.move(self.db,"resume"),second)
        self.assertEqual(r.move(self.db,"back"),first)
        self.assertIn("страница 1",r.move(self.db,"pause"))
        self.assertFalse(r.active(self.db))
        self.assertEqual(r.move(self.db,"resume"),first)
    def test_continuity_and_end(self):
        r.move(self.db,"chapter",5)
        pages,_=r.load(self.db,5)
        for _ in range(len(pages)-1):r.move(self.db,"next")
        self.assertIn("Глава 6 · Страница 1/",r.move(self.db,"next"))
        self.assertIn(f"Страница {len(pages)}/",r.move(self.db,"back"))
        r.move(self.db,"latest")
        end_pages,_=r.load(self.db,13)
        for _ in range(len(end_pages)-1):r.move(self.db,"next")
        old=r.bookmark(self.db)
        self.assertIn("последней опубликованной",r.move(self.db,"next"))
        self.assertEqual(r.bookmark(self.db),old)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM chronicle_attempts").fetchone()[0],0)
    def test_migrate_and_invalid(self):
        soul_omega.mark(self.db,5)
        self.assertIn("Глава 5 · Страница 1/",r.move(self.db,"resume"))
        old=r.bookmark(self.db)
        self.assertIn("недоступна",r.move(self.db,"chapter",999))
        self.assertEqual(r.bookmark(self.db),old)
        self.db.execute("UPDATE book_reader SET source_hash='bad'")
        self.assertIn("изменился",r.move(self.db,"next"))


    def test_adaptive_bookmark_and_unicode(self):
        r.move(self.db,"chapter",5)
        doc=r.view(self.db)["document"]
        self.assertNotIn("Художественный канон",doc["text"])
        self.assertNotIn("### Глава",doc["text"])
        start=137
        r.position(self.db,doc["hash"],start,start+500)
        self.assertEqual(r.document(self.db)["offset"],start)
        self.db.commit();self.db.close();self.db=self.connect()
        r.move(self.db,"pause")
        self.assertIsNone(r.view(self.db))
        r.move(self.db,"resume")
        self.assertEqual(r.document(self.db)["offset"],start)
        with self.assertRaises(ValueError):r.position(self.db,"bad",0,10)
        self.assertEqual(r.document(self.db)["offset"],start)

    def test_adaptive_adjacent_documents(self):
        r.move(self.db,"start")
        r.adjacent(self.db,"advance")
        self.assertEqual(r.document(self.db)["chapter"],2)
        r.adjacent(self.db,"retreat")
        d=r.document(self.db)
        self.assertEqual(d["chapter"],1)
        self.assertEqual(d["offset"],len(d["text"]))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM chronicle_attempts").fetchone()[0],0)

    def test_contents_is_read_only_and_cyrillic_search(self):
        r.move(self.db,"chapter",5)
        old=r.bookmark(self.db)
        data=r.contents(self.db)
        self.assertEqual(data["total"],13)
        self.assertEqual(data["current"],5)
        title=data["items"][4]["title"]
        self.assertTrue(any(x["chapter"]==5 for x in r.contents(self.db,query=title.upper())["items"]))
        self.assertEqual(r.contents(self.db,query="5")["items"][0]["chapter"],5)
        self.assertEqual(r.bookmark(self.db),old)
        with self.assertRaises(ValueError):r.contents(self.db,False)

    def test_portable_preferences_persist_without_moving_bookmark(self):
        r.move(self.db,"chapter",5)
        old=r.bookmark(self.db)
        prefs={"font":24,"spacing":2.1,"theme":"sepia","family":"sans","width":"wide"}
        self.assertEqual(r.save_preferences(self.db,prefs),prefs)
        with self.assertRaises(ValueError):r.save_preferences(self.db,{**prefs,"font":100})
        self.db.commit();self.db.close();self.db=self.connect()
        self.assertEqual(r.view(self.db)["preferences"],prefs)
        self.assertEqual(r.bookmark(self.db),old)
