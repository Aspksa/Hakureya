"""Evidence-based literary intelligence. Derived observations, never new canon.

All text originates in approved chapters. Lexical checks are review signals,
not proof of a fictional event or a character's mental state.
"""
import json
import re
from collections import defaultdict, Counter
from difflib import SequenceMatcher
import soul_omega as o
import soul_intelligence as li
import soul_universe as u
import soul_evolution as ev
import soul_infinite as inf

VERSION=1
PROFILE={"biography","identity","age","trait","habit","fear","goal","voice","belief","location","power","limit","knowledge","secret","letter","relationship","love_moment"}
STABLE={"identity","law","limit","origin"}
THREADS={"clue","promise","conflict"}
KINDS=PROFILE|STABLE|THREADS|{"character","artifact","event","consequence","prophecy","reveal","close","emotion","tradition",*li.RELATIONS}
CONCEPTS=(
 ("страх","боится","боялась","испуг","дрож","опасен","ужас"),
 ("любов","нежност","ласк","объя","поцел","признан","возлюб"),
 ("казн","приговор","темниц","спас","палач","осужд"),
 ("подар","артефакт","вещь","снежин","сувенир"),
 ("обещ","клятв","договор","обязат"),
 ("загад","тайн","секрет","неизвест","улика"),
 ("знан","узна","сведен","рассказ","сообщ","свидетел"),
 ("дворец","двор","совет","император","хакусэйден"),
 ("магия","магич","сила","заклин","энерги"),
 ("сестр","родств","семь","династ"),
 ("горнич","маюри","служ","помощниц"),
 ("путешеств","перемещ","портал","прибыл","отправ")
)

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS intellect_sources(
        chapter INTEGER PRIMARY KEY, digest TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS intellect_evidence(
        id TEXT PRIMARY KEY, chapter INTEGER NOT NULL, actor TEXT NOT NULL,
        kind TEXT NOT NULL, payload TEXT NOT NULL, checksum TEXT NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS intellect_actor ON intellect_evidence(actor,chapter)")
    db.execute("CREATE INDEX IF NOT EXISTS intellect_chapter ON intellect_evidence(chapter)")
    db.execute("CREATE INDEX IF NOT EXISTS intellect_kind ON intellect_evidence(kind,chapter)")
    db.execute("""CREATE TABLE IF NOT EXISTS intellect_identity(
        id TEXT PRIMARY KEY, name TEXT NOT NULL, origin_chapter INTEGER NOT NULL,
        quote TEXT NOT NULL, checksum TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS intellect_assignments(
        evidence_id TEXT PRIMARY KEY, identity_id TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS intellect_runs(
        attempt TEXT PRIMARY KEY,payload TEXT NOT NULL,checksum TEXT NOT NULL)""")

def visible(db,n):
    return n<=13 or ev.readable(db,n)

def evidence_id(n,f):
    return o.digest(o.dump([n,f]))[:32]

def refresh(db):
    li.refresh(db)
    # Index immutable publication metadata once per changed fingerprint.
    changed=0
    for n,raw,h in db.execute("""SELECT l.number,l.payload,l.checksum FROM lit_index l
       LEFT JOIN intellect_sources s ON s.chapter=l.number
       WHERE s.digest IS NULL OR s.digest!=l.checksum ORDER BY l.number""").fetchall():
        if o.digest(raw)!=h:raise ValueError("intellect source checksum")
        chapter=db.execute("SELECT arc,title,story,checksum,draft_id FROM omega_index WHERE number=?",(n,)).fetchone()
        if not chapter:raise ValueError("intellect source missing")
        u.verified_source(db,n,*chapter)
        records=json.loads(raw)["records"]
        db.execute("DELETE FROM intellect_evidence WHERE chapter=?",(n,))
        for f in records:
            quote=f["quote"]
            if not quote or quote not in chapter[2]:raise ValueError("intellect evidence missing")
            data={**f,"chapter":n,"arc":chapter[0],"start":chapter[2].index(quote)}
            payload=o.dump(data)
            db.execute("INSERT OR IGNORE INTO intellect_evidence VALUES(?,?,?,?,?,?)",
                       (evidence_id(n,f),n,li.actor_key(f["subject"]),f["kind"],payload,o.digest(payload)))
        db.execute("INSERT OR REPLACE INTO intellect_sources VALUES(?,?)",(n,h))
        changed+=1
    db.execute("DELETE FROM intellect_evidence WHERE chapter NOT IN (SELECT number FROM lit_index)")
    db.execute("DELETE FROM intellect_sources WHERE chapter NOT IN (SELECT number FROM lit_index)")
    return changed

def rows(db,actor=None,kind=None,public=True,limit=120):
    sql="""SELECT e.id,e.chapter,COALESCE(a.identity_id,e.actor),e.payload,e.checksum
           FROM intellect_evidence e LEFT JOIN intellect_assignments a ON a.evidence_id=e.id WHERE 1=1"""
    args=[]
    if actor is not None:sql+=" AND COALESCE(a.identity_id,e.actor)=?";args.append(actor)
    if kind is not None:sql+=" AND e.kind=?";args.append(kind)
    if public and ev.settings(db)[1]:
        sql+=" AND (e.chapter<=13 OR e.chapter IN (SELECT number FROM evolution_read))"
    sql+=" ORDER BY e.chapter DESC,e.id LIMIT ?";args.append(max(1,min(500,limit)))
    result=[]
    for eid,n,key,raw,h in db.execute(sql,args):
        if o.digest(raw)!=h:raise ValueError("intellect evidence checksum")
        f=json.loads(raw)
        if f["chapter"]!=n:raise ValueError("intellect evidence chapter")
        result.append(dict(f,id=eid,actor_id=key))
    return list(reversed(result))

def create_identity(db,name,n,quote):
    """Explicit disambiguation, no guessed split or merge of same-name actors."""
    name=o.clean(name,2,60);quote=o.clean(quote,12,240)
    source=db.execute("SELECT arc,title,story,checksum,draft_id FROM omega_index WHERE number=?",(n,)).fetchone()
    if not source or not visible(db,n):raise ValueError("identity source unavailable")
    u.verified_source(db,n,*source)
    if quote not in source[2] or li.norm(name) not in o.normalized(quote):raise ValueError("identity evidence")
    ident="person:"+o.digest(o.dump([li.norm(name),n,quote]))[:24]
    raw=o.dump([ident,name,n,quote])
    db.execute("INSERT OR IGNORE INTO intellect_identity VALUES(?,?,?,?,?)",(ident,name,n,quote,o.digest(raw)))
    return ident

def assign_identity(db,eid,ident):
    row=db.execute("SELECT name,origin_chapter,quote,checksum FROM intellect_identity WHERE id=?",(ident,)).fetchone()
    e=db.execute("SELECT chapter,payload,checksum FROM intellect_evidence WHERE id=?",(eid,)).fetchone()
    if not row or not e or not visible(db,e[0]) or not visible(db,row[1]):raise ValueError("identity assignment source")
    if o.digest(o.dump([ident,*row[:3]]))!=row[3] or o.digest(e[1])!=e[2]:raise ValueError("identity checksum")
    fact=json.loads(e[1])
    if li.norm(fact["subject"])!=li.norm(row[0]):raise ValueError("different names; review required")
    db.execute("INSERT OR REPLACE INTO intellect_assignments VALUES(?,?)",(eid,ident))

def candidates(db,query,public=True,arc=None,limit=4):
    # Local concept expansion and reciprocal-rank fusion, not vector embeddings.
    normalized=o.normalized(query)
    hits=u.search(db,query,12,public,arc)
    scores=Counter();items={}
    def add(data,weight):
        for i,r in enumerate(data):
            k=(r["chapter"],r["scene"]);items[k]=r;scores[k]+=weight/(8+i)
    add(hits,2)
    for group in CONCEPTS:
        if any(s in normalized for s in group):
            add(u.search(db," ".join(group),8,public,arc),1)
    return [dict(items[k],rank=round(scores[k],4)) for k in sorted(scores,key=lambda k:(-scores[k],-k[0],k[1]))[:limit]]

def concerns(db,records,public=True):
    """Conservative review flags; quoted dialogue, negation, and changes can be valid."""
    issues=[]
    for f in records:
        n=f["chapter"];cause=f.get("cause")
        if cause is not None and (cause>=n or not db.execute("SELECT 1 FROM omega_index WHERE number=?",(cause,)).fetchone()):
            issues.append({"kind":"cause","chapter":n,"detail":"Причина отсутствует или находится после события","source":f["id"]})
        if f["kind"] in STABLE and f.get("object"):
            for prior in reversed(rows(db,f["actor_id"],f["kind"],public,120)):
                if prior["chapter"]>=n or li.norm(prior.get("object",""))!=li.norm(f["object"]):continue
                if o.normalized(prior["value"])!=o.normalized(f["value"]) and cause!=prior["chapter"]:
                    issues.append({"kind":"stable","chapter":n,"prior":prior["chapter"],"detail":"Возможное изменение устойчивого факта без указанной причины","source":f["id"]})
                break
    return issues[:30]

def prepare(db,plan):
    refresh(db)
    theme=plan.get("universe") or {}
    query=" ".join(str(x) for x in (theme.get("title",""),theme.get("lens","")[:160],plan.get("guide","")[:180]))
    refs=candidates(db,query,False,None if plan["arc"]=="future" else plan["arc"],4)
    latest=rows(db,public=False,limit=100)
    if plan["arc"]!="future":latest=[x for x in latest if x["arc"]==plan["arc"]]
    relevant=[]
    for f in latest:
        if f["kind"] in PROFILE|THREADS|STABLE|{"artifact","event","consequence"}:
            relevant.append(f)
    # Preserve latest evidence for each category, with chapter/quote, not fabricated summaries.
    selected={}
    for f in reversed(relevant):
        k=(f["actor_id"],f["kind"],li.norm(f.get("object","")))
        if k not in selected:selected[k]=f
    _,threads,_=inf.ledger(list(inf.published(db)))
    last=db.execute("SELECT COALESCE(MAX(number),13) FROM omega_index").fetchone()[0]
    open_threads=[{"chapter":t["chapter"],"kind":t["kind"],"value":t["value"][:120],"delay":t.get("delay",0)} for t in threads.values() if t["closed"] is None and (plan["arc"]=="future" or db.execute("SELECT arc FROM omega_index WHERE number=?",(t["chapter"],)).fetchone()==(plan["arc"],))]
    issues=concerns(db,latest,False)
    profiles=[{"chapter":f["chapter"],"subject":f["subject"],"kind":f["kind"],"value":f["value"][:100],"quote":f["quote"][:120]} for f in list(selected.values())[:8]]
    notes={"refs":[{"chapter":r["chapter"],"scene":r["scene"],"quote":u.focused_excerpt(r["text"],query,360)} for r in refs],
           "profiles":profiles,"open":open_threads[:4],"issues":issues[:3],
           "scope":plan["arc"],"last":last}
    # Explicit cap; preserve valid JSON and do not cut quoted spans mid-encoding.
    while len(o.dump(notes).encode("utf-8"))>3800:
        choices=[k for k in ("profiles","refs","open","issues") if notes[k]]
        if not choices:break
        largest=max(choices,key=lambda k:len(o.dump(notes[k][-1]).encode("utf-8"))*len(notes[k]))
        notes[largest].pop()
    plan["intellect7"]=notes
    return notes

def instruction(plan):
    p=plan.get("intellect7")
    if not p:return ""
    return (" Eternal Intelligence: архив свидетельств, не готовые события: "+o.dump(p)+
       ". Отдельные цели, страхи, привычки, голос и знания персонажей подтверждай сценами. "
       "Покажи при уместности жизнь хранительницы, Маюри или Цукинохи без главного героя, но не вводи их до появления в утверждённом сюжете. "
       "Различай слух, знание, признание и эмоциональную реакцию. Покажи, кто кому передал сведения, где и почему. "
       "Не превращай дневник в объективную истину; не раскрывай тайну раньше разрешённого этапа. "
       "Воспоминание и событие в настоящем — разные вещи. Учитывай арку и указанные причины. "
       "Предупреждения являются поводом проверить текст, а не утверждением ошибки.")

def record_run(db,attempt,plan):
    p=plan.get("intellect7")
    if p:
        raw=o.dump(p)
        db.execute("INSERT INTO intellect_runs VALUES(?,?,?)",(attempt,raw,o.digest(raw)))

def report(db,mode,query=""):
    refresh(db)
    if mode=="search":
        hits=candidates(db,query)
        return "\n\n".join(f"Глава {r['chapter']}, сцена {r['scene']} — {r['title']}\n{r['text']}" for r in hits) or "Нет доступных совпадений."
    if mode=="profile":
        records=rows(db,query if query.startswith(("person:","lit:actor:","character:","guardian:")) else li.actor_key(query),limit=60)
        return ("Досье: свидетельства, а не диагноз или всеведение.\n"+"\n\n".join(f"{r['chapter']} · {r['kind']} · {r['value']}\n«{r['quote']}» · ID {r['id']}" for r in records)) if records else "Нет доступных свидетельств."
    if mode=="issues":
        issues=concerns(db,rows(db,limit=300))
        return "\n".join(f"Глава {x['chapter']}: {x['detail']}" for x in issues) or "В доступных проверенных записях эвристические конфликты не найдены; это не гарантия непротиворечивости."
    if mode=="threads":
        _,threads,_=inf.ledger(list(inf.published(db)),at=lambda n:visible(db,n))
        return "\n".join(f"{v['chapter']} · {v['kind']} · {v['value']} · "+("открыто" if v["closed"] is None else f"закрыто в {v['closed']}") for v in list(threads.values())[-60:]) or "Нет доступных записей о нитях."
    if mode=="knowledge":
        out=[]
        for n,_,p in ev.published(db):
            if not visible(db,n):continue
            for f in p["facts"]:
                if f["kind"] in ("knowledge","secret"):
                    out.append(f"{n} · {f['subject']}: {f['detail']} · свидетели: "+(", ".join(f["knows"]) or "не указаны")+" · источник: «"+f["evidence"]+"»")
        return "\n\n".join(out[-60:]) or "Нет подтверждённых доступных записей о знаниях."
    if mode=="audit":
        return audit(db)
    records=rows(db,limit=100)
    return "Интеллект 7.0 · доступные последние свидетельства: "+str(len(records))+". Типы: "+", ".join(f"{k}: {v}" for k,v in sorted(Counter(f["kind"] for f in records).items()))+". Поиск по локальным тематическим понятиям; полная смысловая проверка не гарантируется."

def audit(db):
    for n,raw,h in db.execute("SELECT number,payload,checksum FROM lit_index"):
        if o.digest(raw)!=h:return f"Повреждён исходный литературный индекс: {n}."
        expected={evidence_id(n,f) for f in json.loads(raw)["records"]}
        actual=set()
        story=db.execute("SELECT story FROM omega_index WHERE number=?",(n,)).fetchone()
        if not story:return f"Нет источника: {n}."
        for eid,p,check in db.execute("SELECT id,payload,checksum FROM intellect_evidence WHERE chapter=?",(n,)):
            if o.digest(p)!=check:return f"Повреждено свидетельство: {n}."
            f=json.loads(p)
            if f["chapter"]!=n or story[0][f["start"]:f["start"]+len(f["quote"])]!=f["quote"]:return f"Нет точной цитаты: {n}."
            actual.add(eid)
        if actual!=expected:return f"Неполный индекс свидетельств: {n}."
    if db.execute("""SELECT 1 FROM intellect_assignments a LEFT JOIN intellect_evidence e ON e.id=a.evidence_id
        LEFT JOIN intellect_identity i ON i.id=a.identity_id WHERE e.id IS NULL OR i.id IS NULL""").fetchone():
        return "Есть осиротевшие назначения личности. Требуется ручная проверка."
    for ident,name,n,q,h in db.execute("SELECT id,name,origin_chapter,quote,checksum FROM intellect_identity"):
        source=db.execute("SELECT story FROM omega_index WHERE number=?",(n,)).fetchone()
        if not source or q not in source[0] or o.digest(o.dump([ident,name,n,q]))!=h:return "Повреждён источник отдельной личности."
    return "Индекс свидетельств и назначения личности: целостность подтверждена. Смысловая проверка ограничена."

def graph_notices(db,records):
    """Attach review signals only to nodes already visible in the selected graph."""
    notices=concerns(db,rows(db,limit=120))
    by_chapter=defaultdict(list)
    for x in notices:by_chapter[x["chapter"]].append(x["detail"])
    for node in records:
        key=node["key"]
        if key.startswith("c:") and key[2:].isdigit():
            row=db.execute("SELECT number FROM omega_index WHERE draft_id=?",(int(key[2:]),)).fetchone()
            if row and row[0] in by_chapter:
                node["review_warnings"]=by_chapter[row[0]][:3]
