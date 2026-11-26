"""Local literary development. All material belongs to a fictional universe."""
import json
import math
import re
from collections import Counter
import soul_omega as o
import soul_lore

RULES=(
 ("origin",1,"Хакурэя возникла до богов; прародительница кицунэ."),
 ("nine",2,"Девять хвостов и девять небес; число и исходные способности не изменяются."),
 ("touch",5,"До встречи с героем прямое прикосновение опасно для живых существ."),
 ("immunity",5,"Герой невосприимчив к её энергии от рождения; не приобретённое заклинание."),
 ("warmth",6,"Первые объятия и человеческое тепло открываются после встречи."),
 ("choice",11,"Любовь и добровольный выбор не лишают императрицу достоинства и свободы."),
 ("return",10,"Полная сила возвращается после признания; первоначальный канон неизменен.")
)
POWERS=("Холод","Жизнь и смерть","Пространство","Время","Магия","Знания","Души","Судьба","Законы реальности")
CONCEPTS={
 "тепло":("прикоснов","объят","нежност","ладон","тепл"),
 "любовь":("любов","любим","довер","нежност","поцел"),
 "защита":("защит","невосприим","барьер","энерги"),
 "прошлое":("прошл","древн","эпох","войн","одиночеств"),
 "небеса":("небес","царств","дворец","хакусэйден"),
 "магия":("маг","сил","хвост","энерги"),
}
BEATS={
 "past":("Первая небесная династия","Цена победы","Наследие кицунэ","Совет древних правителей","Законы магии","Забытая клятва","Пророчество","Одиночество на троне"),
 "meeting":("Её взгляд на спасение","Непостижимое прикосновение","Первые минуты дома","Испытание силы","Первое тепло","Разговор о страхе","Доверие без приказа","Два взгляда на встречу"),
 "love":("Письмо императрицы","Человеческое утро","Разговор о прошлом","Спор и взаимное уважение","Воспоминание о первом объятии","Скрытая тревога","Два взгляда на приключение","Нежность без утраты величия"),
 "future":("Возвращение в небесный дворец","Реакция совета","Путешествие по царству","Тайна защиты","Последствия прежнего решения","Пророчество в архиве","Переплетение судеб","Совместное открытие"),
}
VERSION=1

def init(db):
    db.execute("CREATE TABLE IF NOT EXISTS genesis_docs(number INTEGER PRIMARY KEY, fingerprint TEXT NOT NULL, length INTEGER NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS genesis_terms(term TEXT NOT NULL, number INTEGER NOT NULL, weight INTEGER NOT NULL, PRIMARY KEY(term,number))")
    db.execute("CREATE INDEX IF NOT EXISTS genesis_terms_number ON genesis_terms(number)")
    db.execute("CREATE TABLE IF NOT EXISTS genesis_notes(id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL, checksum TEXT NOT NULL, updated TEXT DEFAULT CURRENT_TIMESTAMP)")
    db.execute("CREATE TABLE IF NOT EXISTS genesis_variants(draft_id INTEGER NOT NULL, option INTEGER NOT NULL, payload TEXT NOT NULL, checksum TEXT NOT NULL, score INTEGER NOT NULL, PRIMARY KEY(draft_id,option))")
    db.execute("CREATE TABLE IF NOT EXISTS genesis_edits(id INTEGER PRIMARY KEY, draft_id INTEGER NOT NULL, before_hash TEXT NOT NULL, after_hash TEXT NOT NULL, chosen INTEGER NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP)")
    db.execute("CREATE TABLE IF NOT EXISTS genesis_world(draft_id INTEGER PRIMARY KEY, payload TEXT NOT NULL, checksum TEXT NOT NULL)")
    # Index is derived only from approved chapter archive. Incremental on content checksum.
    if db.execute("SELECT 1 FROM genesis_docs WHERE number NOT IN (SELECT number FROM omega_index) LIMIT 1").fetchone():
        db.execute("DELETE FROM genesis_terms WHERE number NOT IN (SELECT number FROM omega_index)")
        db.execute("DELETE FROM genesis_docs WHERE number NOT IN (SELECT number FROM omega_index)")
    for n,title,story,check in db.execute("""SELECT i.number,i.title,i.story,i.checksum FROM omega_index i
        LEFT JOIN genesis_docs g ON g.number=i.number AND g.fingerprint=i.checksum WHERE g.number IS NULL""").fetchall():
        words=Counter(o.WORD.findall(o.normalized(story)))
        words.update({k:3*v for k,v in Counter(o.WORD.findall(o.normalized(title))).items()})
        for k in o.STOP: words.pop(k,None)
        db.execute("DELETE FROM genesis_terms WHERE number=?",(n,))
        db.executemany("INSERT INTO genesis_terms VALUES(?,?,?)",[(t,n,min(100,w)) for t,w in words.items()])
        db.execute("INSERT OR REPLACE INTO genesis_docs VALUES(?,?,?)",(n,check,sum(words.values())))

def recall(db,q,limit=8,arc=None):
    terms=sorted(o.tokens(q),key=lambda x:(-len(x),x))[:12]
    if not terms:return []
    prefixes=set(t[:max(4,len(t)-2)] for t in terms if len(t)>=4)
    for k,related in CONCEPTS.items():
        if any(t.startswith(k[:4]) for t in terms): prefixes.update(related)
    total=max(1,db.execute("SELECT COUNT(*) FROM genesis_docs").fetchone()[0])
    scores=Counter()
    for p in sorted(prefixes)[:32]:
        # Range scan on indexed term; never interpolate SQL.
        hits=db.execute("SELECT number,SUM(weight) FROM genesis_terms WHERE term>=? AND term<? GROUP BY number",(p,p+"\U0010ffff")).fetchall()
        idf=math.log(1+(total-len(hits)+.5)/(len(hits)+.5))
        for n,w in hits:scores[n]+=idf*w/(w+1.5)
    for t in terms:
        hits=db.execute("SELECT number,weight FROM genesis_terms WHERE term=?",(t,)).fetchall()
        idf=math.log(1+(total-len(hits)+.5)/(len(hits)+.5))
        for n,w in hits:scores[n]+=2*idf*w/(w+1.5)
    result=[]
    for n,score in sorted(scores.items(),key=lambda x:(-x[1],-x[0])):
        row=db.execute("SELECT arc,title,story FROM omega_index WHERE number=?",(n,)).fetchone()
        if not row or (arc and row[0]!=arc):continue
        a,title,story=row
        lines=re.split(r"(?<=[.!?])\s+|\n+",story)
        ranked=sorted(enumerate(lines),key=lambda v:(-sum(p in o.normalized(v[1]) for p in prefixes),v[0]))[:4]
        excerpt=" ".join(line for _,line in sorted(ranked))[:1200]
        result.append({"number":n,"arc":a,"title":title,"story":excerpt,"score":round(score,3)})
        if len(result)>=limit:break
    return result

def roadmap(db,arc=None,limit=100):
    counts=dict(db.execute("SELECT arc,COUNT(*) FROM omega_index WHERE number>13 GROUP BY arc"))
    start=db.execute("SELECT COALESCE(MAX(number),13) FROM omega_index").fetchone()[0]
    out=[]
    for offset in range(min(100,max(0,limit))):
        a=arc or min(o.ARCS,key=lambda k:counts.get(k,0))
        i=counts.get(a,0)
        n=start+offset+1
        out.append({"number":n,"book":o.volume(n),"arc":a,"cycle":i//8+1,"beat":BEATS[a][i%8],"realm":(i//2)%9+1 if a in ("past","future") else None,
                    "view":"Хакурэя" if i%2==0 else "герой или внешний рассказчик"})
        counts[a]=i+1
    return out

def world(db,did):
    row=db.execute("SELECT payload,checksum FROM genesis_world WHERE draft_id=?",(did,)).fetchone()
    if not row or o.digest(row[0])!=row[1]:return None
    try:return json.loads(row[0])
    except (ValueError,TypeError):return None

def state(db):
    actors={}; places={}; consequences=[]
    for n,did in db.execute("SELECT number,draft_id FROM omega_index WHERE draft_id IS NOT NULL ORDER BY number"):
        m=o.metadata(db,did)
        if m:
            for event in m["data"]["events"]:
                for name in event["characters"]:
                    key=o.normalized(name)
                    item=actors.setdefault(key,{"name":name,"first":n,"last":n,"count":0})
                    item["last"]=n;item["count"]+=1
                if event["cause"] is not None:consequences.append({"from":event["cause"],"to":n,"event":event["summary"]})
        w=world(db,did)
        if w:
            for x in w.get("characters",[]):
                key=o.normalized(x["name"]); item=actors.setdefault(key,{"name":x["name"],"first":n,"last":n,"count":0})
                item["last"]=n;item["portrait"]=x["portrait"];item["motive"]=x["motive"];item["lineage"]=x["lineage"];item["source"]=n
            for x in w["places"]:
                places.setdefault(o.normalized(x["name"]),{"name":x["name"],"realm":x["realm"],"chapter":n,"description":x["description"]})
    last=db.execute("SELECT COALESCE(MAX(number),13) FROM omega_index").fetchone()[0]
    forgotten=sorted((a for a in actors.values() if last-a["last"]>=8),key=lambda a:a["last"])
    questions=o.mysteries(db)
    return {"actors":list(actors.values()),"places":list(places.values()),"consequences":consequences,"forgotten":forgotten,
            "open":[{"key":k,**v} for k,v in questions.items() if v["closed"] is None]}

def consolidate(db):
    data=state(db)
    summary={"actors":len(data["actors"]),"places":len(data["places"]),"consequences":len(data["consequences"]),
             "forgotten":data["forgotten"][:12],"open":data["open"][:12],"plan":roadmap(db,limit=12)}
    raw=o.dump(summary)
    db.execute("INSERT INTO genesis_notes(id,payload,checksum) VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,checksum=excluded.checksum,updated=CURRENT_TIMESTAMP WHERE genesis_notes.checksum!=excluded.checksum",(raw,o.digest(raw)))
    return summary

def enrich(db,plan):
    next_beat=roadmap(db,plan["arc"],1)[0]
    summary=consolidate(db)
    plan["genesis"]={"next":next_beat,"recall":recall(db,next_beat["beat"]+" "+plan["guide"],4),
        "forgotten":summary["forgotten"][:3],"open":summary["open"][:4],"rules":[r[2] for r in RULES]}
    return plan

def instruction(plan):
    if "genesis" not in plan:return ""
    g=plan["genesis"]
    return (" Дополнительный литературный план (не канон): "+o.dump(g)+
        " Выстрой выбор героя, его последствия, мотивы и предысторию. Сохрани стиль, самостоятельность и взаимность. "
        " Сначала продумай и отредактируй текст внутри одного ответа. Не выдавай ход рассуждений. "
        " При возможности добавь необязательный объект world с полями places:[{name,realm,description,evidence}], letter, perspective. "
        " realm — число 1–9 или null для человеческого мира; evidence — точная цитата из story; letter — художественное письмо до 500 символов, perspective — альтернативный взгляд до 500 символов. До двух мест. Допустимо поле characters: [{name,portrait,motive,lineage,evidence}], максимум 2; lineage — только родство, описанное в тексте или пустая строка. "
        " Никаких сведений о реальных людях; это художественный материал. "+ (" По запросу альтернативы: добавь необязательное поле alternative — второй самостоятельный вариант с title, story (100–1500 символов), tags, emotions, traits; не копируй основную сцену. Оба варианта краткие, в пределах общего лимита ответа." if plan.get("alternative") else ""))

def validate_world(db,story,raw):
    if raw is None:return {"places":[],"letter":"","perspective":"","characters":[]}
    if not isinstance(raw,dict) or not {"places","letter","perspective"}<=set(raw) or set(raw)-{"places","letter","perspective","characters"}:raise ValueError("invalid world fields")
    places=raw["places"]
    if not isinstance(places,list) or len(places)>2:raise ValueError("invalid places")
    known={o.normalized(p["name"]):p["realm"] for p in state(db)["places"]}
    result={"places":[],"letter":o.clean(raw["letter"],0,500),"perspective":o.clean(raw["perspective"],0,500),"characters":[]}
    for p in places:
        if not isinstance(p,dict) or set(p)!={"name","realm","description","evidence"}:raise ValueError("invalid place")
        name=o.clean(p["name"],2,70); evidence=o.clean(p["evidence"],8,240); realm=p["realm"]
        if realm is not None and (type(realm) is not int or not 1<=realm<=9):raise ValueError("invalid realm")
        if evidence not in story or o.normalized(name) not in o.normalized(evidence):raise ValueError("ungrounded place")
        key=o.normalized(name)
        if key in known and known[key]!=realm:raise ValueError("realm contradiction")
        known[key]=realm
        result["places"].append({"name":name,"realm":realm,"description":o.clean(p["description"],5,250),"evidence":evidence})
    chars=raw.get("characters",[])
    if not isinstance(chars,list) or len(chars)>2:raise ValueError("invalid character portraits")
    for p in chars:
        if not isinstance(p,dict) or set(p)!={"name","portrait","motive","lineage","evidence"}:raise ValueError("invalid character portrait")
        name=o.clean(p["name"],2,60);evidence=o.clean(p["evidence"],8,240)
        if evidence not in story or o.normalized(name) not in o.normalized(evidence):raise ValueError("ungrounded character")
        result["characters"].append({"name":name,"portrait":o.clean(p["portrait"],5,200),"motive":o.clean(p["motive"],0,160),"lineage":o.clean(p["lineage"],0,160),"evidence":evidence})
    return result

def save_world(db,did,story,raw):
    data=validate_world(db,story,raw); payload=o.dump(data)
    db.execute("INSERT OR REPLACE INTO genesis_world VALUES(?,?,?)",(did,payload,o.digest(payload)))

def audit(db):
    import soul_chronicle as c
    issues=[]
    if not c.canon_ok(db):issues.append("Нарушен исходный канон")
    import soul_saga
    for n,title,story in soul_saga.canonical_chapters():
        row=db.execute("SELECT title,story FROM omega_index WHERE number=?",(n,)).fetchone()
        if row!=(title,story):issues.append(f"Канон {n}: несовпадение индекса")
    for did,n,raw,h in db.execute("SELECT d.id,a.number,d.payload,d.checksum FROM chronicle_drafts d JOIN saga_arcs a ON a.draft_id=d.id WHERE d.status='approved'"):
        try:p=c.unpack(raw,h)
        except (ValueError,TypeError):issues.append(f"Глава {n}: повреждён текст");continue
        row=db.execute("SELECT title,story,checksum FROM omega_index WHERE number=?",(n,)).fetchone()
        if not row or row!=(p["title"],p["story"],h):issues.append(f"Глава {n}: несовпадение индекса")
        if db.execute("SELECT 1 FROM omega_meta WHERE draft_id=?",(did,)).fetchone() and not o.metadata(db,did):issues.append(f"Глава {n}: повреждены события")
        if db.execute("SELECT 1 FROM genesis_world WHERE draft_id=?",(did,)).fetchone() and world(db,did) is None:issues.append(f"Глава {n}: повреждены сведения мира")
    return issues

def atlas(db):
    data=state(db)
    lines=["Атлас девяти небес (вымышленный мир). Названия и культура неизвестных царств не считаются каноном до утверждения главы.",
           "Девять сил (не соответствие царствам): "+", ".join(POWERS)]
    for i in range(1,10):
        p=[x for x in data["places"] if x["realm"]==i]
        lines.append(f"Царство {i}: "+("; ".join(f"{x['name']} — {x['description']} (гл. {x['chapter']})" for x in p) if p else "подробности ещё не написаны"))
    return "\n".join(lines)

def read_arc(db,arc,page=1):
    rows=db.execute("SELECT number,title FROM omega_index WHERE arc=? ORDER BY number LIMIT 20 OFFSET ?",(arc,(page-1)*20)).fetchall()
    return o.ERA[arc]+"\n"+"\n".join(f"{n}. {t}" for n,t in rows)+"\nЧитать полный текст: летопись: читать НОМЕР." if rows else "Нет глав на этой странице."

def extras(db,n,kind):
    row=db.execute("SELECT draft_id FROM omega_index WHERE number=?",(n,)).fetchone()
    w=world(db,row[0]) if row and row[0] is not None else None
    return "Художественный материал, глава "+str(n)+"\n\n"+w[kind] if w and w[kind] else "Этот дополнительный материал ещё не создан."

def graph(db):
    nodes=[];edges=[]
    def add(k,label,kind):
        nodes.append({"key":k,"group":4,"content":label,"kind":kind,"created":"","order":len(nodes)})
    for k,n,label in RULES:
        key="law:"+k;add(key,label,"law");edges.append({"a":f"canon:{n}","b":key,"kind":"world_law"})
    for i in range(1,10):
        key=f"realm:{i}";add(key,f"Небесное царство {i}","realm");edges.append({"a":"canon:2","b":key,"kind":"world_realm"})
    # Each recent book/epoch intersection has its own physical constellation hub.
    segments={}
    for n,arc,did in db.execute("SELECT number,arc,draft_id FROM omega_index ORDER BY number DESC LIMIT 145"):
        v=o.volume(n); key=f"segment:{arc}:{v}"
        if key not in segments and len(segments)<32:
            add(key,f"Том {v} · {o.ERA[arc]}","book_segment")
            segments[key]=True;edges.append({"a":"era:"+arc,"b":key,"kind":"book"})
        if key in segments:
            edges.append({"a":key,"b":f"c:{did}" if did is not None else f"canon:{n}","kind":"book_chapter"})
    for p in state(db)["places"][-30:]:
        key="place:"+o.digest(o.normalized(p["name"]))[:20];add(key,p["name"],"place")
        row=db.execute("SELECT draft_id FROM omega_index WHERE number=?",(p["chapter"],)).fetchone()
        if row and row[0] is not None:edges.append({"a":f"c:{row[0]}","b":key,"kind":"world_place"})
        if p["realm"] is not None:edges.append({"a":f"realm:{p['realm']}","b":key,"kind":"world_place"})
    return nodes,edges


def save_variants(db,did,base,lit,world_data,alt,plan):
    """Keep alternative draft as a separate, validated proposal in the same paid call."""
    if alt is None or not plan.get("alternative"):return
    import soul_chronicle as c
    try:
        other=c.validate(alt)
        if len(other["story"])>1500 or o.normalized(other["story"])==o.normalized(base["story"]):return
        score,_=o.review(db,other,{"events":[]})
    except (ValueError,TypeError):return
    m=o.metadata(db,did)
    for i,item,l,w,sc in ((1,base,lit,world_data,m["score"] if m else 0),(2,other,None,None,score)):
        raw=o.dump({"base":item,"literary":l,"world":w,"strategy":plan.get("strategy","causality")})
        db.execute("INSERT INTO genesis_variants VALUES(?,?,?,?,?)",(did,i,raw,o.digest(raw),sc))

def variants(db):
    pending=db.execute("SELECT id FROM chronicle_drafts WHERE status='pending'").fetchone()
    if not pending:return "Нет ожидающего черновика."
    lines=[]
    for option,raw,h,score in db.execute("SELECT option,payload,checksum,score FROM genesis_variants WHERE draft_id=? ORDER BY option",(pending[0],)):
        if o.digest(raw)!=h:continue
        p=json.loads(raw)["base"]
        lines.append(f"Вариант {option} — {score}/100 (эвристика)\n{p['title']}\n\n{p['story']}")
    return "\n\n".join(lines)+"\n\nВыбор: летопись: вариант 1 или 2. Затем утвердите черновик." if lines else "Альтернативный вариант не сохранён. Для следующей попытки: летопись: создать варианты."

def select_variant(db,option):
    import soul_chronicle as c
    row=db.execute("SELECT id,checksum FROM chronicle_drafts WHERE status='pending'").fetchone()
    if not row or not c.canon_ok(db):return False
    did,before=row
    if db.execute("SELECT 1 FROM shadow_drafts WHERE draft_id=?",(did,)).fetchone() or db.execute("SELECT 1 FROM guardian_drafts WHERE draft_id=?",(did,)).fetchone() or db.execute("SELECT 1 FROM destiny_drafts WHERE draft_id=?",(did,)).fetchone() or db.execute("SELECT 1 FROM living_records WHERE draft_id=?",(did,)).fetchone() or db.execute("SELECT 1 FROM evolution_records WHERE draft_id=?",(did,)).fetchone() or db.execute("SELECT 1 FROM immortal_records WHERE draft_id=?",(did,)).fetchone():return False
    selected=db.execute("SELECT payload,checksum FROM genesis_variants WHERE draft_id=? AND option=?",(did,option)).fetchone()
    if not selected or o.digest(selected[0])!=selected[1]:return False
    p=json.loads(selected[0]);base=c.validate(p["base"])
    lit=o.validate_literary(db,base["story"],p["literary"])
    w=validate_world(db,base["story"],p["world"])
    score,warnings=o.review(db,base,lit)
    arc=db.execute("SELECT arc FROM saga_arcs WHERE draft_id=?",(did,)).fetchone()[0]
    warnings+=continuity_warnings(db,base,{"arc":arc})
    import soul_romance
    import soul_heart
    heart=soul_heart.variant_payload(db,did,base,option)
    soul_romance.refresh_variant(db,did,base,lit['events'])
    payload=c.encode(base);h=c.checksum(payload);meta=o.dump(lit);world_raw=o.dump(w)
    db.execute("UPDATE chronicle_drafts SET payload=?,checksum=? WHERE id=? AND status='pending'",(payload,h,did))
    if heart is not None:soul_heart.write(db,did,heart)
    db.execute("UPDATE omega_meta SET payload=?,checksum=?,score=?,warnings=? WHERE draft_id=?",(meta,o.digest(meta),score,o.dump(warnings),did))
    db.execute("INSERT OR REPLACE INTO genesis_world VALUES(?,?,?)",(did,world_raw,o.digest(world_raw)))
    db.execute("INSERT INTO genesis_edits(draft_id,before_hash,after_hash,chosen) VALUES(?,?,?,?)",(did,before,h,option))
    return True


def continuity_warnings(db,base,plan):
    """Flag explicit patterns only; do not claim understanding of all contradictions."""
    text=o.normalized(base["story"]);arc=plan.get("arc")
    warnings=[]
    if re.search(r"\b(?:десять|десятый|восемь|восьмой)\s+хвост",text) and "восьмой хвост" not in text:
        warnings.append("проверь число хвостов")
    if arc=="past" and any(p in text for p in ("наш первый поцелуй","мой любимый хозяин","после нашей встречи")):
        warnings.append("проверь хронологию встречи: сцена относится к прошлому")
    if any(p in text for p in ("защиту получил после","защита появилась после","обрёл защиту благодаря")):
        warnings.append("проверь врождённую защиту героя")
    relevant=recall(db,base["title"]+" "+base["story"][:400],3,arc)
    if relevant and len(o.tokens(base["story"]) & o.tokens(relevant[0]["story"])) / max(1,len(o.tokens(base["story"])))>.75:
        warnings.append("проверь смысловое сходство с главой "+str(relevant[0]["number"]))
    return warnings


def append_warnings(db,did,base,plan):
    m=o.metadata(db,did)
    if m:
        extra=continuity_warnings(db,base,plan)
        if extra: db.execute("UPDATE omega_meta SET warnings=?,score=? WHERE draft_id=?",(o.dump(m["warnings"]+extra),max(0,m["score"]-10*len(extra)),did))
