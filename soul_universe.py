"""Eternal Universe: local scene retrieval and editorial coordination.

The source of truth remains the approved manuscript. Plans are not events.
No new model calls, no user-chat data, no synthetic character facts.
"""
import re
from collections import Counter
import soul_omega as o
import soul_evolution as ev
import soul_dynasty as dy
import soul_intelligence as li

VERSION=1
SCENE_LIMIT=2200
# Additional scene directions attached to existing milestones, not a second saga.
DYNASTY_LENSES={
11: "Раскрой жизнь Маюри до обвинения, её собственную цель, последнюю ночь в темнице. Не завершай приговор до подтверждающего события.",
12: "Появление Хакурэи перед казнью глазами Маюри; страх перед неизвестным решением, тайное спасение и последствия во дворце.",
13: "Первые минуты в человеческом доме: незнакомая речь, предметы и человек. Маюри не понимает его статуса и не знает о любви Хакурэи.",
15: "Предложение личной службы, первый разговор наедине, безопасность и свобода выбора. Не превращай спасение в долг любви.",
32: "Постепенное освоение человеческой речи и технологий, дневник Маюри, маленькие ошибки и самостоятельные открытия.",
16: "Маюри наблюдает нежность императрицы, сопоставляет поступки человека и свои чувства, не торопи признание.",
19: "Раздели расследование приговора на свидетельства, противоречия и последствия; не назначай виновника без доказанной развязки.",
1: "История происхождения взрослой младшей сестры, её обязанности, собственный дворец и общие воспоминания сестёр.",
3: "Тайный разговор хранительниц и конкретный источник сведений Цукинохи; подозрение не равно знанию.",
4: "Первая встреча в человеческом мире с точки зрения Цукинохи; самостоятельная причина визита.",
5: "Недоверие Цукинохи и наблюдение за поступками героя; исследование дара только с разрешения.",
6: "Осознание собственных чувств через уже опубликованные совместные события, не мгновенная влюблённость.",
7: "Личный конфликт Цукинохи, осторожный разговор с Маюри только если они уже знакомы.",
8: "Ревность сестёр через разные цели и решения, не разрушай их родство.",
9: "Хакурэя узнаёт правду лишь из конкретного признания или наблюдаемого свидетельства, а не всеведения."
}
STYLES={
"love":"Нежность через действия, естественные паузы и разные реакции; не повторяй признание.",
"court":"Дворцовая интрига: мотивы, ограниченное знание, решение и политические последствия.",
"mystery":"Улики, альтернативные объяснения, честное ограничение знания; не раскрывай преждевременно.",
"world":"Приключение: конкретные места, культура, препятствие и последствия выбора.",
"power":"Исследование силы: наблюдение, пределы, проверка и цена, без внезапного всемогущества.",
"character":"Внутренний конфликт, характерная речь и самостоятельный поступок.",
"guardians":"Различимые голоса хранительниц, собственные задачи, разговоры без героя.",
"growth":"Изменение убеждения через действие, ошибку и последствие."
}

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS universe_scenes(
        chapter INTEGER NOT NULL, seq INTEGER NOT NULL, start INTEGER NOT NULL,
        end INTEGER NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
        PRIMARY KEY(chapter,seq))""")
    db.execute("""CREATE TABLE IF NOT EXISTS universe_sources(
        chapter INTEGER PRIMARY KEY, digest TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS universe_terms(
        term TEXT NOT NULL, chapter INTEGER NOT NULL, seq INTEGER NOT NULL,
        weight INTEGER NOT NULL, PRIMARY KEY(term,chapter,seq))""")
    db.execute("""CREATE TABLE IF NOT EXISTS universe_plans(
        attempt TEXT PRIMARY KEY, payload TEXT NOT NULL, checksum TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS universe_settings(
        id INTEGER PRIMARY KEY CHECK(id=1), chapter_pages INTEGER NOT NULL)""")
    db.execute("INSERT OR IGNORE INTO universe_settings VALUES(1,0)")
    db.execute("CREATE INDEX IF NOT EXISTS universe_terms_chapter ON universe_terms(chapter,seq)")

def chapter_pages(db):
    return db.execute("SELECT chapter_pages FROM universe_settings WHERE id=1").fetchone()[0]

def set_chapter_pages(db,value):
    if type(value) is not int or value not in (0,5,10,15,20,30):
        raise ValueError("invalid chapter pages")
    db.execute("UPDATE universe_settings SET chapter_pages=? WHERE id=1",(value,))

def split(story):
    """Contiguous exact source spans; prefer authored headings and paragraph boundaries."""
    start=0
    title=""
    headings=list(re.finditer(r"^#### ([^\n]+)",story,re.M))
    boundaries=sorted(set([0,len(story)]+[m.start() for m in headings]))
    names={m.start():m[1] for m in headings}
    for lo,hi in zip(boundaries,boundaries[1:]):
        title=names.get(lo,title)
        start=lo
        while start<hi:
            end=min(hi,start+SCENE_LIMIT)
            if end<hi:
                cut=story.rfind("\n\n",start+SCENE_LIMIT//2,end)
                if cut>=0:end=cut+2
            yield start,end,title,story[start:end]
            start=end

def refresh(db,force=False):
    changed=0
    for n,title,story,source in db.execute("SELECT number,title,story,checksum FROM omega_index ORDER BY number"):
        digest=o.digest(o.dump([VERSION,title,story,source]))
        old=db.execute("SELECT digest FROM universe_sources WHERE chapter=?",(n,)).fetchone()
        if not force and old==(digest,):continue
        db.execute("DELETE FROM universe_terms WHERE chapter=?",(n,))
        db.execute("DELETE FROM universe_scenes WHERE chapter=?",(n,))
        for seq,(a,b,heading,body) in enumerate(split(story),1):
            db.execute("INSERT INTO universe_scenes VALUES(?,?,?,?,?,?)",(n,seq,a,b,heading or title,body))
            allowed=o.tokens(body+" "+heading+" "+title)
            terms=Counter(t for t in o.WORD.findall(o.normalized(body+" "+heading+" "+title)) if t in allowed)
            db.executemany("INSERT INTO universe_terms VALUES(?,?,?,?)",[(t,n,seq,w) for t,w in terms.items()])
        db.execute("INSERT OR REPLACE INTO universe_sources VALUES(?,?)",(n,digest))
        changed+=1
    for table in ("universe_terms","universe_scenes","universe_sources"):
        db.execute("DELETE FROM "+table+" WHERE chapter NOT IN (SELECT number FROM omega_index)")
    return changed

def search(db,query,limit=6,visible=True,arc=None):
    refresh(db)
    import soul_genesis as ge
    terms=sorted(o.tokens(query),key=lambda t:(-len(t),t))[:12]
    prefixes={t[:max(4,len(t)-2)] for t in terms if len(t)>=4}
    for k,related in ge.CONCEPTS.items():
        if any(t.startswith(k[:4]) for t in terms):prefixes.update(related)
    scores=Counter()
    for prefix in sorted(prefixes)[:32]:
        for n,s,w in db.execute("SELECT chapter,seq,SUM(weight) FROM universe_terms WHERE term>=? AND term<? GROUP BY chapter,seq",(prefix,prefix+"\U0010ffff")):
            scores[n,s]+=min(w,4)
    for t in terms:
        for n,s,w in db.execute("SELECT chapter,seq,weight FROM universe_terms WHERE term=?",(t,)):
            scores[n,s]+=2*min(w,4)
    out=[]
    for (n,s),score in sorted(scores.items(),key=lambda x:(-x[1],-x[0][0],x[0][1])):
        if visible and not ev.readable(db,n):continue
        row=db.execute("SELECT i.arc,s.title,s.body,s.start,s.end,i.story FROM universe_scenes s JOIN omega_index i ON i.number=s.chapter WHERE s.chapter=? AND s.seq=?",(n,s)).fetchone()
        if not row or (arc and row[0]!=arc):continue
        if not 0<=row[3]<row[4]<=len(row[5]) or row[5][row[3]:row[4]]!=row[2]:raise ValueError("scene source mismatch")
        out.append(dict(chapter=n,scene=s,title=row[1],text=row[2],start=row[3],end=row[4],score=score))
        if len(out)>=limit:break
    return out

def coordinate(db,plan):
    """Explicit precedence, reject incompatible mandatory lanes before paid I/O."""
    mandatory=[k for k in ("dynasty","guardians","shadow","destiny") if plan.get(k)]
    if len(mandatory)>1:raise ValueError("conflicting mandatory lanes")
    novel=plan.get("novel",{})
    director=plan.get("director",{})
    if mandatory:
        lane=mandatory[0]
        if lane=="dynasty":
            choice=plan[lane]["current"]
            if plan.get("arc")!="future":raise ValueError("dynasty outside future")
        else:choice=plan[lane]
    elif plan.get("alternative"):
        lane="alternative";choice={}
    elif novel.get("part",1)>1:
        lane="continuation";choice=director or {}
    else:
        lane="director";choice=director or plan.get("evolution",{}).get("chosen",{}) or {}
    theme=choice.get("theme",plan.get("evolution",{}).get("chosen",{}).get("theme","character"))
    title=choice.get("title",novel.get("title") or lane)
    lens=DYNASTY_LENSES.get(choice.get("id"),"") if lane=="dynasty" else ""
    query=" ".join(str(x) for x in (title,choice.get("guide",""),lens[:180]))
    # Cross-arc retrieval only in the future; historical scenes must not acquire future knowledge.
    recalled=search(db,query,3,False,None if plan["arc"]=="future" else plan["arc"])
    refs=[{"chapter":r["chapter"],"scene":r["scene"],"title":r["title"],"quote":r["text"][:450]} for r in recalled]
    p={"lane":lane,"theme":theme,"title":title,"lens":lens,"refs":refs,
       "part":novel.get("part",1),"start":novel.get("start",0),
       "style":STYLES.get(theme,STYLES["character"]),
       "structure":["цель персонажа","осложнение","решение или выбор","наблюдаемое последствие"],
       "continuation":bool(novel.get("part",1)>1)}
    plan["universe"]=p
    return p

def instruction(plan):
    p=plan.get("universe")
    if not p:return ""
    return (" Eternal Universe — согласованный план (не события канона): "+o.dump(p)+
            ". Приоритет текущей линии выше конкурирующих прогнозов. Структура относится к целой группе сцен, не требуй кульминации в каждой части. "
            "Покажи при уместности параллельную жизнь двора, человеческого мира или иного известного мира через самостоятельные цели героев. "
            "Отделяй свидетельство от слуха, наблюдение от знания; не сообщай персонажу прочитанный автором источник автоматически. "
            "Сохраняй неразгаданные тайны и последствия предыдущих решений. Воспоминания привязывай к конкретной сцене, не пересказывай её. "
            "Различай интонации персонажей, избегай одинаковых реплик, эпитетов и повторного знакомства.")

def record(db,attempt,plan):
    p=plan.get("universe")
    if p:
        raw=o.dump(p)
        db.execute("INSERT INTO universe_plans VALUES(?,?,?)",(attempt,raw,o.digest(raw)))
def latest_plan(db):
    row=db.execute("SELECT payload,checksum FROM universe_plans ORDER BY attempt DESC LIMIT 1").fetchone()
    if not row:return None
    if o.digest(row[0])!=row[1]:raise ValueError("universe plan damaged")
    import json
    return json.loads(row[0])

def overview(db,page=1):
    refresh(db)
    li.refresh(db)
    rows=db.execute("SELECT number,arc,title,LENGTH(story) FROM omega_index ORDER BY number").fetchall()
    # Do not expose unread titles, character details or planned revelations.
    visible=[{"number":n,"volume":o.volume(n),"arc":arc,"title":title if ev.readable(db,n) else "Непрочитанная часть","chars":length} for n,arc,title,length in rows]
    actors,relations=li.registry(list(li.rows(db,visible=True)))
    volumes=Counter(o.volume(r[0]) for r in rows)
    return {"volume_groups":[{"volume":v,"count":count} for v,count in sorted(volumes.items()) if any(item["volume"]==v for item in visible[(page-1)*50:page*50])],"chapters":len(rows),"chars":sum(r[3] for r in rows),"scenes":db.execute("SELECT COUNT(*) FROM universe_scenes").fetchone()[0],
            "volumes":len({o.volume(r[0]) for r in rows}),"actors":len(actors),"relations":len(relations),
            "items":visible[(page-1)*50:page*50],"pages":max(1,(len(rows)+49)//50),
            "chapter_pages":chapter_pages(db),
            "lanes":dict(Counter(r[1] for r in rows)),
            "pending":db.execute("SELECT COUNT(*) FROM chronicle_drafts WHERE status='pending'").fetchone()[0]}

def report(db,mode,query=""):
    if mode=="search":
        hits=search(db,query)
        return "\n\n".join(f"Глава {r['chapter']}, сцена {r['scene']} — {r['title']}\n{r['text']}" for r in hits) or "Нет доступных сцен."
    if mode=="plan":
        p=latest_plan(db)
        return ("Последний сохранённый план (спойлеры, не канон):\n"+o.dump(p)) if p else "Писатель ещё не сохранил план Universe."
    if mode=="repair":
        if db.execute("PRAGMA quick_check").fetchone()[0]!="ok":return "SQLite повреждена; нужен проверенный снимок."
        return f"Перестроен индекс сцен: {refresh(db,True)} глав. Текст не изменён."
    if mode=="knowledge":
        facts=[f for f in ev.state(db).values() if f["kind"] in ("knowledge","secret") and ev.readable(db,f["chapter"])]
        return "\n".join(f"{f['chapter']}: {f['subject']} — {f['detail']} | свидетели: {', '.join(f['knows']) or 'не подтверждены'}" for f in facts[-40:]) or "Нет доступных подтверждённых записей о знаниях."
    if mode=="actor":
        name=li.norm(query)
        records=[(n,f) for n,f in li.rows(db,visible=True) if li.norm(f["subject"])==name or (f.get("object") and li.norm(f["object"])==name)]
        return "\n\n".join(f"Глава {n}: {f['kind']} — {f['value']}\n«{f['quote']}»" for n,f in records[-30:]) or "Нет доступных свидетельств о персонаже."
    if mode=="timeline":
        data=overview(db)
        return "\n".join(f"{r['number']}. {r['title']} · том {r['volume']} · {r['arc']}" for r in data["items"])
    if mode=="atlas":
        import soul_genesis
        return soul_genesis.atlas(db)
    if mode=="audit":
        refresh(db)
        for n,story in db.execute("SELECT number,story FROM omega_index"):
            spans=db.execute("SELECT start,end,body FROM universe_scenes WHERE chapter=? ORDER BY seq",(n,)).fetchall()
            end=0
            for a,b,body in spans:
                if a!=end or not a<b<=len(story) or body!=story[a:b]:return f"Индекс повреждён: глава {n}."
                end=b
            if end!=len(story):return f"Индекс неполон: глава {n}."
        return "Целостность индекса сцен подтверждена; это не смысловая проверка."
    data=overview(db)
    return f"Литературная вселенная: {data['chapters']} опубликованных частей, {data['scenes']} сцен, {data['volumes']} томов, {data['chars']} знаков. Персонажей: {data['actors']}; отношений: {data['relations']}. Черновиков: {data['pending']}."
