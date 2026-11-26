import json
import sqlite3
import unittest
from datetime import datetime, timezone
import soul_core
import soul_chronicle as c
import soul_lore
import memory_graph

def draft():
    return {"title":"Новое открытие","story":"Хакурэя изучала устройство человеческих машин. "*5,
            "tags":["познание","достоинство"],"emotions":{"wonder":70,"calm":80,"joy":60},
            "traits":{"patience":2,"curiosity":1,"warmth":-1}}

class ChronicleTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db)
        soul_core.init(self.db)
    def tearDown(self):
        self.db.close()
    def reviews(self,start=1):
        for i in range(start,start+5):
            soul_core.review_response(self.db,i,"Ответ")
        self.assertEqual(c.collect(self.db),1)
    def test_diary_and_approval(self):
        initial=soul_lore.canon()
        self.reviews()
        self.assertEqual(c.collect(self.db),0)
        reservation=c.reserve(self.db)
        self.assertIsNotNone(reservation)
        self.assertIsNone(c.reserve(self.db))
        c.finish(self.db,reservation,draft())
        self.assertEqual(c.profile(self.db),c.BASE)
        self.assertEqual(len(c.approved(self.db)),0)
        self.assertTrue(c.decide(self.db,1,True))
        self.assertFalse(c.decide(self.db,1,True))
        self.assertEqual(c.profile(self.db)["patience"],52)
        self.assertEqual(soul_lore.canon(),initial)
        graph=memory_graph.snapshot(self.db)
        self.assertTrue({"d:1","c:1","canon:1","canon:13"}.issubset({n["key"] for n in graph["records"]}))
        self.assertEqual(next(n for n in graph["records"] if n["key"]=="c:1")["group"],4)
        self.assertFalse(any(n["key"].startswith("draft:") for n in graph["records"]))
        self.assertTrue(any(e["kind"]=="emotion" and e["a"]=="c:1" for e in graph["edges"]))
        self.assertTrue(any(e["kind"]=="chronicle" for e in graph["edges"]))
        self.assertEqual(len([n for n in c.biography_graph(self.db)["nodes"] if n["kind"]=="fictional_chapter"]),13)
    def test_expanded_canon_v2_migration(self):
        import soul_saga
        import soul_genesis
        import soul_intelligence
        import soul_reader
        chapters=soul_saga.canonical_chapters()
        self.assertEqual(len(chapters),13)
        self.assertEqual(soul_lore.VERSION,2)
        for n in (5,6):
            story=chapters[n-1][2]
            self.assertTrue(12000<=len(story)<=12600)
            self.assertEqual("".join(soul_reader.paginate(story)),story)
        self.reviews()
        r=c.reserve(self.db)
        c.finish(self.db,r,draft())
        # Simulate the installed version and a pending v1 draft.
        old=soul_lore.PREVIOUS_SHA256
        self.db.execute("DELETE FROM soul_lore_versions")
        self.db.execute("INSERT INTO soul_lore_versions(version,checksum) VALUES(1,?)",(old,))
        self.db.execute("UPDATE chronicle_drafts SET canon_hash=?",(old,))
        self.db.execute("UPDATE omega_index SET checksum=? WHERE number<=13",(old,))
        soul_intelligence.refresh(self.db)
        soul_core.init(self.db)
        soul_intelligence.refresh(self.db)
        self.assertTrue(c.canon_ok(self.db))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM soul_lore_versions").fetchone()[0],2)
        self.assertEqual(self.db.execute("SELECT story FROM omega_index WHERE number=5").fetchone()[0],chapters[4][2])
        self.assertFalse(soul_genesis.audit(self.db))
        self.assertTrue(c.decide(self.db,1,True))
        self.assertEqual(self.db.execute("SELECT number FROM saga_arcs WHERE draft_id=1").fetchone()[0],14)
        self.assertFalse(soul_lore.compatible_draft(self.db,"unknown"))
        self.db.execute("UPDATE soul_lore_versions SET checksum='damaged' WHERE version=1")
        self.assertFalse(soul_lore.compatible_draft(self.db,old))

    def test_validation_and_failure(self):
        self.reviews()
        r=c.reserve(self.db)
        bad=draft()
        bad["traits"]["patience"]=100
        with self.assertRaises(ValueError):
            c.finish(self.db,r,bad)
        c.fail(self.db,r)
        self.assertIsNone(c.reserve(self.db))
        next_day=datetime(2099,1,1,tzinfo=timezone.utc)
        r=c.reserve(self.db,next_day)
        self.assertIsNotNone(r)
        c.finish(self.db,r,draft())
        self.db.execute("UPDATE chronicle_drafts SET checksum='bad'")
        with self.assertRaises(ValueError):
            c.decide(self.db,1,True)
        self.assertEqual(c.profile(self.db),c.BASE)
        self.assertTrue(c.decide(self.db,1,False))
    def test_canon_and_profile(self):
        self.reviews()
        soul_core.observe_user(self.db,99,"отвечай кратко")
        before=soul_core.current(self.db)
        self.db.execute("UPDATE soul_lore_versions SET checksum='invalid'")
        self.assertFalse(c.canon_ok(self.db))
        self.assertIsNone(c.reserve(self.db))
        self.assertEqual(soul_core.current(self.db),before)
    def test_prompt_no_chat_content(self):
        self.reviews()
        r=c.reserve(self.db)
        self.assertNotIn("Ответ",json.dumps(c.prompt(r,c.BASE),ensure_ascii=False))
        self.assertIn("не события легенды",c.prompt(r,c.BASE)[1]["content"])

    def test_permanent_canon_and_stable_slots(self):
        first=memory_graph.snapshot(self.db)
        slots={n["key"]:n["slot"] for n in first["records"]}
        self.reviews()
        r=c.reserve(self.db)
        c.finish(self.db,r,draft())
        second=memory_graph.snapshot(self.db)
        self.assertTrue(any(n["key"]=="draft:1" for n in second["records"]))
        draft_node=next(n for n in second["records"] if n["key"]=="draft:1")
        self.assertIsInstance(draft_node["review_warnings"],list)
        self.assertTrue(next(n for n in second["records"] if n["key"]=="book:1")["volume_complete"])
        self.assertTrue(c.decide(self.db,1,True))
        third=memory_graph.snapshot(self.db)
        self.assertTrue(all(n["slot"]==slots[n["key"]] for n in third["records"] if n["key"] in slots))
        for i in range(80):
            memory_graph.add_note(self.db,1,"Запись "+str(i))
        limited=memory_graph.snapshot(self.db,60)
        self.assertEqual(len([n for n in limited["records"] if n["key"].startswith("canon:")]),13)
        self.assertTrue(limited["limited"])
        keys={n["key"] for n in limited["records"]}
        self.assertTrue(all(e["a"] in keys and e["b"] in keys for e in limited["edges"]))
