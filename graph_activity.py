"""In-process telemetry: bounded, no prompt text, key, model thoughts or tokens."""
from contextlib import contextmanager
from threading import Lock
from time import monotonic
from uuid import uuid4
import re

LOCK=Lock()
ACTIVE={}
RECENT={}
SESSION=uuid4().hex
REV=0
TERMINAL=("done","error","discarded","published","saved")
BRAIN_STAGES=tuple("brain:"+x for x in ("plot","characters","relations","magic","time","memory","editor","analytics","twist","coordinator"))
STAGES=("request","context","waiting","streaming","received","validating","saving",*BRAIN_STAGES,*TERMINAL)
KEY=re.compile(r"[a-zA-Z0-9:_-]{1,100}")

def safe_key(value):
    return value if isinstance(value,str) and KEY.fullmatch(value) else "root"

def update(key,stage,target=None,duration_ms=None):
    global REV
    if stage not in STAGES:raise ValueError("unknown stage")
    with LOCK:
        item=ACTIVE.get(key)
        if item is None:return
        item["stage"]=stage
        item["_heartbeat"]=monotonic()
        if target is not None:item["target"]=safe_key(target)
        REV+=1
        event={"seq":REV,"stage":stage,"target":item["target"]}
        if type(duration_ms) in (int,float) and 0<=duration_ms<1e9:event["duration_ms"]=duration_ms
        item["events"].append(event)
        item["events"]=item["events"][-24:]

def progress(key,chars,chunks):
    """Count only received output content, never model reasoning or text."""
    global REV
    with LOCK:
        item=ACTIVE.get(key)
        if item is None or item["kind"]!="chronicle":return
        if item["stage"] not in ("waiting","streaming"):return
        if item["stage"]!="streaming":
            item["stage"]="streaming"
            REV+=1
            item["events"].append({"seq":REV,"stage":"streaming","target":item["target"]})
            item["events"]=item["events"][-24:]
        item["_heartbeat"]=monotonic()
        item["response_chars"]=chars
        item["chunks"]=chunks
        REV+=1

@contextmanager
def track(kind,source="root",sources=()):
    global REV
    if kind not in ("chat","chronicle"):raise ValueError("unknown activity")
    key=uuid4().hex
    with LOCK:
        REV+=1
        ACTIVE[key]={"id":key,"kind":kind,"source":safe_key(source),"sources":list(dict.fromkeys(safe_key(s) for s in sources))[:16],
            "_started":monotonic(),"_heartbeat":monotonic(),"target":"root","stage":"request","events":[{"seq":REV,"stage":"request","target":"root"}]}
    try:
        yield key
    except BaseException:
        update(key,"error")
        raise
    finally:
        with LOCK:
            item=ACTIVE.pop(key)
            if item["stage"] not in TERMINAL:
                item["stage"]="error"
                REV+=1
                item["events"].append({"seq":REV,"stage":"error","target":item["target"]})
            RECENT[key]=(monotonic(),item)
            while len(RECENT)>32:del RECENT[next(iter(RECENT))]
            REV+=1

def snapshot():
    now=monotonic()
    with LOCK:
        for key,(when,_) in list(RECENT.items()):
            if now-when>12:del RECENT[key]
        def copy(a):
            value={k:v for k,v in a.items() if not k.startswith("_")}
            value.update(age_seconds=round(max(0,now-a["_started"])),idle_seconds=round(max(0,now-a["_heartbeat"])),sources=list(a["sources"]),events=[dict(e) for e in a["events"]])
            value["stalled"]=a["kind"]=="chronicle" and a["stage"] not in TERMINAL and (value["age_seconds"]>=300 or value["idle_seconds"]>=180)
            return value
        return {"session":SESSION,"revision":REV,"active":[copy(a) for a in ACTIVE.values()],
                "recent":[copy(a) for _,a in RECENT.values()]}
