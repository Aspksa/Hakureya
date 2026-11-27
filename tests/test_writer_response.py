import json
import unittest
import writer_response as w
import writer_preview
from test_dynasty import base

class WriterResponseTest(unittest.TestCase):
    def test_strict_complete_fenced_json(self):
        value=base()
        raw="\x60\x60\x60json\n"+json.dumps(value,ensure_ascii=False)+"\n\x60\x60\x60"
        parsed=w.parse(raw)
        self.assertEqual(parsed,value)
        self.assertEqual(w.normalize(parsed),(value,[]))
        self.assertEqual(writer_preview.story_prefix(raw),value["story"])
        with self.assertRaises(ValueError):w.parse(raw+"\nmore text")
        with self.assertRaises(ValueError):w.parse('{"story":"one","story":"two"}')
        with self.assertRaises(ValueError):w.parse('{"story":"unfinished')

    def test_invalid_fictional_counters_do_not_change_story(self):
        value=base()
        value["tags"]=[" ЛЮБОВЬ ","other","любовь"]
        value["traits"]={"patience":900}
        value["emotions"]=None
        value["extra"]="unknown"
        repaired,warnings=w.normalize(value)
        self.assertEqual(repaired["story"],value["story"])
        self.assertEqual(repaired["title"],value["title"])
        self.assertEqual(repaired["tags"],["любовь"])
        self.assertEqual(repaired["traits"],{"patience":0,"curiosity":0,"warmth":0})
        self.assertEqual(len(warnings),4)
        self.assertNotIn("extra",repaired)
        with self.assertRaises(ValueError):w.normalize({"title":"Test","story":"too short"})
        with self.assertRaises(ValueError):w.normalize({"title":"Test","story":"a"*5001})

    def test_error_text_cannot_echo_secrets(self):
        self.assertNotIn("secret-key",w.detail(ValueError("secret-key")))
        self.assertIn("Повтор",w.detail(ValueError("duplicate published chapter")))
