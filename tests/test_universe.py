import io
import json
import sqlite3
import unittest
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import memory_graph
import soul_core
import soul_chronicle as c
import soul_universe as u
import soul_export
import soul_novel
import writer_volume
import writer_preview

class UniverseTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db)
        soul_core.init(self.db)

    def test_exact_scene_index_and_repair(self):
        self.assertEqual(u.refresh(self.db),13)
        self.assertEqual(u.refresh(self.db),0)
        for n,story in self.db.execute("SELECT number,story FROM omega_index"):
            spans=self.db.execute("SELECT start,end,body FROM universe_scenes WHERE chapter=? ORDER BY seq",(n,)).fetchall()
            self.assertEqual("".join(x[2] for x in spans),story)
            self.assertTrue(all(story[a:b]==text for a,b,text in spans))
        hits=u.search(self.db,"первое прикосновение",3,False)
        self.assertTrue(hits)
        for r in hits:
            story=self.db.execute("SELECT story FROM omega_index WHERE number=?",(r["chapter"],)).fetchone()[0]
            self.assertEqual(r["text"],story[r["start"]:r["end"]])
        self.assertIn("подтверждена",u.report(self.db,"audit"))
        self.db.execute("UPDATE universe_scenes SET body='bad' WHERE chapter=5 AND seq=1")
        self.assertIn("повреждён",u.report(self.db,"audit"))
        self.assertIn("13",u.report(self.db,"repair"))
        self.assertIn("подтверждена",u.report(self.db,"audit"))

    def test_coordination_and_preferences(self):
        plan={"arc":"future","dynasty":{"current":{"id":13,"theme":"world","title":"Незнакомый человеческий мир","guide":"Маюри впервые видит человека"}},"novel":{"part":1,"start":14}}
        result=u.coordinate(self.db,plan)
        self.assertEqual(result["lane"],"dynasty")
        self.assertIn("Маюри",result["lens"])
        self.assertIn("не знает",result["lens"])
        u.record(self.db,"test",plan)
        self.assertEqual(u.latest_plan(self.db),result)
        with self.assertRaises(ValueError):u.coordinate(self.db,{**plan,"shadow":{"title":"other"}})
        self.assertEqual(writer_volume.target(self.db),0)
        writer_volume.set_target(self.db,30)
        u.set_chapter_pages(self.db,30)
        self.assertEqual(writer_volume.target(self.db),30)
        self.assertEqual(soul_novel.next_group(self.db,"future")["target"],7500)
        soul_core.init(self.db)
        self.assertEqual(u.chapter_pages(self.db),30)
        self.assertEqual(writer_volume.target(self.db),30)

    def test_local_export(self):
        rows=list(soul_export.chapters(self.db))
        self.assertEqual(len(rows),13)
        for kind,name in (("epub","OEBPS/ch13.xhtml"),("docx","word/document.xml")):
            data,mime,filename=soul_export.export(self.db,kind)
            self.assertTrue(filename.endswith(kind))
            with ZipFile(io.BytesIO(data)) as z:
                self.assertIsNone(z.testzip())
                ET.fromstring(z.read(name))
                self.assertIn("Хакурэя",z.read(name).decode())
                if kind=="epub":self.assertEqual(z.namelist()[0],"mimetype")
        data,_,_=soul_export.export(self.db,"html")
        self.assertIn(b"@page{size:A4",data)
        self.assertIn("Хакурэя",data.decode())

    def test_preview_only_story(self):
        self.assertEqual(writer_preview.story_prefix('{"title":"заголовок","story":"Привет\\nмир'),"Привет\nмир")
        self.assertEqual(writer_preview.story_prefix('{"other":{"story":"hidden"},"story":"visible'),"visible")
        self.assertEqual(writer_preview.story_prefix('{"other":{"story":"hidden"}'),"")
        self.assertEqual(writer_preview.story_prefix('{"story":"a\\u04'),"a")
        writer_preview.push("t",'{"story":"сцена')
        self.assertEqual(writer_preview.snapshot()["story"],"сцена")
        writer_preview.clear("t")
        self.assertFalse(writer_preview.snapshot()["active"])

    def test_missing_term_and_corrupt_publication_recovery(self):
        u.refresh(self.db)
        self.db.execute("DELETE FROM universe_terms WHERE chapter=5 AND seq=1")
        self.assertIn("Поисковый индекс повреждён",u.report(self.db,"audit"))
        u.report(self.db,"repair")
        self.assertIn("подтверждена",u.report(self.db,"audit"))
        before=self.db.execute("SELECT story FROM omega_index WHERE number=5").fetchone()[0]
        self.db.execute("UPDATE omega_index SET story='not canon' WHERE number=5")
        with self.assertRaises(ValueError):u.refresh(self.db)
        self.assertIn("повреждён",u.report(self.db,"audit"))
        u.report(self.db,"repair")
        self.assertEqual(self.db.execute("SELECT story FROM omega_index WHERE number=5").fetchone()[0],before)
        self.db.execute("DELETE FROM omega_index WHERE number=6")
        self.assertIn("неполон",u.report(self.db,"audit"))
        u.report(self.db,"repair")
        self.assertIn("подтверждена",u.report(self.db,"audit"))

    def test_relevant_excerpt_and_partial_recovery(self):
        story="Начало главы. "*100+"\n\nМаюри увидела человека впервые."
        snippet=u.focused_excerpt(story,"Маюри человек")
        self.assertIn("Маюри",snippet)
        self.assertIn(snippet,story)
        u.save_fragment(self.db,"2026-01-01","Неоконченная сцена","interrupted")
        self.assertIn("Неоконченная сцена",u.fragment_text(self.db))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM chronicle_drafts").fetchone()[0],0)

    def test_old_bookmark_recovery(self):
        import soul_reader as r
        r.display(self.db,5,0)
        self.db.execute("UPDATE book_reader SET source_hash='old-edition'")
        self.assertIn("Издание обновилось",r.move(self.db,"resume"))
        self.assertEqual(r.document(self.db)["chapter"],5)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM reader_migrations").fetchone()[0],1)

    def test_inline_export(self):
        self.assertEqual(soul_export.inline_html("**Свет** и *снег* & лёд"),"<strong>Свет</strong> и <em>снег</em> &amp; лёд")

    def test_preview_retained_without_claim_of_publication(self):
        writer_preview.push("fragment-test",'{"story":"Новая сцена')
        writer_preview.clear("fragment-test")
        st=writer_preview.snapshot()
        self.assertFalse(st["active"])
        self.assertEqual(st["story"],"Новая сцена")

    def test_writer_cooldown(self):
        self.assertEqual(writer_volume.cooldown(self.db,1800),0)
        reservation=c.reserve(self.db,allow_story=True)
        self.assertIsNotNone(reservation)
        self.assertGreater(writer_volume.cooldown(self.db,1800),1700)
