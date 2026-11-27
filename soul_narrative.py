"""Narrative memory: exact-source extracts and review signals, never inferred canon.

One authoritative archive (omega_index + immutable approved drafts); the existing
Universe scene index supplies search. This cache does not invent characters, events,
relationships, or knowledge. It requires no network calls or external dependencies.
"""
import json
import re
from collections import Counter
import soul_omega as o
import soul_universe as u
import soul_evolution as ev

VERSION=1
CONTEXT_BYTES=10000
BATCH=20
# Linguistic cues are possible evidence, not proof: dialogue, negation, and
# hypothetical statements can contain the same words.
CUES={
    "promise":("обещ","клятв","покля","договор","обязал"),
    "goal":("решил","намерен","хотел","хотела","мечтал","планир"),
    "knowledge":("узнал","узнала","рассказ","сообщ","объясн","признал"),
    "clue":("тайн","загад","улика","неизвест","секрет"),
    "relation":("довер","любов","любил","любила","ревност","вражд","дружб"),
    "conflict":("ссор","спор","угроз","напал","предал","конфликт"),
    "magic":("заклин","магия","маги","энерги","силой","ограничен"),
    "time":("утром","вечером","ночью","через ","спустя ","на следующий день"),
    "location":("дворец","царств","храм","архив","вош","прибыл"),
    "consequence":("поэтому","вследствие","из-за ","в результате","после этого"),
    "emotion":("страх","боял","испуг","радост","гнев","смущ","одиночеств"),
}
def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS narrative_sources(
        chapter INTEGER PRIMARY KEY,digest TEXT NOT NULL,payload TEXT NOT NULL,checksum TEXT NOT NULL,
        scenes INTEGER NOT NULL,chars INTEGER NOT NULL,signals INTEGER NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS narrative_runs(
        attempt TEXT PRIMARY KEY,payload TEXT NOT NULL,checksum TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS narrative_maintenance(
        id INTEGER PRIMARY KEY CHECK(id=1),cursor INTEGER NOT NULL)""")
    db.execute("INSERT OR IGNORE INTO narrative_maintenance VALUES(1,0)")

def fingerprint(source):
    return str(VERSION)+":"+source

def excerpts(story,spans):
    """Extract representative sentences from each contiguous scene, preserving offsets."""
    result=[]
    for seq,a,b,body in spans:
        if story[a:b]!=body or not 0<=a<b<=len(story):raise ValueError("narrative source span")
        sentences=[]
        for m in re.finditer(r"[^.!?…\n]+(?:[.!?…]+[»”\"]?)?",body):
            raw=m[0];quote=raw.strip()
            if len(quote)<12 or quote.startswith("#"):continue
            offset=a+m.start()+len(raw)-len(raw.lstrip())
            # Limit long sentences without manufacturing a new one.
            quote=quote[:240].rstrip()
            low=o.normalized(quote)
            kinds=[k for k,markers in CUES.items() if any(x in low for x in markers)]
            sentences.append({"scene":seq,"start":offset,"end":offset+len(quote),"quote":quote,
                "signals":kinds,"speech":quote.startswith(("—","«","\""))})
        if not sentences:
            quote=body[:240];sentences=[{"scene":seq,"start":a,"end":a+len(quote),"quote":quote,"signals":[],"speech":False}]
        # Include the opening and closing sentence plus the most informative
        # candidate. No inference from mere co-occurrence.
        best=max(sentences,key=lambda x:(len(x["signals"]),len(x["quote"]),-x["start"]))
        selected={x["start"]:x for x in (sentences[0],best,sentences[-1])}
        result.extend(selected[k] for k in sorted(selected))
    return result

def build(db,n,source):
    row=db.execute("SELECT arc,title,story,checksum,draft_id FROM omega_index WHERE number=?",(n,)).fetchone()
    if not row:raise ValueError("narrative source missing")
    arc,title,story,h,did=row
    u.verified_source(db,n,arc,title,story,h,did)
    if source!=o.digest(o.dump([u.VERSION,title,story,h])):raise ValueError("narrative source fingerprint")
    spans=db.execute("SELECT seq,start,end,body FROM universe_scenes WHERE chapter=? ORDER BY seq",(n,)).fetchall()
    cursor=0
    for i,(seq,a,b,body) in enumerate(spans,1):
        if seq!=i or a!=cursor or not a<b<=len(story) or body!=story[a:b]:raise ValueError("narrative incomplete spans")
        cursor=b
    if cursor!=len(story):raise ValueError("narrative incomplete chapter")
    observations=excerpts(story,spans)
    payload=o.dump({"chapter":n,"arc":arc,"title":title,"extracts":observations})
    return (n,fingerprint(source),payload,o.digest(payload),len(spans),len(story),sum(bool(x["signals"]) for x in observations))

def refresh(db,limit=None,chapter=None):
    """The persisted source/dirty rows are the queue, surviving restart."""
    init(db)
    u.refresh(db,limit=limit,chapter=chapter)
    sql="""SELECT s.chapter,s.digest FROM universe_sources s LEFT JOIN narrative_sources n ON n.chapter=s.chapter
           WHERE s.chapter NOT IN (SELECT chapter FROM universe_dirty) AND (n.digest IS NULL OR n.digest!=?||s.digest)"""
    args=[str(VERSION)+":"]
    if chapter is not None:sql+=" AND s.chapter=?";args.append(chapter)
    sql+=" ORDER BY s.chapter"
    if limit is not None:sql+=" LIMIT ?";args.append(max(1,min(100,limit)))
    changed=0
    for n,source in db.execute(sql,args).fetchall():
        old=db.execute("SELECT digest FROM narrative_sources WHERE chapter=?",(n,)).fetchone()
        if old==(fingerprint(source),):continue
        row=build(db,n,source)
        db.execute("INSERT OR REPLACE INTO narrative_sources VALUES(?,?,?,?,?,?,?)",row)
        changed+=1
        if limit is not None and changed>=max(1,min(100,limit)):break
    db.execute("DELETE FROM narrative_sources WHERE chapter NOT IN (SELECT number FROM omega_index)")
    return changed

def read(db,n):
    row=db.execute("""SELECT r.digest,r.payload,r.checksum,s.digest,i.story,i.arc,i.title,i.checksum,i.draft_id
       FROM narrative_sources r JOIN universe_sources s ON s.chapter=r.chapter
       JOIN omega_index i ON i.number=r.chapter WHERE r.chapter=? AND r.chapter NOT IN (SELECT chapter FROM universe_dirty)""",(n,)).fetchone()
    if not row or row[0]!=fingerprint(row[3]) or o.digest(row[1])!=row[2]:raise ValueError("narrative cache missing or damaged")
    u.verified_source(db,n,row[5],row[6],row[4],row[7],row[8])
    data=json.loads(row[1])
    if data["chapter"]!=n or data["arc"]!=row[5] or data["title"]!=row[6]:raise ValueError("narrative cache identity")
    for x in data["extracts"]:
        if not 0<=x["start"]<x["end"]<=len(row[4]) or row[4][x["start"]:x["end"]]!=x["quote"]:raise ValueError("narrative quote mismatch")
    return data

def sweep(db,limit=BATCH):
    """Verify older derived records in a rotating batch; never repair the manuscript."""
    cursor=db.execute("SELECT cursor FROM narrative_maintenance WHERE id=1").fetchone()[0]
    batch=db.execute("SELECT chapter,digest FROM universe_sources WHERE chapter>? AND chapter NOT IN (SELECT chapter FROM universe_dirty) ORDER BY chapter LIMIT ?",(cursor,max(1,min(100,limit)))).fetchall()
    repaired=0
    for n,source in batch:
        expected=build(db,n,source)
        actual=db.execute("SELECT chapter,digest,payload,checksum,scenes,chars,signals FROM narrative_sources WHERE chapter=?",(n,)).fetchone()
        if actual!=expected:
            db.execute("INSERT OR REPLACE INTO narrative_sources VALUES(?,?,?,?,?,?,?)",expected)
            repaired+=1
    db.execute("UPDATE narrative_maintenance SET cursor=? WHERE id=1",(batch[-1][0] if batch else 0,))
    return repaired

def status(db):
    total=db.execute("SELECT COUNT(*) FROM omega_index").fetchone()[0]
    expected=13+db.execute("SELECT COUNT(*) FROM saga_arcs a JOIN chronicle_drafts d ON d.id=a.draft_id WHERE a.number IS NOT NULL AND d.status='approved'").fetchone()[0]
    indexed,scenes,chars,signals=db.execute("""SELECT COUNT(*),COALESCE(SUM(n.scenes),0),COALESCE(SUM(n.chars),0),COALESCE(SUM(n.signals),0)
       FROM narrative_sources n JOIN universe_sources s ON s.chapter=n.chapter JOIN omega_index i ON i.number=n.chapter
       WHERE n.chapter NOT IN (SELECT chapter FROM universe_dirty) AND n.digest=?||s.digest""",(str(VERSION)+":",)).fetchone()
    evidence=db.execute("SELECT COUNT(*) FROM intellect_evidence").fetchone()[0]
    return {"published":expected,"archive":total,"indexed":indexed,"pending":max(0,expected-indexed),
            "scenes":scenes,"chars":chars,"signals":signals,"evidence":evidence,"method":"local_extractive",
            "vector_enabled":False}

def audit(db):
    if status(db)["published"]!=status(db)["archive"]:return "Архив публикаций неполон; требуется восстановление."
    result=u.report(db,"audit")
    if "целостность индекса сцен подтверждена" not in result.casefold():return result
    for n,source in db.execute("SELECT chapter,digest FROM universe_sources"):
        if db.execute("SELECT chapter,digest,payload,checksum,scenes,chars,signals FROM narrative_sources WHERE chapter=?",(n,)).fetchone()!=build(db,n,source):
            return f"Литературная память неполна или повреждена: часть {n}."
    if status(db)["pending"]:return "Есть необработанные публикации."
    return "Целостность литературной памяти подтверждена. Смысловые метки остаются эвристиками, не фактами."

def repair(db):
    db.execute("SAVEPOINT narrative_repair")
    try:
        u.rebuild_publication_index(db)
        db.execute("DELETE FROM narrative_sources")
        count=refresh(db)
        db.execute("RELEASE narrative_repair")
        return count
    except BaseException:
        db.execute("ROLLBACK TO narrative_repair");db.execute("RELEASE narrative_repair");raise

def scope(arc):
    return None if arc=="future" else arc

def prepare(db,plan):
    """One bounded packet: every approved part of the current logical chapter,
    relevant exact passages from the entire permitted archive, source IDs."""
    refresh(db)
    arc=plan["arc"]
    if status(db)["published"]!=status(db)["archive"]:raise ValueError("publication archive incomplete")
    novel=plan.get("novel",{})
    theme=plan.get("universe") or plan.get("director") or {}
    query=" ".join(str(x) for x in (theme.get("title",""),theme.get("guide",""),theme.get("lens","")[:160],plan.get("guide","")[:180],novel.get("ending","")[-500:]))
    current=[]
    if novel.get("part",1)>1:
        import soul_novel
        for row in soul_novel.published_group(db,novel["start"]):
            if row["arc"]!=arc:raise ValueError("cross-arc chapter memory")
            data=read(db,row["number"])
            # Always preserve at least one extract per part, so the opening of a
            # 20-part chapter does not disappear behind the last two endings.
            entries=data["extracts"]
            best=max(entries,key=lambda x:(len(x["signals"]),len(x["quote"])),default=None)
            if best:
                current.append({"chapter":row["number"],"scene":best["scene"],"start":best["start"],
                    "quote":best["quote"][:120],"signals":best["signals"][:3]})
    current_numbers={x["chapter"] for x in current}
    recall=[]
    for r in u.search(db,query,16,False,scope(arc)):
        if r["chapter"] in current_numbers or any(x["chapter"]==r["chapter"] for x in recall):continue
        quote=u.focused_excerpt(r["text"],query,330)
        recall.append({"chapter":r["chapter"],"scene":r["scene"],"start":r["start"]+r["text"].index(quote),"quote":quote})
        if len(recall)>=6:break
    # Prefer the same evidence already used by the evidence-based character brain.
    profiles=[]
    for f in plan.get("intellect7",{}).get("profiles",[]):
        n=f["chapter"]
        row=db.execute("SELECT arc,story FROM omega_index WHERE number=?",(n,)).fetchone()
        if row and (scope(arc) is None or row[0]==arc) and f.get("quote") and f["quote"] in row[1]:
            profiles.append({k:f[k] for k in ("chapter","subject","kind","value","quote")})
    data={"scope":arc,"current":current,"recall":recall,"profiles":profiles[:6],
          "method":"exact_extracts_and_lexical_signals_not_confirmed_facts"}
    while len(o.dump(data).encode("utf-8"))>CONTEXT_BYTES:
        if data["profiles"]:data["profiles"].pop()
        elif data["recall"]:data["recall"].pop()
        else:
            # Never silently drop a whole current part; shorten all extracts.
            if all(len(x["quote"])<=40 for x in current):raise ValueError("chapter memory exceeds cap")
            for x in current:x["quote"]=x["quote"][:max(40,len(x["quote"])//2)]
    plan["narrative"]=data
    return data

def record(db,attempt,plan):
    data=plan.get("narrative")
    if data is None:return
    # Store only source coordinates, not an additional copy of the manuscript.
    refs=[{"chapter":r["chapter"],"scene":r["scene"],"start":r["start"],"length":len(r["quote"])}
          for r in data["current"]+data["recall"]]
    payload=o.dump({"scope":data["scope"],"refs":refs,"bytes":len(o.dump(data).encode("utf-8"))})
    db.execute("INSERT INTO narrative_runs VALUES(?,?,?)",(attempt,payload,o.digest(payload)))

def last_run(db,public=True):
    row=db.execute("SELECT payload,checksum FROM narrative_runs ORDER BY attempt DESC LIMIT 1").fetchone()
    if not row:return None
    if o.digest(row[0])!=row[1]:raise ValueError("narrative trace checksum")
    data=json.loads(row[0])
    if public:data["refs"]=[r for r in data["refs"] if r["chapter"]<=13 or ev.readable(db,r["chapter"])]
    return data

def summary(db,n,kind="chapter",public=True):
    """Extractive chapter/volume digest; exact citations, no cloud."""
    refresh(db)
    import soul_novel
    if kind=="chapter":
        nums=[r["number"] for r in soul_novel.group_for(db,n)] or [n]
    elif kind=="volume":
        nums=[k for k, in db.execute("SELECT number FROM omega_index ORDER BY number") if o.volume(k)==n]
    else:raise ValueError("summary kind")
    result=[]
    for k in nums:
        if public and k>13 and not ev.readable(db,k):continue
        data=read(db,k)
        if not data["extracts"]:continue
        best=max(data["extracts"],key=lambda x:(len(x["signals"]),len(x["quote"])))
        result.append(f"Часть {k}, сцена {best['scene']} — «{best['quote']}»")
    return "Выборочные цитаты, не полный пересказ:\n"+"\n".join(result) if result else "Нет доступных источников."

def report(db):
    s=status(db)
    return (f"Литературная память: {s['indexed']}/{s['published']} опубликованных частей; "
            f"в очереди {s['pending']}; {s['scenes']} сцен, {s['chars']} знаков. "
            f"Свидетельства: {s['evidence']}; фрагменты с возможными смысловыми признаками: {s['signals']}. "
            "Локальный поиск и цитаты; векторный анализ не подключён.")
