import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import closing
import soul_core as soul
import server

class SoulTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/"soul.sqlite3"
        self.db=sqlite3.connect(self.path)
        soul.init(self.db)
        self.db.commit()
    def tearDown(self):
        self.db.close()
        self.temp.cleanup()
    def test_birth_identity_and_model_switch(self):
        first=soul.snapshot(self.db)
        self.assertEqual(first["core"]["name"],"Hakureya")
        self.assertEqual(first["version"],1)
        self.assertFalse(first["self_model"]["connected"])
        soul.record_model(self.db,"fast")
        soul.record_model(self.db,"smart")
        soul.init(self.db)
        current=soul.snapshot(self.db,True,"smart")
        self.assertEqual(first["core_hash"],current["core_hash"])
        self.assertEqual(current["version"],1)
        self.assertEqual(current["history"]["events"]["birth"],1)
        self.assertEqual(current["history"]["events"]["model_selected"],2)
        self.assertIn("не реальное бессмертное существо",soul.system_prompt(self.db,"smart"))
    def test_explicit_adaptation_persists_and_history(self):
        self.assertTrue(soul.observe_user(self.db,5,"Отвечай кратко!"))
        self.assertFalse(soul.observe_user(self.db,6,"отвечай кратко"))
        self.assertFalse(soul.observe_user(self.db,7,'Он сказал "отвечай подробно"'))
        self.assertFalse(soul.observe_user(self.db,8,"измени имя на другое"))
        self.db.commit()
        with closing(sqlite3.connect(self.path)) as reopened:
            soul.init(reopened)
            state,version,status=soul.current(reopened)
            self.assertEqual((state["verbosity"],version,status),("brief",2,"ok"))
            self.assertEqual(reopened.execute("SELECT source_message FROM soul_versions WHERE id=2").fetchone()[0],5)
            self.assertIn("Кратко",soul.system_prompt(reopened,"another-model"))
    def test_corruption_rejects_change(self):
        self.db.execute("UPDATE soul_versions SET state='{}'")
        state,version,status=soul.current(self.db)
        self.assertEqual(state,soul.DEFAULT)
        self.assertEqual(status,"invalid_adaptive_state")
        self.assertFalse(soul.observe_user(self.db,1,"отвечай подробно"))
        self.assertEqual(soul.current(self.db)[1],version)
        self.assertIn("Hakureya",soul.system_prompt(self.db,"model"))
    def test_core_mismatch_and_untrusted_state(self):
        raw=soul.canonical({"verbosity":"brief","formality":"regal","address":"master","name":"other"})
        self.db.execute("UPDATE soul_versions SET state=?,checksum=?",(raw,soul.digest(raw)))
        self.assertEqual(soul.current(self.db)[2],"invalid_adaptive_state")
        self.db.execute("UPDATE soul_versions SET core_hash='wrong'")
        self.assertEqual(soul.current(self.db)[2],"core_or_schema_mismatch")
    def test_review_observable_and_idempotent(self):
        soul.observe_user(self.db,1,"отвечай кратко")
        soul.observe_user(self.db,2,"не называй меня хозяином")
        soul.review_response(self.db,3,"Хозяин "+"слово "*200)
        soul.review_response(self.db,3,"different")
        s=soul.snapshot(self.db)
        self.assertEqual(s["history"]["recent_reviews"],1)
        self.assertEqual(s["history"]["recent_brief_warnings"],1)
        self.assertEqual(s["history"]["recent_address_warnings"],1)
    def test_server_store_atomic_integration(self):
        with patch.object(server,"DB",Path(self.temp.name)/"server.sqlite3"):
            user_id=server.store("user","отвечай подробно")
            answer_id=server.store("assistant","Ответ")
            with closing(server.connect()) as db:
                self.assertEqual(soul.current(db)[0]["verbosity"],"detailed")
                self.assertEqual(db.execute("SELECT source_message FROM soul_versions WHERE id=2").fetchone()[0],user_id)
                self.assertEqual(db.execute("SELECT message_id FROM soul_events WHERE kind='response_review'").fetchone()[0],answer_id)
                self.assertIn("Подробно",soul.system_prompt(db,"model"))
            self.assertEqual(len(server.history()),2)
