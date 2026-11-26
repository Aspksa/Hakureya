import sqlite3
import unittest
import json
from unittest.mock import MagicMock
import cloud_writer as w

class WriterTest(unittest.TestCase):
    def test_exact_model_and_ambiguity(self):
        ids=["zai-org/GLM-5.3","moonshotai/Kimi-K2.6"]
        self.assertEqual(w.match(ids,"glm-5.3"),ids[0])
        self.assertEqual(w.match(ids,"moonshotai/kimi-k2.6"),ids[1])
        self.assertIsNone(w.match(ids,"GLM-5"))
        self.assertIsNone(w.match(ids+["other/GLM-5.3"],"glm-5.3"))

    def test_model_list(self):
        opener=MagicMock()
        opener.return_value.__enter__.return_value.read.return_value=json.dumps({"data":[{"id":"zai-org/GLM-5.3"},{"id":"zai-org/GLM-5.3"},{}]}).encode()
        self.assertEqual(w.list_models("secret",opener),["zai-org/GLM-5.3"])
        req=opener.call_args.args[0]
        self.assertEqual(req.get_method(),"GET")
        self.assertEqual(req.full_url,w.MODELS_URL)
        self.assertEqual(req.get_header("Authorization"),"Bearer secret")

    def test_settings_and_usage(self):
        db=sqlite3.connect(":memory:")
        try:
            w.init(db)
            self.assertEqual(w.selected(db),"")
            w.choose(db,"zai-org/GLM-5.3")
            w.init(db)
            self.assertEqual(w.selected(db),"zai-org/GLM-5.3")
            w.usage(db,"2099-01-01",w.selected(db),{"usage":{"prompt_tokens":1200,"completion_tokens":900}})
            w.usage(db,"2099-01-01",w.selected(db),{"usage":{"prompt_tokens":1,"completion_tokens":1}})
            self.assertIn("вход 1200, выход 900",w.usage_text(db))
        finally:db.close()
