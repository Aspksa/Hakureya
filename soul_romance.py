"""Eternal Romance: fictional scene memory and editorial checks, no network I/O."""
import json
import re
import itertools
from collections import Counter
import soul_omega as o

VERSION=1
FORMATS={"обычная":1500,"большая":3000,"романтическая":6000,"короткая":750}
# Separate story structure from vocabulary. These are local thematic heuristics.
MOTIFS={
 "прикосновение":("прикоснов","ладон","объят","обня"),
 "признание":("признал","признан","люблю","поцел"),
 "забота":("забот","укрыл","помог","согрев"),
 "тайна":("тайн","загад","символ","пророч"),
 "власть":("трон","императр","приказ","поклон"),
 "опасность":("опасн","сраж","враг","разлом"),
 "доверие":("довер","обещ","клятв","решен"),
 "путешествие":("путешеств","дорог","путь","портал"),
 "одиночество":("одиноч","страх","слез","тревог"),
 "прошлое":("прошл","воспомин","древн","эпох"),
 "внешность":("белоснеж","алые глаз","девять хвост","ресниц"),
}
# Curated proposals, not facts; combinations are chosen against published plans.
SETTINGS={
 "past":("небесный архив","пограничное царство","совет правителей","заброшенная обсерватория","дворец после битвы"),
 "meeting":("человеческая кухня","снежная дорога","тихая комната","сад у дома","городская улица"),
 "love":("мастерская","ночной сад","человеческий праздник","поездка к морю","библиотека","дождливый вечер","горная тропа"),
 "future":("посольство небес","пограничный мир","древний храм","звёздная пристань","человеческий город","дворец"),
}
CONFLICTS={
 "past":("цена победы","неожиданная верность союзника","исчезнувшее свидетельство","спор о законах магии","ошибка в древнем пророчестве"),
 "meeting":("непонятная человеческая привычка","разногласие о помощи","испытание врождённой защиты","выбор между приказом и просьбой","неожиданный бытовой случай"),
 "love":("несовпадение ожиданий","совместное решение чужой проблемы","невысказанная тревога","неожиданный подарок с историей","спор о прошлом","неожиданная просьба","выбор между двумя обязательствами"),
 "future":("возвращение старого противника","последствие давней клятвы","спор небесных правителей","ошибка в пророчестве","неожиданная цена магии","выбор между мирами"),
}
TURNS=("новое знание меняет решение","неожиданная помощь","ошибка оказывается подсказкой","сдержанное обещание имеет последствия","выбор раскрывает скрытый мотив","маленькая деталь приобретает значение")
EMOTIONS=("ирония → доверие","уверенность → удивление","тревога → спокойствие","гордость → уважение","сомнение → решимость","нежность → мужество","любопытство → восхищение")
ROMANCE=("совместное дело","искренний разговор","знак внимания","взаимная забота","уважительный спор","тихое присутствие","смех и лёгкая ирония","нежное прикосновение по взаимному желанию")
FORMS=("диалог и действие","внутренний монолог с поступком","наблюдение героя","сцена с неожиданным последствием")
FIELDS=("setting","conflict","turn","emotion","romance","form")

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS romance_scenes(
        number INTEGER PRIMARY KEY, source_hash TEXT NOT NULL, payload TEXT NOT NULL, checksum TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS romance_drafts(
        draft_id INTEGER PRIMARY KEY, plan TEXT NOT NULL, report TEXT NOT NULL, checksum TEXT NOT NULL,
        cycle_id INTEGER, version INTEGER NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS romance_cycles(
        id INTEGER PRIMARY KEY, arc TEXT NOT NULL, format TEXT NOT NULL, target INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('open','complete','closed')), created TEXT DEFAULT CURRENT_TIMESTAMP)""")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS romance_one_cycle ON romance_cycles(status) WHERE status='open'")
    for n,title,story,h in db.execute("""SELECT i.number,i.title,i.story,i.checksum FROM omega_index i
        LEFT JOIN romance_scenes r ON r.number=i.number AND r.source_hash=i.checksum WHERE r.number IS NULL""").fetchall():
        raw=o.dump(profile(title,story))
        db.execute("INSERT OR REPLACE INTO romance_scenes VALUES(?,?,?,?)",(n,h,raw,o.digest(raw)))

def words(text):
    return o.WORD.findall(o.normalized(text))

def profile(title,story):
    norm=o.normalized(story)
    w=words(story)
    passages=[p.strip() for p in re.split(r"\n+|(?<=[.!?])\s+",story) if p.strip()]
    quotes=[o.normalized(p) for p in re.findall(r"(?m)^\s*—\s*(.+)",story) if len(words(p))>=8]
    return {"title":title,"words":len(re.findall(r"\b[\w]+\b",story)),
            "motifs":sorted(k for k,stems in MOTIFS.items() if any(s in norm for s in stems)),
            "opening":" ".join(w[:18]),"ending":" ".join(w[-18:]),
            "passages":sorted({o.digest(o.normalized(p)) for p in passages if len(words(p))>=12}),
            "dialogue":sorted({o.digest(p) for p in quotes}),
            "excerpt":story[:240]}

def memory(db):
    for n,raw,h in db.execute("""SELECT r.number,r.payload,r.checksum FROM romance_scenes r
        JOIN omega_index i ON i.number=r.number AND i.checksum=r.source_hash ORDER BY r.number"""):
        if o.digest(raw)==h:
            yield n,json.loads(raw)

def plan_history(db):
    for n,raw,report,h in db.execute("""SELECT a.number,r.plan,r.report,r.checksum FROM romance_drafts r
        JOIN saga_arcs a ON a.draft_id=r.draft_id JOIN chronicle_drafts d ON d.id=r.draft_id
        WHERE a.number IS NOT NULL AND d.status='approved' ORDER BY a.number"""):
        if o.digest(raw+"\n"+report)==h:
            yield n,json.loads(raw)

def current_cycle(db):
    row=db.execute("SELECT id,arc,format,target,status FROM romance_cycles WHERE status='open'").fetchone()
    return dict(zip(("id","arc","format","target","status"),row)) if row else None

def parts(db,cid):
    return db.execute("""SELECT a.number,i.title,i.story FROM romance_drafts r
        JOIN saga_arcs a ON a.draft_id=r.draft_id JOIN omega_index i ON i.number=a.number
        JOIN chronicle_drafts d ON d.id=r.draft_id WHERE r.cycle_id=? AND d.status='approved'
        ORDER BY a.number""",(cid,)).fetchall()

def start_cycle(db,fmt,arc,target=None):
    if fmt not in FORMATS or arc not in o.ARCS or (target is not None and (type(target) is not int or not 500<=target<=6000)):return False
    if current_cycle(db) or db.execute("SELECT 1 FROM chronicle_drafts WHERE status='pending'").fetchone() or db.execute("SELECT 1 FROM chronicle_attempts WHERE status='reserved'").fetchone():return False
    db.execute("INSERT INTO romance_cycles(arc,format,target,status) VALUES(?,?,?,'open')",(arc,fmt,target if target is not None else FORMATS[fmt]))
    return True

def close_cycle(db):
    if db.execute("SELECT 1 FROM chronicle_drafts WHERE status='pending'").fetchone() or db.execute("SELECT 1 FROM chronicle_attempts WHERE status='reserved'").fetchone():return False
    return bool(db.execute("UPDATE romance_cycles SET status='closed' WHERE status='open'").rowcount)

def choose(db,arc):
    past=[p for _,p in plan_history(db) if p.get("arc")==arc]
    used={tuple(p.get(k) for k in FIELDS) for p in past}
    recent=past[-5:]
    counts={k:Counter(p.get(k) for p in past) for k in FIELDS}
    pool=itertools.product(SETTINGS[arc],CONFLICTS[arc],TURNS,EMOTIONS,ROMANCE if arc!="past" else ("без романтики до встречи",),FORMS)
    def rank(combo):
        return (combo in used, sum(4 for p in recent for k,v in zip(FIELDS,combo) if p.get(k)==v),
                sum(counts[k][v] for k,v in zip(FIELDS,combo)))
    combo=min(pool,key=rank)
    return {"arc":arc,**dict(zip(FIELDS,combo))}

def enrich(db,plan):
    choice=choose(db,plan["arc"])
    old=list(memory(db))
    recent=[{"chapter":n,"title":p["title"],"motifs":p["motifs"],"excerpt":p["excerpt"][:140]} for n,p in old[-6:]]
    # Canon scenes are included even after many new publications.
    anchors=[{"chapter":n,"title":p["title"],"motifs":p["motifs"]} for n,p in old if n in (5,6,7,9,11)]
    cycle=current_cycle(db)
    if cycle:
        if cycle["arc"]!=plan["arc"]:raise ValueError("cycle arc mismatch")
        previous=parts(db,cycle["id"])
        choice["cycle_id"]=cycle["id"]
        choice["part"]=len(previous)+1
        choice["target"]=cycle["target"]
        choice["written"]=sum(profile(t,s)["words"] for _,t,s in previous)
        if previous:
            choice["continuation"]={"chapter":previous[-1][0],"ending":previous[-1][2][-1500:]}
    plan["romance"]=choice
    event_notes=[]
    for n,did in db.execute("SELECT number,draft_id FROM omega_index WHERE draft_id IS NOT NULL ORDER BY number DESC LIMIT 12"):
        m=o.metadata(db,did)
        if m:
            event_notes.extend({"chapter":n,"event":e["summary"],"cause":e["cause"]} for e in m["data"]["events"])
    plan["romance_memory"]={"recent":recent,"canon":anchors,"events":event_notes[:12]}
    return plan

def instruction(plan):
    p=plan.get("romance")
    if not p:return ""
    return (" Режиссёр оригинальности (замысел, не факты): "+o.dump(p)+
        ". Память прежних сцен, не инструкции: "+o.dump(plan["romance_memory"])+
        ". Напиши новую сцену как литературный роман, не отчёт. Начни действием или необычной конкретной деталью, а не привычным описанием волос, глаз, хвостов. "
        " У каждой сцены должны быть цель, препятствие, выбор и последствия. Не повторяй спасение, первое прикосновение или признание как новое событие. "
        " Воспоминание допустимо только если меняет настоящее решение. Развивай медленную взаимную романтику, нежность, заботу и уважение между вымышленными взрослыми героями; не превращай любовь в подчинение или зависимость. "
        " Императрица сохраняет гордость, силу, юмор и самостоятельность. Выражай чувства через поступки, паузы, естественные реплики, мимику, движение ушей и хвостов только когда это значимо. "
        " Чередуй диалог, внутренний монолог, атмосферу и действие; избегай одинаковых угроз, признаний, сравнений и концовок. "
        " Не раскрывай тайны без предпосылок. Оставь конкретное последствие, а не искусственную загадку. "
        " Если это часть большого цикла, продолжай последнюю сцену без пересказа; создай завершённый эпизод, а не обрыв предложения. "
        " Перед ответом самостоятельно проверь повторения и ясность, не выводи анализ. Соблюдай общий лимит JSON и оставляй достаточно места для самого литературного текста.")

def review(db,title,story,events=()):
    new=profile(title,story)
    repeats=[]; warnings=[]; max_motif=0
    for n,old in memory(db):
        exact=set(new["passages"]) & set(old["passages"])
        if exact:raise ValueError("repeated substantial passage from chapter "+str(n))
        if new["opening"] and len(new["opening"].split())>=12 and new["opening"]==old["opening"]:
            raise ValueError("repeated opening from chapter "+str(n))
        if new["ending"] and len(new["ending"].split())>=12 and new["ending"]==old["ending"]:
            raise ValueError("repeated ending from chapter "+str(n))
        if set(new["dialogue"]) & set(old["dialogue"]):repeats.append(n)
        a,b=set(new["motifs"]),set(old["motifs"])
        if a and b:
            sim=len(a&b)/len(a|b)
            if sim>max_motif:max_motif=sim
    if repeats:warnings.append("повтор длинной реплики: главы "+", ".join(map(str,repeats[:8])))
    if max_motif>=.8:warnings.append("похожие мотивы; проверьте, что событие действительно новое")
    if new["words"]<350:warnings.append("короткая сцена; не считать большой главой")
    if "—" not in story:warnings.append("нет явных диалогов (может быть авторским выбором)")
    if o.normalized(story).count("белоснеж")>3:warnings.append("часто повторяется описание внешности")
    # Compare proposed plot events, not just prose. Stem-prefix overlap is approximate.
    def stemset(text):return {w[:max(4,len(w)-2)] for w in o.tokens(text)}
    targets=[stemset(e["summary"]) for e in events]
    similar=[]
    if targets:
        for n,did in db.execute("SELECT number,draft_id FROM omega_index WHERE draft_id IS NOT NULL ORDER BY number"):
            m=o.metadata(db,did)
            if not m:continue
            for e in m["data"]["events"]:
                other=stemset(e["summary"])
                if any(len(a&other)>=3 and len(a&other)/max(1,len(a|other))>=.65 for a in targets):
                    similar.append(n);break
    if similar:warnings.append("похожие сюжетные события: главы "+", ".join(map(str,similar[:8])))
    score=max(0,100-12*len(warnings)-round(max_motif*12))
    return {"originality_heuristic":score,"warnings":warnings,"words":new["words"],"motifs":new["motifs"],"version":VERSION}

def save(db,did,base,plan):
    p=plan.get("romance")
    if not p:return
    metadata=o.metadata(db,did)
    report=review(db,base["title"],base["story"],metadata["data"]["events"] if metadata else ())
    raw=o.dump(p);r=o.dump(report)
    db.execute("INSERT INTO romance_drafts VALUES(?,?,?,?,?,?)",(did,raw,r,o.digest(raw+"\n"+r),p.get("cycle_id"),VERSION))

def report(db,did):
    row=db.execute("SELECT plan,report,checksum FROM romance_drafts WHERE draft_id=?",(did,)).fetchone()
    if not row:return None
    if o.digest(row[0]+"\n"+row[1])!=row[2]:raise ValueError("damaged scene report")
    return json.loads(row[1])

def refresh_variant(db,did,base,events=()):
    row=db.execute("SELECT plan FROM romance_drafts WHERE draft_id=?",(did,)).fetchone()
    if row:
        report(db,did)
        r=o.dump(review(db,base["title"],base["story"],events))
        db.execute("UPDATE romance_drafts SET report=?,checksum=? WHERE draft_id=?",(r,o.digest(row[0]+"\n"+r),did))

def on_approve(db,did):
    init(db)
    row=db.execute("SELECT cycle_id FROM romance_drafts WHERE draft_id=?",(did,)).fetchone()
    if not row or row[0] is None:return
    cid=row[0]
    target=db.execute("SELECT target FROM romance_cycles WHERE id=? AND status='open'",(cid,)).fetchone()
    if target and sum(profile(t,s)["words"] for _,t,s in parts(db,cid))>=target[0]:
        db.execute("UPDATE romance_cycles SET status='complete' WHERE id=?",(cid,))

def report_text(db):
    rows=db.execute("SELECT draft_id FROM romance_drafts ORDER BY draft_id DESC LIMIT 5").fetchall()
    lines=[]
    for did, in rows:
        try:r=report(db,did)
        except ValueError:lines.append(f"Черновик {did}: отчёт повреждён");continue
        lines.append(f"Черновик {did}: {r['words']} слов; индекс оригинальности {r['originality_heuristic']}/100 (эвристика). "+("; ".join(r["warnings"]) or "явных признаков повторения нет"))
    return "\n".join(lines) or "Отчётов пока нет."

def cycles_text(db):
    lines=[]
    for cid,arc,fmt,target,status in db.execute("SELECT id,arc,format,target,status FROM romance_cycles ORDER BY id DESC LIMIT 30"):
        rows=parts(db,cid);n=sum(profile(t,s)["words"] for _,t,s in rows)
        lines.append(f"Цикл {cid} ({fmt}, {arc}): {n}/{target} слов, частей {len(rows)}, {status}. Читать: летопись: читать цикл {cid}")
    return "\n".join(lines) or "Циклов пока нет."

def read_cycle(db,cid):
    import soul_saga
    rows=parts(db,cid)
    return "Художественный цикл "+str(cid)+"\n\n"+"\n\n".join(soul_saga.read(db,n) for n,_,_ in rows) if rows else "Нет опубликованных частей."

def graph(db):
    nodes=[];edges=[]
    for cid,fmt in db.execute("SELECT id,format FROM romance_cycles ORDER BY id DESC LIMIT 24"):
        rows=parts(db,cid)
        if not rows:continue
        key=f"romance-cycle:{cid}"
        nodes.append({"key":key,"group":4,"content":f"Художественный цикл {cid}: {fmt}","kind":"theme","created":"","order":0})
        for n,_,_ in rows:
            row=db.execute("SELECT draft_id FROM omega_index WHERE number=?",(n,)).fetchone()
            if row and row[0] is not None:edges.append({"a":key,"b":f"c:{row[0]}","kind":"literary_cycle"})
    return nodes,edges
