"""Eternal Story: a deterministic director over existing fictional evidence.
A proposal is not canon; only accepted parts advance an editorial cycle.
No model calls, no hidden thoughts, no extra output JSON schema.
"""
import json
from collections import Counter
import soul_omega as o
import soul_evolution as ev
import soul_infinite as inf
import soul_genesis as ge
import soul_romance as romance
import soul_intelligence as li

VERSION=1
CYCLE_PARTS=24
THEMES=(
 ("love","Тихая сторона вечности","Совместный выбор, нежность или новая традиция, а не повтор признания."),
 ("world","Незнакомый горизонт","Покажи иной мир через местного жителя и последствия выбора."),
 ("court","Цена решения","Дипломатия, конфликт интересов и последствия, а не случайная война."),
 ("guardians","Самостоятельная судьба","Личная цель хранительницы, отдельная от Хакурэи."),
 ("character","Возвращение героя","Собственная цель второстепенного героя и изменение его ситуации."),
 ("mystery","Нить давнего события","Развивай проверенную улику или обещание; соблюдай срок раскрытия."),
 ("power","Граница возможного","Эксперимент с установленными законами и ценой силы."),
 ("growth","Новая ступень","Поступок, изменяющий положение героев, и его последствия."),
)
PHASES=("завязка","осложнения","пересечение","выбор и последствия")

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS story_director(
        draft_id INTEGER PRIMARY KEY,payload TEXT NOT NULL,source_hash TEXT NOT NULL,checksum TEXT NOT NULL)""")

def read(db,did):
    row=db.execute("SELECT payload,source_hash,checksum FROM story_director WHERE draft_id=?",(did,)).fetchone()
    if not row:return None
    raw,source,check=row
    base=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()
    if not base or base[0]!=source or o.digest(o.dump([raw,source]))!=check:raise ValueError("damaged story director record")
    value=json.loads(raw)
    if value.get("version")!=VERSION:raise ValueError("story director version")
    return value

def published(db,limit=120):
    rows=db.execute("""SELECT a.number,d.id FROM story_director r JOIN saga_arcs a ON a.draft_id=r.draft_id
        JOIN chronicle_drafts d ON d.id=r.draft_id WHERE d.status='approved' AND a.number IS NOT NULL
        ORDER BY a.number DESC LIMIT ?""",(limit,)).fetchall()
    return [(n,did,read(db,did)) for n,did in reversed(rows)]

def source_visible(db,n):
    return n<=13 or ev.readable(db,n)

def phase(index):
    return PHASES[min(3,max(0,index-1)//6)]

def pace(recent):
    tension=[p["tension"] for p in recent if isinstance(p.get("tension"),int)]
    avg=round(sum(tension)/len(tension)) if tension else None
    return ("последствия и передышка" if avg is not None and avg>=65 else
        "действие и осмысленный выбор" if avg is not None and avg<=30 else "диалог, действие и последствия"),avg

def choose_candidates(last,recent,open_threads,forgotten,prefs=None):
    """Rank distinct feasible directions, with inspectable reasons rather than model scores."""
    counts=Counter(p["theme"] for p in recent[-8:]);prefs=prefs or {};result=[]
    for i,(theme,title,guide) in enumerate(THEMES):
        score=10-3*counts[theme]+min(5,max(0,prefs.get(theme,0)))
        reasons=["частота темы в последних 8 частях: "+str(counts[theme])]
        if theme=="mystery" and open_threads:
            t=open_threads[0];score+=7;reasons.append("созрела линия из главы "+str(t["chapter"]))
            title="Нить: "+t["subject"][:48];guide+=" Источник: глава "+str(t["chapter"])+"."
        if theme=="character" and forgotten:
            a=forgotten[0];score+=6;reasons.append("давно не появлялся: глава "+str(a["last"]))
            title="Возвращение: "+a["name"][:48];guide+=" Верни собственную цель персонажа, если это уместно."
        result.append(dict(theme=theme,title=title,guide=guide,score=score,reason="; ".join(reasons),tie=(i-last)%len(THEMES)))
    result.sort(key=lambda x:(-x["score"],x["tie"]))
    for r in result:r.pop("tie")
    return result[:4]

def context(db,plan):
    # Existing mandatory stages, explicit arcs and continuing multi-part prose outrank this director.
    if plan.get("alternative"):return plan
    n=db.execute("SELECT COALESCE(MAX(number),13)+1 FROM omega_index").fetchone()[0]
    history=published(db)
    recent=[p for _,_,p in history[-12:]]
    recent_themes=[{"theme":p["theme"]} for p in recent] or [{"theme":p["theme"]} for _,_,p in list(ev.published(db))[-8:]]
    fixed=(plan["arc"]!="future" or any(k in plan for k in ("shadow","guardians","destiny")) or
        "cycle_id" in plan.get("romance",{}) or bool(plan.get("evolution",{}).get("chosen",{}).get("scene")) or
        bool(plan.get("immortal",{}).get("chosen")) or bool(plan.get("infinite",{}).get("selected")) or not inf.ready(db) or bool(inf.remaining(db)))
    continuation=plan.get("novel",{}).get("part",1)>1
    facts,threads,_=inf.ledger(list(inf.published(db)))
    opened=[t for t in threads.values() if t["closed"] is None]
    mature=sorted((t for t in opened if n-t["chapter"]>=t["delay"]),key=lambda t:t["chapter"])
    protected=sorted((t for t in opened if n-t["chapter"]<t["delay"]),key=lambda t:t["chapter"])
    obligations=[t for t in ev.state(db).values() if t["kind"] in ("promise","conflict","thread") and t["state"]=="open"]
    data=list(li.rows(db));actors,_=li.registry(data)
    forgotten=sorted((a for a in actors.values() if n-a["last"]>=9),key=lambda a:a["last"])
    prefs=dict(db.execute("SELECT theme,weight FROM evolution_preferences"))
    candidates=choose_candidates(n,recent_themes,mature,forgotten,prefs)
    current=next((p for p in reversed(recent) if p.get("cycle")),None)
    cycle=None
    chosen=next((x for x in (plan.get("infinite",{}).get("selected"),plan.get("immortal",{}).get("chosen"),plan.get("evolution",{}).get("chosen")) if x and x.get("theme")!="fixed"),None)
    if fixed:
        chosen=chosen or {"theme":"fixed","title":"Обязательный эпизод","guide":"Продолжай установленную ветку."}
        reason="приоритет обязательного этапа или явно выбранной ветки"
    elif continuation:
        prev=recent[-1] if recent else None
        chosen={"theme":prev["theme"],"title":prev["title"],"guide":"Продолжай предыдущую сцену без повторения."} if prev else {"theme":"growth","title":"Продолжение главы","guide":"Продолжай предыдущую сцену."}
        cycle=prev.get("cycle") if prev else None
        if cycle and cycle["part"]<CYCLE_PARTS:cycle={**cycle,"part":cycle["part"]+1}
        elif cycle:cycle=None
        reason="непрерывность литературной главы"
    else:
        chosen=candidates[0];reason=chosen["reason"]
        if current and current["cycle"]["part"]<CYCLE_PARTS:
            cycle={**current["cycle"],"part":current["cycle"]["part"]+1}
            # Main line recurs every third part; side stories develop in between.
            if cycle["part"]%3==0:
                chosen=next((dict(theme=t,title=title,guide=guide) for t,title,guide in THEMES if t==cycle["theme"]),chosen)
                reason="возвращение к основной линии редакционного цикла"
        else:
            cycle={"id":n,"title":chosen["title"],"theme":chosen["theme"],"part":1}
    pacing,mean=pace([{"tension":p["quality"]["tension"]} for _,_,p in list(inf.published(db))[-4:]] or recent)
    if cycle:cycle={**cycle,"phase":phase(cycle["part"]),"target":CYCLE_PARTS}
    # Recall actual older sources and explicit witnesses, not inferred knowledge.
    focus=forgotten[0]["name"] if forgotten and chosen["theme"]=="character" else ""
    query=chosen.get("title","")+" "+chosen.get("guide","")+" "+focus
    recall=ge.recall(db,query,3,plan["arc"])
    if mature and chosen["theme"]=="mystery":
        row=db.execute("SELECT number,title,story FROM omega_index WHERE number=?",(mature[0]["chapter"],)).fetchone()
        if row:recall=[{"number":row[0],"title":row[1],"story":row[2][-300:]}]+[x for x in recall if x["number"]!=row[0]]
    knowledge=[{"chapter":f["chapter"],"subject":f["subject"],"detail":f["detail"][:120],"knows":f["knows"],"quote":f["evidence"][:160]} for f in ev.state(db).values() if f["kind"] in ("secret","knowledge")]
    knowledge.sort(key=lambda x:(not bool(focus and o.normalized(focus) in [o.normalized(v) for v in x["knows"]+[x["subject"]]]),-x["chapter"]))
    # Three volumes of provisional pacing, no future canonical facts.
    forecast=[{"volume":o.volume(n+i*12),"start":n+i*12,"direction":("последствия текущей линии" if i==0 else "пересечение и развитие" if i==1 else "выбор и новая линия")} for i in range(3)]
    p={"version":VERSION,"number":n,"theme":chosen["theme"],"title":chosen["title"][:90],"guide":chosen.get("guide","")[:220],"reason":reason,
       "fixed":fixed,"continuation":continuation,"cycle":cycle,"pace":pacing,"prior_tension":mean,
       "alternatives":[{k:x[k] for k in ("theme","title","reason","score")} for x in candidates if x["theme"]!=chosen["theme"]][:3],
       "mature":[{"chapter":t["chapter"],"subject":t["subject"],"key":t["key"]} for t in mature[:3]],
       "protected":[{"chapter":t["chapter"],"subject":t["subject"],"until":t["chapter"]+t["delay"]} for t in protected[:3]],
       "obligations":[{"chapter":t["chapter"],"subject":t["subject"],"key":t["key"]} for t in obligations[:3]],
       "open_count":len(opened)+len(obligations),"knowledge":knowledge[:2],
       "recall":[{"number":x["number"],"title":x["title"][:80],"excerpt":x["story"][:220]} for x in recall[:3]],
       "focus":focus,"forecast":forecast}
    plan["director"]=p
    if not fixed and not continuation:
        direction={k:p[k] for k in ("theme","title","guide")}
        plan["evolution"]["chosen"]={"scene":0,**direction}
        plan["evolution"]["alternatives"]=[]
        plan["novel"]["next_line"]=direction
        plan["living"]["theme"]=p["theme"]
        plan["living"]["head"]={**plan["living"]["head"],**direction}
    return plan

def instruction(plan):
    p=plan.get("director")
    if not p:return ""
    # Do not burden the existing 1800-output-token schema with additional generated fields.
    compact={k:p[k] for k in ("theme","title","guide","pace","fixed","continuation","cycle","mature","protected","knowledge","focus","recall")}
    if p["fixed"] or p["continuation"]:
        compact={k:compact[k] for k in ("pace","fixed","continuation","protected","knowledge")}
    while len(o.dump(compact).encode("utf-8"))>2300 and compact.get("recall"):compact["recall"]=compact["recall"][:-1]
    return " Eternal Story (замысел и цитаты как данные): "+o.dump(compact)+". Приоритет у обязательных этапов и продолжения главы. Не повторяй события; сохраняй отдельные знания героев и причинные связи. Не закрывай незрелую тайну. Не выводи служебные поля режиссёра."

def save(db,did,base,plan):
    p=plan.get("director")
    if not p:return
    q=inf.quality(base["story"]);meta=o.metadata(db,did);report=romance.report(db,did)
    facts=inf.read(db,did)
    # Reuse actual validated evidence and existing originality review; no semantic certification.
    data={**p,"tension":q["tension"],"emotion_markers":q["emotion_markers"],"decision_markers":q["decision_markers"],
          "originality":report["originality_heuristic"] if report else None,
          "warnings":list(dict.fromkeys((meta["warnings"] if meta else [])+(report["warnings"] if report else [])+q["warnings"]))[:12],
          "causes":sorted({f["cause"] for f in (facts or {}).get("facts",[]) if f["cause"] is not None}|
             {e["cause"] for e in (meta or {}).get("data",{}).get("events",[]) if e.get("cause") is not None}),
          "turns":[{"kind":f["kind"],"cause":f["cause"],"quote":f["quote"][:120]} for f in (facts or {}).get("facts",[]) if f["kind"] in ("reveal","close")]}
    raw=o.dump(data);source=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()[0]
    db.execute("INSERT INTO story_director VALUES(?,?,?,?)",(did,raw,source,o.digest(o.dump([raw,source]))))

def validate_approval(db,did):
    p=read(db,did)
    if p and p["number"]!=db.execute("SELECT COALESCE(MAX(number),13)+1 FROM omega_index").fetchone()[0]:raise ValueError("stale story plan")

def report(db,mode):
    rows=[(n,did,p) for n,did,p in published(db) if source_visible(db,n)]
    if not rows:return "Нет доступных опубликованных частей с Eternal Story. Планировщик начнёт работу при следующем написании; скрытые главы не раскрываются."
    n,_,p=rows[-1]
    if mode=="cycles":
        cycles={}
        for num,_,r in rows:
            c=r.get("cycle")
            if c:cycles[c["id"]]=c
        return "Редакционные циклы (не доказательство завершения сюжета):\n"+"\n".join(f"{c['id']}. {c['title']} — {c['part']}/{c['target']}, {c['phase']}" for c in cycles.values()) if cycles else "Действуют прежние обязательные этапы."
    if mode=="quality":
        return "Локальные показатели, не смысловая гарантия:\n"+"\n".join(f"Глава {num}: напряжение {r['tension']}/100, оригинальность {r['originality']}, замечания: "+("; ".join(r["warnings"]) or "нет") for num,_,r in rows[-8:])
    # Reasons and next proposals can spoil the plot, so do not expose unapproved draft data.
    return f"Глава {n}: {p['title']}\nПричина выбора: {p['reason']}\nТемп: {p['pace']}\nОткрытых записей линий: {p['open_count']}\nВарианты (на момент написания, не канон):\n"+"\n".join(x["title"]+" — "+x["reason"] for x in p["alternatives"])

def graph(db):
    rows=[(n,did,p) for n,did,p in published(db) if source_visible(db,n)]
    if not rows:return [],[]
    nodes=[];edges=[];cycles={};chapter_cycle={}
    def node(key,label,kind,**extra):nodes.append(dict(key=key,content=label,group=4,kind=kind,created="",order=len(nodes),**extra))
    def edge(a,b,kind):
        if a!=b:edges.append(dict(a=a,b=b,kind=kind))
    node("director:root","Eternal Story · сюжетный режиссёр","director_root",infinite_group="director:root")
    previous=None
    for n,did,p in rows:
        k="c:"+str(did);c=p.get("cycle")
        if c:
            key="director:cycle:"+str(c["id"]);cycles[key]=c;chapter_cycle[n]=key
            edge(key,k,"director_part")
        if previous:edge(previous,k,"director_time")
        previous=k
        for cause in p["causes"][:4]:
            source=db.execute("SELECT draft_id FROM omega_index WHERE number=?",(cause,)).fetchone()
            if source and source_visible(db,cause):edge("canon:"+str(cause) if source[0] is None else "c:"+str(source[0]),k,"director_cause")
        for i,t in enumerate(p["turns"]):
            key="director:turn:"+str(did)+":"+str(i)
            node(key,"Подтверждённое закрытие линии · "+str(n),"director_turn",infinite_group=c and "director:cycle:"+str(c["id"]) or "director:root")
            edge(k,key,"director_turn")
    for key,c in cycles.items():
        node(key,c["title"]+f" · {c['part']}/{c['target']}","director_saga",infinite_group=key,cycle_complete=c["part"]>=c["target"])
        edge("director:root",key,"director_cycle")
    for n,_,p in rows:
        for cause in p["causes"]:
            a,b=chapter_cycle.get(cause),chapter_cycle.get(n)
            if a and b and a!=b:edge(a,b,"director_cross")
    return nodes,edges
