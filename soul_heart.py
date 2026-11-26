"""Eternal Heart: a literary relationship model, never real emotions or user facts."""
import re
import json
from collections import Counter
import soul_omega as o
import soul_genesis as g

VERSION=1
TOPICS=("meeting","tenderness","trust","memory","letters","adventure")
LABELS={"meeting":"Знакомство","tenderness":"Нежность и признания","trust":"Доверие и выбор","memory":"Воспоминания","letters":"Письма и дневник","adventure":"Совместные приключения"}
EMOTIONS=("удивление","смущение","нежность","доверие","радость","тревога","гордость","восхищение","спокойствие","решимость")
# Exact excerpts from immutable canon, not synthetic memories.
CANON=(
 (5,"meeting","Первое тепло","Не... отпускай меня пока.","удивление","смущение",None),
 (6,"tenderness","Открытие нежности","В нём впервые появилась открытая нежность.","удивление","нежность",5),
 (7,"trust","Уважение границ","Ты не стал настаивать.","гордость","доверие",6),
 (8,"memory","Разговоры о прошлом","Она стала смеяться, проявлять нежность, рассказывать о своём прошлом","доверие","радость",7),
 (9,"tenderness","Признание любви","Я люблю тебя.","волнение","нежность",8),
 (10,"trust","Свободный выбор","Моё возвращение на трон не изменит моего выбора.","гордость","решимость",9),
 (11,"trust","Добровольное доверие","Я по-прежнему останусь гордой.","гордость","доверие",10),
 (12,"adventure","Совместное созидание","И особенно нравилось видеть, как вы вместе создаёте","любопытство","радость",11),
 (13,"letters","Сокровенный дневник","Он не лишил меня императорской гордости.","гордость","нежность",12),
)
# Planned scene lenses, not events until written and approved.
LENSES={
 "meeting":("Первые дни: удивление простым человеческим привычкам","Разговор о необычном прикосновении без повторного спасения","Самостоятельный выбор принять помощь"),
 "tenderness":("Нежность выражается поступком, а не очередным признанием","Сдержанная шутка императрицы скрывает смущение","Романтическая пауза после совместного решения"),
 "trust":("Несогласие и уважение разных решений","Героиня решает поделиться трудным воспоминанием","Герой и императрица помогают друг другу, сохраняя самостоятельность"),
 "memory":("Старое воспоминание меняет решение в настоящем","Сравнение одиночества при дворе и новой жизни без пересказа","Две точки зрения на одно значимое событие"),
 "letters":("Письмо о конкретном событии и его последствиях","Невысказанная мысль в художественном дневнике","Ответное письмо героя как самостоятельный поступок"),
 "adventure":("Совместная задача в одном из небесных царств","Человеческий праздник с неожиданным открытием","Романтическая сцена после решения реальной сюжетной проблемы"),
}

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS heart_drafts(
       draft_id INTEGER PRIMARY KEY, payload TEXT NOT NULL, checksum TEXT NOT NULL,
       source_hash TEXT NOT NULL, version INTEGER NOT NULL)""")
    db.execute("CREATE TABLE IF NOT EXISTS heart_original(draft_id INTEGER PRIMARY KEY,payload TEXT NOT NULL,checksum TEXT NOT NULL)")
    db.execute("""CREATE TABLE IF NOT EXISTS heart_slots(
       key TEXT PRIMARY KEY, topic TEXT NOT NULL, slot INTEGER NOT NULL, UNIQUE(topic,slot))""")

def chapter_key(db,n):
    row=db.execute("SELECT draft_id FROM omega_index WHERE number=?",(n,)).fetchone()
    return (f"c:{row[0]}" if row[0] is not None else f"canon:{n}") if row else None

def canon_events(db):
    for n,topic,title,quote,before,after,parent in CANON:
        row=db.execute("SELECT story FROM omega_index WHERE number=?",(n,)).fetchone()
        if row and quote in row[0]:
            yield {"chapter":n,"key":f"heart:canon:{n}","topic":topic,"title":title,"evidence":quote,
                   "before":before,"after":after,"cause":parent,"effect":"","thread":None,"source":"canon"}

def read(db,did):
    row=db.execute("SELECT payload,checksum,source_hash FROM heart_drafts WHERE draft_id=?",(did,)).fetchone()
    if not row:return None
    if o.digest(row[0])!=row[1]:raise ValueError("damaged heart record")
    source=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()
    if not source or source[0]!=row[2]:raise ValueError("heart source mismatch")
    return json.loads(row[0])

def published(db):
    yield from canon_events(db)
    for n,did in db.execute("""SELECT i.number,i.draft_id FROM omega_index i JOIN chronicle_drafts d ON d.id=i.draft_id
            WHERE d.status='approved' ORDER BY i.number"""):
        try: data=read(db,did)
        except ValueError:continue
        if data:
            for index,item in enumerate(data["moments"]):
                yield {**item,"chapter":n,"key":f"heart:moment:{did}:{index}","source":"approved"}

def threads(db):
    state={}
    for p in published(db):
        t=p["thread"]
        if not t:continue
        key=t["key"]
        if t["action"]=="open" and key not in state:
            state[key]={"title":t["title"],"opened":p["chapter"],"closed":None}
        elif t["action"]=="resolve" and key in state and state[key]["closed"] is None:
            state[key]["closed"]=p["chapter"]
    return state

def choose(db,arc):
    if arc=="past":
        return {"topic":"memory","lens":"Раскрой прошлое императрицы без знакомства с героем; только предпосылки будущих чувств"}
    allowed=("meeting","trust","memory") if arc=="meeting" else ("tenderness","trust","memory","letters","adventure")
    history=[p for p in published(db) if p["source"]=="approved"]
    counts=Counter(p["topic"] for p in history)
    recent=Counter(p["topic"] for p in history[-6:])
    topic=min(allowed,key=lambda k:(recent[k],counts[k],allowed.index(k)))
    return {"topic":topic,"lens":LENSES[topic][counts[topic]%len(LENSES[topic])]}

def enrich(db,plan):
    choice=choose(db,plan["arc"])
    old=list(published(db))
    recalls=g.recall(db,choice["lens"],3)
    plan["heart"]={**choice,"future_lenses":[{"topic":t,"lens":LENSES[t][0]} for t in TOPICS if t!=choice["topic"]][:4],"recent":[{k:p[k] for k in ("chapter","title","before","after","effect")} for p in old[-5:]],
                   "threads":[{"key":k,**v} for k,v in threads(db).items() if v["closed"] is None][:4],
                   "recall":[{"chapter":p["number"],"title":p["title"],"excerpt":p["story"][:350]} for p in recalls]}
    return plan

def instruction(plan):
    p=plan.get("heart")
    if not p:return ""
    return (" Режиссёр художественной любви: "+o.dump(p)+
        ". Сохрани императорскую гордость, властность, свободу выбора и уважение обоих взрослых вымышленных героев. "
        " Раскрой, почему чувство возникает именно сейчас: ситуация, внутренний конфликт, выбор, реакция второго героя, эмоциональное последствие. "
        " Не повторяй признания и первые прикосновения; если вспомнила прошлое, покажи новое понимание. "
        " Пиши выразительно, с индивидуальными голосами, паузами, жестами, мимикой, движениями ушей и хвостов лишь по смыслу, "
        " живыми деталями места, взаимной нежностью, объятиями и поцелуями по взаимному желанию. "
        " Чередуй тишину, юмор, приключение, драму, письма, взгляды обоих героев. Не заменяй действие длинным перечислением чувств. "
        " Не изображай романтические события до знакомства. Не пересказывай канон и не раскрывай поворот без основания. "
        " Если есть место в JSON, добавь необязательный объект heart: {moments:[{topic,title,evidence,before,after,cause,effect,thread}]}. "
        " Не более одного значимого момента; topic из "+", ".join(TOPICS)+
        "; before/after из "+", ".join(EMOTIONS)+
        "; evidence — точная цитата из story, cause — номер существующей опубликованной главы или null, effect — конкретное художественное последствие из текста, "
        " effect — дословный фрагмент story, либо пустая строка. thread — null или {key,action,title}, action open/resolve, ключ латиницей. Не придумывай ссылки. При нехватке места отдай приоритет полному тексту сцены.")

def validate(db,story,raw,arc):
    if raw is None:return {"moments":[]}
    if not isinstance(raw,dict) or set(raw)!={"moments"} or not isinstance(raw["moments"],list) or len(raw["moments"])>1:
        raise ValueError("invalid heart fields")
    if arc=="past" and raw["moments"]:raise ValueError("romance before meeting")
    result=[]; known=threads(db)
    for p in raw["moments"]:
        if not isinstance(p,dict) or set(p)!={"topic","title","evidence","before","after","cause","effect","thread"}:
            raise ValueError("invalid moment")
        if p["topic"] not in TOPICS or p["before"] not in EMOTIONS or p["after"] not in EMOTIONS:
            raise ValueError("invalid heart category")
        title=o.clean(p["title"],5,100);evidence=o.clean(p["evidence"],8,240)
        if evidence not in story:raise ValueError("ungrounded heart moment")
        effect=o.clean(p["effect"],0,180)
        # Consequence is a source excerpt, not a model's invented event.
        if effect and effect not in story:raise ValueError("ungrounded heart consequence")
        cause=p["cause"]
        if cause is not None and (type(cause) is not int or not chapter_key(db,cause)):raise ValueError("unknown heart cause")
        t=p["thread"]
        if t is not None:
            if not isinstance(t,dict) or set(t)!={"key","action","title"} or not isinstance(t["key"],str) or not re.fullmatch(r"[a-z0-9-]{2,40}",t["key"]):
                raise ValueError("invalid relationship thread")
            key=t["key"];action=t["action"]
            if action=="open" and key not in known:pass
            elif action=="resolve" and key in known and known[key]["closed"] is None:pass
            else:raise ValueError("invalid thread transition")
            t={"key":key,"action":action,"title":o.clean(t["title"],5,100)}
        result.append({"topic":p["topic"],"title":title,"evidence":evidence,"before":p["before"],"after":p["after"],"cause":cause,"effect":effect,"thread":t})
    return {"moments":result}

def save(db,did,base,raw,arc):
    data=validate(db,base["story"],raw,arc)
    write(db,did,data)

def write(db,did,data):
    payload=o.dump(data)
    h=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()[0]
    db.execute("INSERT OR REPLACE INTO heart_drafts VALUES(?,?,?,?,?)",(did,payload,o.digest(payload),h,VERSION))

def variant_payload(db,did,base,option):
    if read(db,did) is None:return None
    row=db.execute("SELECT payload,checksum FROM heart_original WHERE draft_id=?",(did,)).fetchone()
    if option==1 and row and o.digest(row[0])!=row[1]:raise ValueError("damaged original moment")
    arc=db.execute("SELECT arc FROM saga_arcs WHERE draft_id=?",(did,)).fetchone()[0]
    return validate(db,base["story"],json.loads(row[0]) if option==1 and row else None,arc)

def remember_original(db,did):
    data=read(db,did)
    if data is not None:
        raw=o.dump(data);db.execute("INSERT OR IGNORE INTO heart_original VALUES(?,?,?)",(did,raw,o.digest(raw)))

def timeline(db,topic=None,limit=30):
    rows=[p for p in published(db) if topic is None or p["topic"]==topic][-limit:]
    return "Художественная история отношений (не реальные воспоминания):\n\n"+"\n\n".join(
        f"Глава {p['chapter']}. {p['title']}\n{p['before']} → {p['after']}\n«{p['evidence']}»"+("\nПоследствие: "+p["effect"] if p["effect"] else "") for p in rows) if rows else "Нет опубликованных моментов."

def thread_text(db):
    return "Художественные сюжетные линии:\n"+"\n".join(f"{v['title']} — глава {v['opened']}; "+(f"завершена в главе {v['closed']}" if v["closed"] else "открыта") for v in threads(db).values()) if threads(db) else "Новых незавершённых романтических линий пока нет."

def graph(db):
    nodes=[]; edges=[]; seen=set()
    def node(key,label,kind,topic,slot=None):
        if key in seen:return
        seen.add(key)
        if slot is None:
            row=db.execute("SELECT slot FROM heart_slots WHERE key=?",(key,)).fetchone()
            if row is None:
                db.execute("INSERT OR IGNORE INTO heart_slots(key,topic,slot) SELECT ?,?,COALESCE(MAX(slot),-1)+1 FROM heart_slots WHERE topic=?",(key,topic,topic))
                row=db.execute("SELECT slot FROM heart_slots WHERE key=?",(key,)).fetchone()
            slot=row[0]
        nodes.append({"key":key,"group":4,"kind":kind,"content":label,"created":"","order":0,"heart_topic":topic,"heart_slot":slot})
    node("heart:root","История любви (художественная)","heart_root","root",-1)
    edges.append({"a":"arc:love","b":"heart:root","kind":"heart_root"})
    all_rows=list(published(db))
    counts=Counter(p["topic"] for p in all_rows)
    for topic in TOPICS:
        key="heart:topic:"+topic;node(key,LABELS[topic],"heart_topic",topic,-1)
        edges.append({"a":"heart:root","b":key,"kind":"heart_branch","shared":counts[topic]})
    # Retain original moments and a bounded recent window of new detailed stars.
    rows=[p for p in all_rows if p["source"]=="canon"]+[p for p in all_rows if p["source"]=="approved"][-48:]
    previous={}
    for p in rows:
        key=p["key"];topic=p["topic"]
        node(key,p["title"]+" · гл. "+str(p["chapter"]),"heart_moment",topic)
        edges.append({"a":"heart:topic:"+topic,"b":key,"kind":"heart_moment"})
        chapter=chapter_key(db,p["chapter"])
        if chapter:edges.append({"a":chapter,"b":key,"kind":"heart_source"})
        if p["cause"] is not None:
            cause=chapter_key(db,p["cause"])
            if cause:edges.append({"a":cause,"b":key,"kind":"heart_cause"})
        if topic in previous:edges.append({"a":previous[topic],"b":key,"kind":"heart_related"})
        previous[topic]=key
        for kind,emotion in (("heart_before",p["before"]),("heart_after",p["after"])):
            feeling="heart:feeling:"+o.digest(emotion)[:16]
            node(feeling,"Чувство героини: "+emotion,"heart_moment","tenderness")
            edges.append({"a":key,"b":feeling,"kind":kind})
        if p["effect"]:
            consequence=key+":effect"
            node(consequence,"Последствие: "+p["effect"],"heart_moment",topic)
            edges.append({"a":key,"b":consequence,"kind":"heart_effect"})
    for n,did in db.execute("SELECT number,draft_id FROM omega_index WHERE draft_id IS NOT NULL ORDER BY number DESC LIMIT 12"):
        w=g.world(db,did);m=o.metadata(db,did)
        for kind,body in (("letter",w.get("letter") if w else None),("diary",m["data"].get("diary") if m else None)):
            if body:
                key=f"heart:{kind}:{did}";node(key,("Письмо" if kind=="letter" else "Дневник")+" · гл. "+str(n),"heart_moment","letters")
                edges.extend(({"a":"heart:topic:letters","b":key,"kind":"heart_moment"},{"a":f"c:{did}","b":key,"kind":"heart_source"}))
    for k,v in list(threads(db).items())[-24:]:
        key="heart:thread:"+k;node(key,v["title"]+(" (завершена)" if v["closed"] else " (открыта)"),"heart_moment","memory")
        edges.append({"a":"heart:topic:memory","b":key,"kind":"heart_moment"})
        for n in (v["opened"],v["closed"]):
            c=chapter_key(db,n) if n else None
            if c:edges.append({"a":c,"b":key,"kind":"heart_thread"})
    return nodes,edges


def audit(db):
    issues=[]
    for did,n in db.execute("SELECT h.draft_id,a.number FROM heart_drafts h JOIN saga_arcs a ON a.draft_id=h.draft_id JOIN chronicle_drafts d ON d.id=h.draft_id WHERE d.status=\'approved\'"):
        try: read(db,did)
        except (ValueError,TypeError): issues.append(f"Глава {n}: повреждены сведения о художественных отношениях")
    return issues
