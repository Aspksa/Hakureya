import io
import json
import unittest
import writer_stream
import graph_activity

class Response(io.BytesIO):
    def __init__(self,body,mime="text/event-stream"):
        super().__init__(body)
        self.headers={"Content-Type":mime}

def event(obj):
    return ("data: "+json.dumps(obj,ensure_ascii=False)+"\n\n").encode()

def chunk(text,reason=None):
    return event({"choices":[{"index":0,"delta":{"content":text},"finish_reason":reason}]})

class WriterStreamTests(unittest.TestCase):
    def test_counts_real_content_and_usage(self):
        body=chunk("Глава ")+event({"choices":[{"delta":{"reasoning_content":"not exposed"}}]})+chunk("один","stop")+event({"choices":[],"usage":{"prompt_tokens":9,"completion_tokens":4}})+b"data: [DONE]\n\n"
        progress=[]
        result=writer_stream.read_response(Response(body),lambda a,b:progress.append((a,b)))
        self.assertEqual(progress,[(6,1),(10,2)])
        self.assertEqual(result["choices"][0]["message"]["content"],"Глава один")
        self.assertEqual(result["usage"]["completion_tokens"],4)

    def test_truncated_stream(self):
        with self.assertRaises(ValueError):
            writer_stream.read_response(Response(chunk("unfinished")),lambda *_:None)

    def test_json_fallback_same_response(self):
        result={"choices":[{"message":{"content":"text"}}]}
        self.assertEqual(writer_stream.read_response(Response(json.dumps(result).encode(),"application/json"),lambda *_:self.fail("not streamed")),result)

    def test_real_telemetry(self):
        with graph_activity.track("chronicle") as key:
            graph_activity.update(key,"waiting")
            graph_activity.progress(key,7,1)
            graph_activity.progress(key,14,2)
            item=next(a for a in graph_activity.snapshot()["active"] if a["id"]==key)
            self.assertEqual(item["stage"],"streaming")
            self.assertEqual(item["response_chars"],14)
            self.assertEqual(item["chunks"],2)
            self.assertEqual(sum(e["stage"]=="streaming" for e in item["events"]),1)
            graph_activity.update(key,"saved")
