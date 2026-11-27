import json
import unittest
from urllib.error import HTTPError, URLError
import diagnostics
import graph_activity

class DiagnosticTests(unittest.TestCase):
    def records(self, captured):
        return [json.loads(line.split(":",2)[2]) for line in captured.output]

    def test_exception_trace_contains_locations_not_payload(self):
        with self.assertLogs("hakureya.diagnostics",level="INFO") as captured:
            try:
                raise ValueError("private-api-key manuscript prompt raw-provider-output")
            except ValueError as error:
                diagnostics.failure("writer.failed",error,activity="abc",attempt="2026-11-27")
        raw=" ".join(captured.output)
        for secret in ("private-api-key","manuscript","prompt","raw-provider-output"):
            self.assertNotIn(secret,raw)
        entry=self.records(captured)[0]
        self.assertEqual(entry["activity"],"abc")
        self.assertEqual(entry["error_type"],"ValueError")
        self.assertEqual(entry["frames"][-1]["file"],"test_diagnostics.py")
        self.assertGreater(entry["frames"][-1]["line"],0)

    def test_provider_and_json_errors_keep_safe_details(self):
        with self.assertLogs("hakureya.diagnostics",level="INFO") as captured:
            diagnostics.failure("chat.failed",HTTPError("https://example.test/secret","429", "secret-body",None,None))
            diagnostics.failure("writer.failed",URLError("secret-url"))
            try:json.loads('{"secret manuscript":')
            except ValueError as error:diagnostics.failure("writer.failed",error)
            diagnostics.failure("writer.failed",ValueError("incomplete writer stream"))
        raw=" ".join(captured.output)
        self.assertNotIn("secret",raw)
        records=self.records(captured)
        self.assertEqual(records[0]["http_status"],"429")
        self.assertEqual(records[1]["reason_type"],"str")
        self.assertEqual(records[2]["json_line"],1)
        self.assertEqual(records[3]["error_code"],"incomplete writer stream")

    def test_route_and_finish_are_allowlisted(self):
        self.assertEqual(diagnostics.route("/api/writer/resume?key=secret"),"/api/writer")
        self.assertEqual(diagnostics.route("/api/secret"),"other")
        self.assertEqual(diagnostics.finish("secret"),"unknown")

    def test_graph_transitions_share_activity_id(self):
        with self.assertLogs("hakureya.diagnostics",level="INFO") as captured:
            with graph_activity.track("chronicle") as key:
                graph_activity.update(key,"waiting")
                graph_activity.progress(key,12,1)
                graph_activity.update(key,"saved")
        records=self.records(captured)
        self.assertEqual([x["event"] for x in records],["graph.start","graph.transition","graph.transition","graph.end"])
        self.assertTrue(all(x["activity"]==key for x in records))
        self.assertEqual(records[-1]["chars"],12)

if __name__=="__main__":
    unittest.main()
