"""In-process activity telemetry, independent of database and chat locks."""
from contextlib import contextmanager
from threading import Lock
from time import monotonic
from uuid import uuid4

LOCK=Lock()
ACTIVE={}
RECENT={}
SESSION=uuid4().hex
REV=0

def update(key,stage,target=None):
    global REV
    with LOCK:
        item=ACTIVE.get(key)
        if item is None:
            return
        item["stage"]=stage
        if target is not None:
            item["target"]=target
        REV+=1

@contextmanager
def track(kind,source="root"):
    global REV
    if kind not in ("chat","chronicle"):
        raise ValueError("unknown activity")
    key=uuid4().hex
    with LOCK:
        ACTIVE[key]={"id":key,"kind":kind,"source":source,"target":"root","stage":"request"}
        REV+=1
    try:
        yield key
    except BaseException:
        update(key,"error")
        raise
    finally:
        with LOCK:
            item=ACTIVE.pop(key)
            stage=item["stage"]
            item["stage"]=stage if stage in ("done","error","discarded") else "error"
            RECENT[key]=(monotonic(),item)
            while len(RECENT)>32:
                del RECENT[next(iter(RECENT))]
            REV+=1

def snapshot():
    now=monotonic()
    with LOCK:
        for key,(when,_) in list(RECENT.items()):
            if now-when>3:
                del RECENT[key]
        return {"session":SESSION,"revision":REV,
                "active":[dict(a) for a in ACTIVE.values()],
                "recent":[dict(a) for _,a in RECENT.values()]}
