"""Typed, bounded local handoffs between the existing literary brains.

The network is a deterministic DAG, not ten LLMs. All handoffs contain only
local derived literary data; telemetry exports sizes and identifiers, not text.
"""
import json
from time import perf_counter
import soul_omega as o

VERSION=1
ORDER=("plot","characters","relations","magic","time","memory","editor","analytics","twist","coordinator")
DEPENDENCIES={
    "plot":(),
    "characters":("plot",),
    "relations":("characters","plot"),
    "magic":("plot","characters"),
    "time":("plot","magic"),
    "memory":("plot","characters","time","magic"),
    "editor":("relations","magic","time","memory"),
    "analytics":("characters","relations","editor"),
    "twist":("plot","memory","time","analytics"),
    "coordinator":ORDER[:-1],
}
FIELDS={
    "plot":("theme","open","guide"),
    "characters":("recent","forgotten","profiles","guide"),
    "relations":("recent","guide"),
    "magic":("rules","limits"),
    "time":("last","volume","guide"),
    "memory":None,
    "editor":("warnings","originality","last_scene_words","guide"),
    "analytics":("chapters","characters","cross_volume","profile_gaps","rapid_relations","guide"),
    "twist":("causes","guide"),
    "coordinator":("included","bytes"),
}
MAX_PACKET=16000
LIST_FIELDS={"open","recent","forgotten","profiles","rules","limits","profile_gaps","rapid_relations","causes","included"}
TEXT_FIELDS={"theme","guide"}
INT_FIELDS={"last","volume","warnings","last_scene_words","chapters","characters","cross_volume","bytes"}
CONTEXT_BUDGET=4200

def size(value):
    return len(o.dump(value).encode("utf-8"))

def validate_topology():
    if tuple(DEPENDENCIES)!=ORDER or set(FIELDS)!=set(ORDER):raise ValueError("network topology")
    for pos,key in enumerate(ORDER):
        parents=DEPENDENCIES[key]
        if len(set(parents))!=len(parents) or not set(parents)<=set(ORDER[:pos]):raise ValueError("network dependency order")
    if set(DEPENDENCIES["coordinator"])!=set(ORDER[:-1]):raise ValueError("coordinator coverage")

def validate_output(key,value):
    if key=="memory":
        if not isinstance(value,list) or any(not isinstance(x,dict) or type(x.get("number")) is not int or not isinstance(x.get("story"),str) for x in value):raise ValueError("memory contract")
    else:
        if not isinstance(value,dict) or not set(FIELDS[key])<=set(value):raise ValueError("brain contract: "+key)
    if isinstance(value,dict):
        for field in FIELDS[key]:
            v=value[field]
            if field in LIST_FIELDS and not isinstance(v,list):raise ValueError("brain list field: "+key+"."+field)
            if field in TEXT_FIELDS and not isinstance(v,str):raise ValueError("brain text field: "+key+"."+field)
            if field in INT_FIELDS and (type(v) is not int or v<0):raise ValueError("brain integer field: "+key+"."+field)
        if key=="time" and (type(value.get("scope_last")) is not int or not 0<=value["scope_last"]<=value["last"] or value.get("arc") not in ("past","meeting","love","future")):raise ValueError("time scope")
        if key=="editor" and not isinstance(value.get("check_sources"),list):raise ValueError("editor source contract")
        if key=="analytics" and not isinstance(value.get("editor_sources"),list):raise ValueError("analytics source contract")
        if key=="coordinator" and (set(value["included"])!=set(ORDER[:-1]) or not 0<value["bytes"]<=CONTEXT_BUDGET):raise ValueError("coordinator coverage")
    if size(value)>MAX_PACKET:raise ValueError("brain packet limit")

class Network:
    def __init__(self):
        validate_topology()
        self.outputs={}
        self.events=[]
        self.started=perf_counter()
        self.inflight=None
    def begin(self,key):
        if self.inflight is not None or len(self.outputs)>=len(ORDER) or ORDER[len(self.outputs)]!=key:raise ValueError("brain execution order")
        inputs={}
        transfers=[]
        for parent in DEPENDENCIES[key]:
            value=self.outputs[parent]
            validate_output(parent,value)
            # Copy so the consumer cannot mutate another brain's result.
            inputs[parent]=json.loads(o.dump(value))
            transfers.append({"from":parent,"to":key,"bytes":size(value)})
        self.inflight=(key,perf_counter(),transfers)
        return inputs
    def finish(self,key,value):
        if self.inflight is None or self.inflight[0]!=key:raise ValueError("brain not started")
        validate_output(key,value)
        _,started,transfers=self.inflight
        self.outputs[key]=json.loads(o.dump(value))
        self.events.append({"brain":key,"duration_ms":round((perf_counter()-started)*1000,3),
            "bytes":size(value),"inputs":transfers})
        self.inflight=None
        return value
    def trace(self,selected):
        if self.inflight or tuple(self.outputs)!=ORDER or set(selected)!=set(ORDER[:-1]):raise ValueError("incomplete network")
        return {"version":VERSION,"events":self.events,"included":list(selected),
                "context_bytes":size(selected),"duration_ms":round((perf_counter()-self.started)*1000,3)}

def compact(outputs):
    """Mandatory contribution from all nine modules; expand only within a strict cap."""
    if set(outputs)!=set(ORDER[:-1]):raise ValueError("missing coordinator input")
    # Keep one small meaningful field per module even for large profiles.
    selected={
        "plot":{"theme":outputs["plot"]["theme"],"guide":outputs["plot"]["guide"][:140]},
        "characters":{"profiles":[],"guide":outputs["characters"]["guide"][:140]},
        "relations":{"recent":[],"guide":outputs["relations"]["guide"][:140]},
        "magic":{"rules":outputs["magic"]["rules"][:1],"limits":[]},
        "time":{"last":outputs["time"]["last"],"volume":outputs["time"]["volume"],"guide":outputs["time"]["guide"][:140]},
        "memory":[],
        "editor":{"warnings":outputs["editor"]["warnings"],"guide":outputs["editor"]["guide"][:140]},
        "analytics":{"chapters":outputs["analytics"]["chapters"],"guide":outputs["analytics"]["guide"][:140]},
        "twist":{"causes":[],"guide":outputs["twist"]["guide"][:140]},
    }
    if size(selected)>CONTEXT_BUDGET:raise ValueError("minimal context too large")
    # Add a first evidence item before attempting larger full packets.
    for key in ORDER[:-1]:
        value=outputs[key]
        if isinstance(value,list):candidate=value[:1]
        else:
            candidate={**selected[key],**{k:v[:1] if isinstance(v,list) else v[:180] if isinstance(v,str) else v for k,v in value.items()}}
        attempt={**selected,key:candidate}
        if size(attempt)<=CONTEXT_BUDGET:selected=attempt
    for key in ORDER[:-1]:
        attempt={**selected,key:outputs[key]}
        if size(attempt)<=CONTEXT_BUDGET:selected=attempt
    return selected

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS neural_runs(
        attempt TEXT PRIMARY KEY,payload TEXT NOT NULL,checksum TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS neural_diagnostic(id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL,checksum TEXT NOT NULL)""")

def validate_trace(trace):
    if trace.get("version")!=VERSION or set(trace.get("included",[]))!=set(ORDER[:-1]):raise ValueError("network trace version or coverage")
    if type(trace.get("context_bytes")) is not int or not 0<trace["context_bytes"]<=CONTEXT_BUDGET:raise ValueError("network context size")
    events=trace.get("events",[])
    if tuple(e["brain"] for e in events)!=ORDER:raise ValueError("network trace order")
    previous={}
    for e in events:
        k=e["brain"]
        if type(e["bytes"]) is not int or not 0<e["bytes"]<=MAX_PACKET:raise ValueError("network output size")
        if type(e["duration_ms"]) not in (float,int) or not 0<=e["duration_ms"]<1e9:raise ValueError("network duration")
        if tuple(x["from"] for x in e["inputs"])!=DEPENDENCIES[k]:raise ValueError("network inputs")
        if any(x["to"]!=k or x["bytes"]!=previous[x["from"]] for x in e["inputs"]):raise ValueError("network handoff size")
        previous[k]=e["bytes"]
    return trace

def record(db,attempt,trace):
    validate_trace(trace)
    raw=o.dump(trace)
    db.execute("INSERT INTO neural_runs VALUES(?,?,?)",(attempt,raw,o.digest(raw)))

def record_diagnostic(db,trace):
    validate_trace(trace)
    raw=o.dump(trace)
    db.execute("INSERT OR REPLACE INTO neural_diagnostic VALUES(1,?,?)",(raw,o.digest(raw)))

def latest(db):
    row=db.execute("SELECT payload,checksum FROM neural_runs ORDER BY attempt DESC LIMIT 1").fetchone()
    if not row:return None
    if o.digest(row[0])!=row[1]:raise ValueError("network trace checksum")
    return validate_trace(json.loads(row[0]))

def edges():
    return [{"a":"brain:"+parent,"b":"brain:"+key,"kind":"neural_input"} for key in ORDER for parent in DEPENDENCIES[key]]

def snapshot(db,labels):
    trace=latest(db)
    origin="writer" if trace else None
    if not trace:
        row=db.execute("SELECT payload,checksum FROM neural_diagnostic WHERE id=1").fetchone()
        if row:
            if o.digest(row[0])!=row[1]:raise ValueError("diagnostic checksum")
            trace=validate_trace(json.loads(row[0]));origin="diagnostic"
    events={e["brain"]:e for e in trace["events"]} if trace else {}
    records=[dict(key="lit:db",label="SQLite · литературная память",group=4,kind="lit_database",slot=0)]
    for pos,(key,label) in enumerate(labels,1):
        e=events.get(key)
        records.append(dict(key="brain:"+key,label=label,group=4,kind="lit_brain",slot=pos,
          neural_inputs=list(DEPENDENCIES[key]),neural_ms=e["duration_ms"] if e else None,neural_bytes=e["bytes"] if e else None))
    links=edges()+[dict(a="lit:db",b="brain:"+k,kind="neural_source") for k in ("plot","characters","relations","magic","time","memory","editor","analytics","twist")]
    links.append(dict(a="brain:coordinator",b="root",kind="neural_output"))
    return dict(records=records,edges=links,total=10,limited=False,network=True,neural_trace=trace,trace_origin=origin)

def report(db,trace):
    validate_trace(trace)
    lines=["Локальная нейросеть: 10/10 проходов; 9/9 разделов контекста.",
           "Передача данных: "+str(sum(len(e["inputs"]) for e in trace["events"]))+" проверенных зависимостей.",
           "Контекст: "+str(trace["context_bytes"])+"/4200 байт."]
    for e in trace["events"]:
        lines.append(e["brain"]+": "+str(e["duration_ms"])+" мс, "+str(e["bytes"])+" байт; входы: "+(", ".join(x["from"] for x in e["inputs"]) or "SQLite/план"))
    return "\n".join(lines)+"\nЛокальные проверки форматов и передачи, не тест понимания модели Cloud.ru."
