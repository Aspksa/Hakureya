import re
import sqlite3
import unittest
import soul_core
import soul_lore

class LoreTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
    def tearDown(self):
        self.db.close()
    def test_canon_and_context(self):
        raw=soul_lore.canon()
        self.assertEqual(len(re.findall(r"^### Глава [IVX]+\.",raw,re.M)),13)
        for phrase in ("Хакусэйден","с самого рождения","Никто не мог прикоснуться","Императрица на руках смертного","Первые объятия","Продолжай... пожалуйста"):
            self.assertIn(phrase,raw)
        self.assertNotIn("#### Первое невозможное прикосновение",soul_lore.context_for("составь рабочий план"))
        self.assertIn("#### Первое невозможное прикосновение",soul_lore.context_for("как мы познакомились"))
        self.assertIn("Глава XIII.",soul_lore.context_for("биография"))
    def test_upgrade_preserves_old_profile(self):
        soul_core.init(self.db)
        soul_core.observe_user(self.db,11,"отвечай подробно")
        soul_core.observe_user(self.db,12,"не называй меня хозяином")
        before=soul_core.current(self.db)
        self.db.execute("DROP TABLE soul_lore_versions")
        self.db.execute("DELETE FROM soul_events WHERE kind='lore_installed'")
        self.db.commit()
        soul_core.init(self.db)
        self.assertEqual(soul_core.current(self.db),before)
        self.assertEqual(before[2],"ok")
        soul_core.init(self.db)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM soul_lore_versions").fetchone()[0],1)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM soul_events WHERE kind='lore_installed'").fetchone()[0],1)
        prompt=soul_core.system_prompt(self.db,"other-model","первая встреча")
        self.assertIn("Не обращайся к пользователю как к хозяину",prompt)
        self.assertIn("Твоё",prompt.replace("твоё","Твоё"))
        self.assertIn("Канонические главы V–VI",prompt)
        self.assertIn("не к реальным воспоминаниям пользователя",prompt)
        self.assertEqual(soul_core.snapshot(self.db)["lore"]["chapters"],13)
    def test_legacy_hash_unchanged(self):
        # CORE must remain identical to the already deployed profile; lore has its own version.
        self.assertEqual(soul_core.SCHEMA,1)
        self.assertNotIn("lore",soul_core.CORE)
        self.assertNotIn("летопись",soul_core.canonical(soul_core.CORE).casefold())
