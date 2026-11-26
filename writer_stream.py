"""Bounded OpenAI-compatible writer stream; never expose reasoning or retry a paid call."""
import json

MAX_WIRE=1_000_000
MAX_TEXT=24_000

def read_response(response,on_progress,on_preview=None):
    content_type=getattr(response,"headers",{}).get("Content-Type","")
    if not isinstance(content_type,str) or "text/event-stream" not in content_type.lower():
        raw=response.read(MAX_WIRE+1)
        if len(raw)>MAX_WIRE:raise ValueError("writer response too large")
        return json.loads(raw)
    parts=[]
    size=wire=0
    reason=None
    usage=None
    finished=False
    event=[]
    def consume(lines):
        nonlocal size,reason,usage,finished
        if not lines:return
        data="\n".join(lines)
        if data=="[DONE]":
            finished=True
            return
        obj=json.loads(data)
        if not isinstance(obj,dict) or obj.get("error"):raise ValueError("writer stream error")
        if isinstance(obj.get("usage"),dict):usage=obj["usage"]
        choices=obj.get("choices",[])
        if not isinstance(choices,list) or len(choices)>1:raise ValueError("unexpected writer choices")
        if not choices:return
        choice=choices[0]
        if not isinstance(choice,dict) or choice.get("index",0)!=0:raise ValueError("unexpected writer choice")
        delta=choice.get("delta") or {}
        if not isinstance(delta,dict):raise ValueError("invalid writer delta")
        chunk=delta.get("content")
        if chunk is not None and not isinstance(chunk,str):raise ValueError("invalid writer fragment")
        if chunk:
            if reason is not None:raise ValueError("content after finish")
            size+=len(chunk)
            if size>MAX_TEXT:raise ValueError("writer response too large")
            parts.append(chunk)
            on_progress(size,len(parts))
            if on_preview:on_preview("".join(parts))
        if choice.get("finish_reason") is not None:reason=choice["finish_reason"]
    while not finished:
        raw=response.readline(MAX_WIRE-wire+1)
        if not raw:
            consume(event)
            break
        wire+=len(raw)
        if wire>MAX_WIRE:raise ValueError("writer stream too large")
        line=raw.decode("utf-8").rstrip("\r\n")
        if not line:
            consume(event)
            event=[]
        elif line.startswith("data:"):
            event.append(line[5:].lstrip(" "))
    if not parts or reason not in ("stop","length"):raise ValueError("incomplete writer stream")
    return {"choices":[{"message":{"content":"".join(parts)},"finish_reason":reason}],"usage":usage}
