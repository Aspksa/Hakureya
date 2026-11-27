"""Opt-in embeddings for published fiction. No automatic external requests.

The server alone performs a user-confirmed POST to Cloud.ru. Cached vectors
are reusable by local writer retrieval, bound to the exact scene fingerprint.
"""
import hashlib
import heapq
import math
import struct
import soul_omega as o
import soul_universe as u
import soul_evolution as ev

MODEL="Qwen/Qwen3-Embedding-0.6B"
DIM=1024
BATCH=8
ENDPOINT="https://foundation-models.api.cloud.ru/v1/embeddings"
FORMAT="<"+"f"*DIM

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS narrative_vectors(
        chapter INTEGER NOT NULL,seq INTEGER NOT NULL,model TEXT NOT NULL,source TEXT NOT NULL,
        vector BLOB NOT NULL,checksum TEXT NOT NULL,PRIMARY KEY(chapter,seq,model))""")
    db.execute("""CREATE TABLE IF NOT EXISTS narrative_query_vectors(
        digest TEXT PRIMARY KEY,vector BLOB NOT NULL,checksum TEXT NOT NULL,
        touched TEXT DEFAULT CURRENT_TIMESTAMP)""")

def pack(values):
    if not isinstance(values,list) or len(values)!=DIM or any(type(x) not in (int,float) or not math.isfinite(x) for x in values):
        raise ValueError("invalid embedding dimensions")
    length=math.hypot(*values)
    if not math.isfinite(length) or length<=0:raise ValueError("invalid embedding norm")
    return struct.pack(FORMAT,*(x/length for x in values))

def unpack(raw,checksum):
    if not isinstance(raw,bytes) or len(raw)!=4*DIM or hashlib.sha256(raw).hexdigest()!=checksum:raise ValueError("damaged embedding")
    values=struct.unpack(FORMAT,raw)
    if any(not math.isfinite(x) for x in values) or not .99<=math.hypot(*values)<=1.01:raise ValueError("invalid cached norm")
    return values

def parse(response,count):
    if not isinstance(response,dict) or not isinstance(response.get("data"),list) or len(response["data"])!=count:
        raise ValueError("embedding response count")
    items={}
    for entry in response["data"]:
        i=entry.get("index")
        if type(i) is not int or not 0<=i<count or i in items:raise ValueError("embedding response index")
        items[i]=pack(entry.get("embedding"))
    return [items[i] for i in range(count)]

def clean(db):
    db.execute("""DELETE FROM narrative_vectors WHERE NOT EXISTS(
        SELECT 1 FROM universe_scenes s JOIN universe_sources u ON u.chapter=s.chapter
        WHERE s.chapter=narrative_vectors.chapter AND s.seq=narrative_vectors.seq
          AND u.digest=narrative_vectors.source)""")

def missing(db):
    """Snapshot exactly the scenes that one explicitly authorized batch may send."""
    u.refresh(db,limit=20)
    clean(db)
    rows=db.execute("""SELECT s.chapter,s.seq,d.digest,s.body,s.start,s.end,i.arc,i.title,i.story,i.checksum,i.draft_id
       FROM universe_scenes s JOIN universe_sources d ON d.chapter=s.chapter JOIN omega_index i ON i.number=s.chapter
       LEFT JOIN narrative_vectors v ON v.chapter=s.chapter AND v.seq=s.seq AND v.model=? AND v.source=d.digest
       WHERE v.chapter IS NULL AND s.chapter NOT IN (SELECT chapter FROM universe_dirty)
       ORDER BY s.chapter,s.seq LIMIT ?""",(MODEL,BATCH)).fetchall()
    result=[]
    for n,seq,source,body,a,b,arc,title,story,h,did in rows:
        u.verified_source(db,n,arc,title,story,h,did)
        if story[a:b]!=body:raise ValueError("embedding source mismatch")
        result.append({"chapter":n,"seq":seq,"source":source,"body":body})
    return result

def store(db,items,response):
    vectors=parse(response,len(items))
    for item,raw in zip(items,vectors):
        row=db.execute("""SELECT d.digest,s.body FROM universe_scenes s JOIN universe_sources d ON d.chapter=s.chapter
          WHERE s.chapter=? AND s.seq=? AND s.chapter NOT IN (SELECT chapter FROM universe_dirty)""",(item["chapter"],item["seq"])).fetchone()
        if row!=(item["source"],item["body"]):raise ValueError("embedding source changed")
        db.execute("INSERT OR REPLACE INTO narrative_vectors VALUES(?,?,?,?,?,?)",
            (item["chapter"],item["seq"],MODEL,item["source"],raw,hashlib.sha256(raw).hexdigest()))

def status(db):
    indexed=db.execute("""SELECT COUNT(*) FROM narrative_vectors v JOIN universe_sources s ON s.chapter=v.chapter AND s.digest=v.source
       JOIN universe_scenes c ON c.chapter=v.chapter AND c.seq=v.seq WHERE v.model=? AND v.chapter NOT IN (SELECT chapter FROM universe_dirty)""",(MODEL,)).fetchone()[0]
    total=db.execute("SELECT COUNT(*) FROM universe_scenes").fetchone()[0]
    return {"model":MODEL,"indexed":indexed,"total":total,"batch":BATCH,"auto":False}

def query_key(query):
    return o.digest(o.dump([MODEL,query]))

def cached_query(db,query):
    row=db.execute("SELECT vector,checksum FROM narrative_query_vectors WHERE digest=?",(query_key(query),)).fetchone()
    return unpack(*row) if row else None

def save_query(db,query,response):
    raw=parse(response,1)[0]
    checksum=hashlib.sha256(raw).hexdigest()
    db.execute("INSERT OR REPLACE INTO narrative_query_vectors(digest,vector,checksum) VALUES(?,?,?)",(query_key(query),raw,checksum))
    db.execute("DELETE FROM narrative_query_vectors WHERE digest NOT IN (SELECT digest FROM narrative_query_vectors ORDER BY touched DESC,rowid DESC LIMIT 100)")
    return unpack(raw,checksum)

def candidates(db,vector,arc=None,public=True,limit=6):
    if not vector:return []
    sql="""SELECT v.chapter,v.seq,v.vector,v.checksum FROM narrative_vectors v
        JOIN universe_sources s ON s.chapter=v.chapter AND s.digest=v.source
        JOIN omega_index i ON i.number=v.chapter
        WHERE v.model=? AND v.chapter NOT IN (SELECT chapter FROM universe_dirty)"""
    args=[MODEL]
    if arc:sql+=" AND i.arc=?";args.append(arc)
    if public and ev.settings(db)[1]:sql+=" AND (v.chapter<=13 OR v.chapter IN (SELECT number FROM evolution_read))"
    def scores():
        for n,seq,raw,h in db.execute(sql,args):
            try:values=unpack(raw,h)
            except ValueError:continue # bad derived cache is never evidence
            score=sum(a*b for a,b in zip(vector,values))
            yield score,n,seq
    out=[]
    for score,n,seq in heapq.nlargest(max(1,min(30,limit)),scores()):
        row=db.execute("""SELECT s.title,s.body,s.start,s.end,i.arc,i.title,i.story,i.checksum,i.draft_id
          FROM universe_scenes s JOIN omega_index i ON i.number=s.chapter WHERE s.chapter=? AND s.seq=?""",(n,seq)).fetchone()
        if not row:continue
        u.verified_source(db,n,row[4],row[5],row[6],row[7],row[8])
        if row[6][row[2]:row[3]]!=row[1]:raise ValueError("vector scene mismatch")
        out.append({"chapter":n,"scene":seq,"title":row[0],"text":row[1],"start":row[2],"end":row[3],"score":round(score,6)})
    return out

def latest_vector(db,arc=None):
    sql="""SELECT v.vector,v.checksum FROM narrative_vectors v JOIN universe_sources s ON s.chapter=v.chapter AND s.digest=v.source
       JOIN omega_index i ON i.number=v.chapter WHERE v.model=? AND v.chapter NOT IN (SELECT chapter FROM universe_dirty)"""
    args=[MODEL]
    if arc:sql+=" AND i.arc=?";args.append(arc)
    sql+=" AND i.number=(SELECT MAX(number) FROM omega_index WHERE (? IS NULL OR arc=?))";args.extend((arc,arc))
    row=db.execute(sql+" ORDER BY v.chapter DESC,v.seq DESC LIMIT 1",args).fetchone()
    if not row:return None
    try:return unpack(*row)
    except ValueError:return None

def hybrid(db,query,vector=None,arc=None,public=True,limit=12):
    """Rank fusion; lexical results remain available when no valid vectors exist."""
    lexical=u.search(db,query,limit,public,arc)
    if vector is None:return lexical
    semantic=candidates(db,vector,arc,public,limit)
    scores={};items={}
    for weight,group in ((2,lexical),(1,semantic)):
        for i,r in enumerate(group):
            k=(r["chapter"],r["scene"]);items[k]=r;scores[k]=scores.get(k,0)+weight/(10+i)
    return [dict(items[k],score=round(scores[k],6)) for k in sorted(scores,key=lambda k:(-scores[k],-k[0],k[1]))[:limit]]
