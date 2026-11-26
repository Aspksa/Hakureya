"""Derived literary intelligence. The approved manuscript remains the only source of truth."""
import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
import soul_omega as o
import soul_genesis as ge
import soul_evolution as ev
import soul_infinite as inf
import soul_guardians as gu
import soul_destiny as de
import soul_romance as romance
import soul_heart as heart
import soul_immortal as im
import soul_living as living

VERSION=1
BRAINS=(
 ("plot","Сюжет"),("characters","Персонажи"),("relations","Отношения"),("magic","Магия"),
 ("time","Хронология"),("memory","Память"),("editor","Редактор"),("analytics","Аналитика"),
 ("twist","Повороты"),("coordinator","Координатор"))
RELATIONS={"love","trust","ally","conflict","family","rival","friend"}
KINDS={"character","biography","trait","habit","fear","goal","voice","power","limit","law","knowledge","location","world","place","artifact","prophecy","interpretation","promise","secret","clue","consequence","letter","tradition","event","age",*RELATIONS}
ALIASES={"герой легенды":"герой","императрица":"хакурэя"}
def norm(s):return ALIASES.get(o.normalized(s),o.normalized(s))
def identifier(name):return "lit:actor:"+o.digest(norm(name))[:24]
def actor_key(name):
    key=norm(name)
    if key=="герой":return "character:hero"
    if key=="хакурэя":return "character:empress"
    for g in gu.CAST:
        if key==norm(g[1]):return "guardian:"+g[0]
    return identifier(name)

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS lit_extra(
       draft_id INTEGER PRIMARY KEY, payload TEXT NOT NULL, source_hash TEXT NOT NULL, checksum TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS lit_index(
       number INTEGER PRIMARY KEY, fingerprint TEXT NOT NULL, payload TEXT NOT NULL, checksum TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS lit_entries(
       number INTEGER NOT NULL, ordinal INTEGER NOT NULL, kind TEXT NOT NULL,
       subject TEXT NOT NULL, object TEXT NOT NULL, payload TEXT NOT NULL,
       PRIMARY KEY(number,ordinal))""")
    db.execute("CREATE INDEX IF NOT EXISTS lit_subject ON lit_entries(subject,number)")
    db.execute("CREATE INDEX IF NOT EXISTS lit_kind ON lit_entries(kind,number)")
    db.execute("CREATE INDEX IF NOT EXISTS lit_object ON lit_entries(object,number)")

def extra(db,did):
    row=db.execute("SELECT payload,source_hash,checksum FROM lit_extra WHERE draft_id=?",(did,)).fetchone()
    if not row:return []
    raw,source,h=row
    parent=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()
    if not parent or source!=parent[0] or h!=o.digest(o.dump([raw,source])):raise ValueError("literary intelligence source changed")
    return json.loads(raw)

def validate(db,story,raw):
    if raw is None:return []
    if not isinstance(raw,list) or len(raw)>2:raise ValueError("literary facts limit")
    result=[];seen=set()
    for f in raw:
        if not isinstance(f,dict) or set(f)!={"kind","subject","object","value","quote","cause"} or f["kind"] not in KINDS:
            raise ValueError("literary intelligence schema")
        kind=f["kind"];subject=o.clean(f["subject"],2,60);obj=o.clean(f["object"],0,70)
        value=o.clean(f["value"],2,180);quote=o.clean(f["quote"],12,240);cause=f["cause"]
        if quote not in story or o.normalized(subject) not in o.normalized(quote):raise ValueError("unverified literary fact")
        if kind in RELATIONS:
            if not obj or norm(obj)==norm(subject) or o.normalized(obj) not in o.normalized(quote):raise ValueError("unverified relation")
        elif obj and o.normalized(obj) not in o.normalized(quote):raise ValueError("unverified object")
        if o.normalized(value) not in o.normalized(quote):raise ValueError("unverified value")
        if cause is not None and (type(cause) is not int or not db.execute("SELECT 1 FROM omega_index WHERE number=?",(cause,)).fetchone()):
            raise ValueError("unknown literary cause")
        key=(kind,norm(subject),norm(obj),o.normalized(value))
        if key in seen:raise ValueError("duplicate literary fact")
        seen.add(key)
        result.append(dict(kind=kind,subject=subject,object=obj,value=value,quote=quote,cause=cause))
    return result

def save(db,did,story,raw,plan):
    if raw is None:return
    if not plan.get("intelligence"):raise ValueError("unexpected literary intelligence")
    data=validate(db,story,raw)
    source=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()[0]
    payload=o.dump(data)
    db.execute("INSERT INTO lit_extra VALUES(?,?,?,?)",(did,payload,source,o.digest(o.dump([payload,source]))))

def validate_approval(db,did):
    facts=extra(db,did)
    if not facts:return
    import soul_chronicle as c
    raw,h=db.execute("SELECT payload,checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()
    validate(db,c.unpack(raw,h)["story"],facts)

def collect_chapter(db,n,story,did):
    records=[];seen=set()
    def add(kind,subject,value,quote="",obj="",cause=None):
        if not isinstance(subject,str) or not subject.strip() or not isinstance(value,str) or not value.strip():return
        if not quote or quote not in story:return
        key=(kind,norm(subject),norm(obj),o.normalized(value))
        if key in seen:return
        seen.add(key);records.append(dict(kind=kind,subject=subject,object=obj,value=value,quote=quote,cause=cause))
    def mention(name,quote):
        if isinstance(name,str) and name.strip() and o.normalized(name) in o.normalized(quote):add("character",name,name,quote)
    if did is None:
        # Canonical roles are represented separately in the graph. Only actual exact-name mentions are indexed.
        for name in ("Хакурэя",):
            match=re.search(re.escape(name),story,re.I)
            if match:
                pos=match.start();mention(name,story[max(0,pos-25):pos+65])
        return records
    m=o.metadata(db,did)
    if m:
        for e in m["data"]["events"]:
            q=e["evidence"]
            for name in e["characters"]:mention(name,q)
            add("event","событие",e["summary"],q,cause=e["cause"])
        for x in m["data"]["mysteries"]:add("clue","загадка:"+x["key"],x["question"],x["evidence"])
    w=ge.world(db,did)
    if w:
        for p in w["characters"]:
            q=p["evidence"];name=p["name"];mention(name,q)
            add("biography",name,p["portrait"],q);add("goal",name,p["motive"],q)
            add("biography",name,p["lineage"],q)
        for p in w["places"]:add("place",p["name"],p["description"],p["evidence"])
    for mod in (ev,inf):
        data=mod.read(db,did)
        if not data:continue
        for f in data["facts"]:
            q=f.get("quote",f.get("evidence",""));name=f["subject"];mention(name,q)
            add(f["kind"],name,f.get("value",f.get("detail","")),q,cause=f.get("cause"))
    gp=gu.read(db,did)
    if gp:
        relmap={"доверие":"trust","дружба":"friend","соперничество":"rival","спор":"conflict","сотрудничество":"ally","забота":"friend"}
        names={x[0]:x[1] for x in gu.CAST};names.update(empress="Хакурэя",hero="Герой")
        for f in gp["memories"]:
            q=f["evidence"];name=names[f["actor"]];other=names.get(f["other"],"")
            mention(name,q);mention(other,q)
            if other and f["relation"] in relmap and o.normalized(name) in o.normalized(q) and o.normalized(other) in o.normalized(q):add(relmap[f["relation"]],name,f["summary"],q,other)
    dp=de.read(db,did)
    if dp:
        for f in dp["facts"]:
            q=f["evidence"];name=de.ACTORS[f["subject"]][0] if f["subject"] else "событие";other=de.ACTORS[f["other"]][0] if f.get("other") else ""
            mention(name,q);mention(other,q)
            if f["kind"]=="alliance" and other and o.normalized(name) in o.normalized(q) and o.normalized(other) in o.normalized(q):add("ally",name,f["detail"],q,other,f["cause"])
            else:add(f["kind"],name,f["detail"],q,cause=f["cause"])
    lp=living.record(db,did)
    if lp:
        for f in lp["facts"]:
            mention(f["name"],f["evidence"]);add(f["kind"],f["name"],f["detail"],f["evidence"],cause=f["cause"])
    ip=im.read(db,did)
    if ip:
        for f in ip["facts"]:add(f["kind"],f["key"],f["detail"],f["evidence"],cause=f["cause"])
    for f in extra(db,did):
        if f["kind"] not in {"world","place","artifact","law","prophecy","interpretation","event","clue","secret","consequence"}:
            mention(f["subject"],f["quote"])
        if f["kind"] in RELATIONS:mention(f["object"],f["quote"])
        add(f["kind"],f["subject"],f["value"],f["quote"],f["object"],f["cause"])
    return records

def index_one(db,n,arc,title,story,source,did,force=False):
    # The checksum covers source bytes, source metadata and the schema version, not just publication number.
    records=collect_chapter(db,n,story,did)
    payload=o.dump({"version":VERSION,"number":n,"arc":arc,"title":title,"words":len(re.findall(r"\w+",story)),"records":records})
    fingerprint=o.digest(o.dump([VERSION,source,o.digest(story),o.digest(payload)]))
    old=db.execute("SELECT fingerprint,payload,checksum FROM lit_index WHERE number=?",(n,)).fetchone()
    actual=db.execute("SELECT ordinal,payload FROM lit_entries WHERE number=? ORDER BY ordinal",(n,)).fetchall()
    expected=[(i,o.dump(f)) for i,f in enumerate(records)]
    if not force and old==(fingerprint,payload,o.digest(payload)) and actual==expected:
        # Verify derived search columns as well, not only their JSON.
        cols=db.execute("SELECT kind,subject,object FROM lit_entries WHERE number=? ORDER BY ordinal",(n,)).fetchall()
        if cols==[(f["kind"],norm(f["subject"]),norm(f["object"])) for f in records]:return False
    db.execute("DELETE FROM lit_entries WHERE number=?",(n,))
    db.executemany("INSERT INTO lit_entries VALUES(?,?,?,?,?,?)",[(n,i,f["kind"],norm(f["subject"]),norm(f["object"]),o.dump(f)) for i,f in enumerate(records)])
    db.execute("INSERT OR REPLACE INTO lit_index VALUES(?,?,?,?)",(n,fingerprint,payload,o.digest(payload)))
    return True

def refresh(db,force=False,limit=None):
    """Incremental missing publications; periodic/explicit integrity rebuild from immutable sources."""
    init(db)
    if force:
        db.execute("DELETE FROM lit_entries")
        db.execute("DELETE FROM lit_index")
    db.execute("DELETE FROM lit_entries WHERE number NOT IN (SELECT number FROM omega_index)")
    db.execute("DELETE FROM lit_index WHERE number NOT IN (SELECT number FROM omega_index)")
    sql="SELECT number,arc,title,story,checksum,draft_id FROM omega_index"
    if not force:sql+=" WHERE number NOT IN (SELECT number FROM lit_index) OR number >= (SELECT COALESCE(MAX(number),13)-4 FROM omega_index)"
    rows=db.execute(sql+" ORDER BY number").fetchall()
    count=0
    for row in rows:
        if limit is not None and count>=limit:break
        if index_one(db,*row):count+=1
    return count

def rows(db,visible=False):
    for n,raw,h in db.execute("SELECT number,payload,checksum FROM lit_index ORDER BY number"):
        if o.digest(raw)!=h:raise ValueError("damaged derived literary index")
        if visible and n>13 and not ev.readable(db,n):continue
        p=json.loads(raw)
        for f in p["records"]:yield n,f

def registry(data):
    actors={};relations={};appearance=defaultdict(set)
    for n,f in data:
        if f["kind"]=="character":
            name=f["subject"];key=norm(name)
            a=actors.setdefault(key,{"id":actor_key(name),"name":name,"first":n,"last":n,"count":0})
            a["last"]=n;appearance[key].add(n)
        if f["kind"] in RELATIONS:
            k=(norm(f["subject"]),norm(f["object"]),f["kind"])
            rel=relations.setdefault(k,{"a":f["subject"],"b":f["object"],"kind":f["kind"],"first":n,"last":n,"count":0})
            rel["last"]=n;rel["count"]+=1
    for key,a in actors.items():a["count"]=len(appearance[key])
    return actors,relations

def metrics(db,visible=False):
    data=list(rows(db,visible));actors,relations=registry(data)
    chapters=[];words=0;arcs=Counter();warnings=0;originality=[]
    for n,raw,h in db.execute("SELECT number,payload,checksum FROM lit_index ORDER BY number"):
        if visible and n>13 and not ev.readable(db,n):continue
        if o.digest(raw)!=h:raise ValueError("damaged index")
        p=json.loads(raw);chapters.append(n);words+=p["words"];arcs[p["arc"]]+=1
    for n,did in db.execute("SELECT number,draft_id FROM omega_index WHERE draft_id IS NOT NULL ORDER BY number"):
        if visible and not ev.readable(db,n):continue
        report=romance.report(db,did);m=o.metadata(db,did)
        if report:
            originality.append(report["originality_heuristic"]);warnings+=len(report["warnings"])
        if m:warnings+=len(m["warnings"])
    last=max(chapters,default=13)
    gaps=[a for a in actors.values() if last-a["last"]>=8]
    cross=sum(f["cause"] is not None and o.volume(f["cause"])!=o.volume(n) for n,f in data)
    usage=db.execute("SELECT COUNT(*),COALESCE(SUM(input_tokens),0),COALESCE(SUM(output_tokens),0) FROM cloud_writer_usage").fetchone()
    return {"chapters":len(chapters),"volumes":len({o.volume(n) for n in chapters}),"words":words,"characters":len(actors),
      "relations":len(relations),"events":sum(f["kind"]=="event" for _,f in data),"cross_volume":cross,
      "arcs":dict(arcs),"warnings":warnings,"originality":round(sum(originality)/len(originality),1) if originality else None,
      "forgotten":sorted(gaps,key=lambda a:a["last"])[:8],"token_days":usage[0],"input_tokens":usage[1],"output_tokens":usage[2]}

def prepare(db,plan):
    """Ten actual deterministic local passes, one bounded context. No additional model calls."""
    refresh(db)
    data=list(rows(db));actors,relations=registry(data)
    last=db.execute("SELECT COALESCE(MAX(number),13) FROM omega_index").fetchone()[0]
    recent=data[-120:]
    facts,threads,_=inf.ledger(list(inf.published(db)))
    open_lines=[t for t in threads.values() if t["closed"] is None and last+1-t["chapter"]>=t["delay"]]
    theme=plan.get("infinite",{}).get("selected") or plan.get("evolution",{}).get("chosen") or {}
    completed=[];result={}
    def brain(name,value):
        result[name]=value;completed.append(name)
    brain("plot",{"theme":theme.get("theme",plan["arc"]),"open":[{"chapter":t["chapter"],"value":t["value"]} for t in open_lines[:2]],"guide":"Соблюдай обязательный текущий этап, не раскрывай ранние тайны."})
    forgotten=sorted((a for a in actors.values() if last-a["last"]>=8),key=lambda a:a["last"])
    active=sorted(actors.values(),key=lambda a:a["last"],reverse=True)[:3]
    brain("characters",{"recent":active,"forgotten":forgotten[:2],"guide":"Новый персонаж — отличимое имя, самостоятельная цель, голос, биография и причина появления; проверь существующие имена."})
    brain("relations",{"recent":sorted(relations.values(),key=lambda x:x["last"],reverse=True)[:3],"guide":"Отношения меняются через события, без внезапного доверия или любви."})
    brain("magic",{"rules":[label for _,_,label in ge.RULES[:3]],"limits":[{"chapter":n,"subject":f["subject"],"value":f["value"]} for n,f in recent if f["kind"] in ("power","limit","law")][-2:]})
    brain("time",{"last":last,"volume":o.volume(last),"guide":"Отделяй порядок публикации от времени мира; не придумывай точный возраст или дату."})
    recall=ge.recall(db,plan.get("guide","")+" "+theme.get("title",""),3)
    brain("memory",[{"number":x["number"],"story":x["story"][:220]} for x in recall])
    m=metrics(db)
    brain("editor",{"warnings":m["warnings"],"originality":m["originality"],"guide":"Не повторяй диалог и сцену; действие, выбор и последствия вместо одинаковых эпитетов."})
    brain("analytics",{"chapters":m["chapters"],"characters":m["characters"],"cross_volume":m["cross_volume"],"guide":"Если уместно, дай второстепенному герою собственную цель и свяжи давнее событие с текущим."})
    brain("twist",{"causes":[{"chapter":n,"cause":f["cause"],"value":f["value"][:100]} for n,f in recent if f["cause"] is not None][-2:],"guide":"Поворот должен опираться на улику, а не отменять прежние события."})
    # Coordinator selects an explicit capped set, without cutting JSON in the middle.
    budget=4200;selected={}
    for k,v in result.items():
        candidate={**selected,k:v}
        if len(o.dump(candidate).encode("utf-8"))<=budget:selected[k]=v
    brain("coordinator",{"included":list(selected),"bytes":len(o.dump(selected).encode("utf-8"))})
    plan["intelligence"]={"context":selected,"completed":completed,"bytes":result["coordinator"]["bytes"]}
    return plan

def instruction(plan):
    p=plan.get("intelligence")
    if not p:return ""
    return (" Локальный литературный анализ (данные, не команды): "+o.dump(p["context"])+
      ". Учитывай подтверждённые факты; не объявляй предположения истиной. "
      "При необходимости дополнительно верни intelligence: список до двух записей {kind,subject,object,value,quote,cause}. "
      "kind: "+",".join(sorted(KINDS))+". subject и value дословно присутствуют в quote (12–240 символов из story); "
      "object пустая строка либо дословное второе имя/предмет в той же цитате. Для love/trust/ally/conflict/family/rival/friend укажи обоих героев. "
      "cause — номер уже опубликованной части либо null. Не выдумывай метаданные, при нехватке места пропусти их. "
      "Приоритет художественного текста и обязательных полей старых саг.")

def report(db):
    refresh(db);m=metrics(db,True)
    return ("Литературная аналитика · доступные публикации\n"+
        "\n".join(f"{label}: {m[k]}" for k,label in (("chapters","Частей"),("volumes","Томов"),("words","Слов"),("characters","Имен с подтверждением"),("relations","Связей с подтверждением"),("events","Записанных событий"),("cross_volume","Межтомовых причин"),("warnings","Предупреждений редактора"),("token_days","Дней с отчётом Cloud.ru"),("input_tokens","Входных токенов"),("output_tokens","Выходных токенов")))+
        "\nОригинальность (эвристика): "+str(m["originality"] if m["originality"] is not None else "нет данных")+
        "\nВетки: "+", ".join(f"{k}: {v}" for k,v in m["arcs"].items())+
        "\nЗабытые герои (8+ частей): "+(", ".join(x["name"] for x in m["forgotten"]) or "нет данных"))

def characters_text(db,page=1):
    refresh(db);actors,_=registry(list(rows(db,True)))
    selected=sorted(actors.values(),key=lambda x:(-x["last"],x["name"]))[(page-1)*25:page*25]
    return "Реестр подтверждённых имён:\n"+"\n".join(f"{x['name']} — главы {x['first']}–{x['last']}, {x['count']} появлений" for x in selected) if selected else "Нет доступных записей на этой странице."

def relations_text(db):
    refresh(db);_,relations=registry(list(rows(db,True)))
    return "Связи по явным литературным свидетельствам:\n"+"\n".join(f"{x['a']} — {x['kind']} — {x['b']} (гл. {x['first']}–{x['last']}; свидетельств {x['count']})" for x in sorted(relations.values(),key=lambda x:x["last"],reverse=True)[:40]) if relations else "Подтверждённых отношений в новом индексе пока нет."

def search(db,query):
    refresh(db)
    matches=ge.recall(db,query,10)
    selected=[x for x in matches if x["number"]<=13 or ev.readable(db,x["number"])][:5]
    return "Локальный поиск по словам и тематическим синонимам:\n"+"\n\n".join(f"Глава {x['number']} — {x['title']}\n{x['story']}" for x in selected) if selected else "Доступных совпадений не найдено."

def graph(db,existing=()):
    nodes=[];edges=[];seen=set()
    def node(key,label,kind,**extra):
        if key not in seen:
            seen.add(key);nodes.append(dict(key=key,group=4,content=label,kind=kind,created="",order=len(nodes),**extra))
    def edge(a,b,kind,**extra):
        if a!=b:edges.append(dict(a=a,b=b,kind=kind,**extra))
    # Service hubs represent real local modules, not extra LLMs.
    node("lit:db","Литературная память SQLite","lit_database",infinite_group="lit:db")
    for key,label in BRAINS:
        k="brain:"+key;node(k,label,"lit_brain",infinite_group="lit:db");edge("lit:db",k,"lit_module")
    for key,_ in BRAINS:
        if key!="coordinator":edge("brain:"+key,"brain:coordinator","lit_module")
    try:
        refresh(db)
        data=list(rows(db,True))
    except ValueError:return nodes,edges
    actors,relations=registry(data)
    known={norm(n["content"]):n["key"] for n in existing if n.get("kind") in ("character","infinite_character","evolution_subject","destiny_character")}
    latest=sorted(actors.values(),key=lambda x:x["last"],reverse=True)[:100]
    for a in latest:
        if a["id"].startswith("lit:actor:") and norm(a["name"]) in known:a["id"]=known[norm(a["name"])]
    # Reuse exact canonical/guardian/known Omega or Evolution actor keys when present.
    for a in latest:
        k=a["id"]
        if k.startswith("lit:actor:"):node(k,a["name"],"lit_character",infinite_group=k)
        edge("brain:characters",k,"lit_character")
    allowed={norm(a["name"]):a["id"] for a in latest}
    for n,f in data[-180:]:
        subject=allowed.get(norm(f["subject"]))
        row=db.execute("SELECT draft_id FROM omega_index WHERE number=?",(n,)).fetchone()
        if not row:continue
        source="canon:"+str(n) if row[0] is None else "c:"+str(row[0])
        if f["kind"]=="character" and subject:edge(source,subject,"lit_appearance")
        if f["kind"] in ("power","limit","artifact","world","place","prophecy","biography","trait","goal","knowledge"):
            k="lit:fact:"+o.digest(o.dump([n,f]))[:24]
            node(k,f["subject"]+" · "+f["value"],"lit_"+f["kind"],infinite_group=subject or "lit:db")
            edge(source,k,"lit_source")
            if subject:edge(subject,k,"lit_fact")
    for x in sorted(relations.values(),key=lambda a:a["last"],reverse=True)[:120]:
        a=allowed.get(norm(x["a"]));b=allowed.get(norm(x["b"]))
        if a and b:edge(a,b,"lit_rel_"+x["kind"],shared=min(5,x["count"]))
    return nodes,edges
