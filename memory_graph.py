"""Local graph, backed exclusively by persisted records. No invented nodes."""
import re
import soul_chronicle
from contextlib import closing

KINDS = ("Запросы", "Знания", "Ответы", "Опыт", "Биография")
WORD = re.compile(r"[\w]{4,}", re.UNICODE)
STOP = {"который","которые","чтобы","этого","этот","этого","также","можно","your","with","this","that","have","from","about","сообщение","сохранено","локально","подключите"}

def init(db):
    db.execute("CREATE TABLE IF NOT EXISTS memory_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, kind INTEGER NOT NULL CHECK(kind IN (1,3)), content TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP)")

def tokens(s):
    return set(WORD.findall(s.lower())) - STOP

def snapshot(db, limit=5000):
    rows = db.execute("SELECT id,role,content,created FROM messages ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
    notes = db.execute("SELECT id,kind,content,created FROM memory_notes ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
    records = [{"key":f"m:{i}","group":0 if r=="user" else 2,"content":c,"created":t,"order":i} for i,r,c,t in reversed(rows) if r in ("user","assistant") and not (r=="assistant" and c=="Сообщение сохранено локально. Для ответа подключите Cloud.ru через меню аватара.")]
    records += [{"key":f"n:{i}","group":g,"content":c,"created":t,"order":i} for i,g,c,t in reversed(notes)]
    extra, chronicle_edges = soul_chronicle.graph(db,limit) if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='chronicle_diary'").fetchone() else ([],[])
    records += extra
    permanent,biography_edges,pending=soul_chronicle.constellation(db,limit) if db.execute("SELECT 1 FROM sqlite_master WHERE name=\'chronicle_diary\'").fetchone() else ([],[],None)
    records.sort(key=lambda n:(n["created"] or "",n["key"][0],n["order"]))
    # Preserve the original canon and a real pending draft even under memory pressure.
    budget=max(0,limit-len(permanent)-int(pending is not None))
    records=permanent+(records[-budget:] if budget else [])+([pending] if pending else [])
    edges=[]
    index={}
    last=None
    for n in records:
        key=n["key"]
        if key.startswith("m:"):
            if last is not None:
                edges.append({"a":last,"b":key,"kind":"chronology"})
            last=key
        # Do not create lexical bridges between fictional and real memory.
        if n["group"]==4:
            continue
        words=tokens(n["content"][:4000])
        counts={}
        for word in words:
            for prev in index.get(word,()):
                counts[prev]=counts.get(prev,0)+1
        for prev,count in sorted(counts.items(),key=lambda pair:(-pair[1],pair[0]))[:3]:
            if count>=2 and not any(e["a"]==prev and e["b"]==key for e in edges[-2:]):
                edges.append({"a":prev,"b":key,"kind":"keywords","shared":count})
        for word in words:
            recent=index.setdefault(word,[])
            recent.append(key)
            if len(recent)>8:
                del recent[0]
    visible={n["key"] for n in records}
    edges.extend(e for e in chronicle_edges+biography_edges if e["a"] in visible and e["b"] in visible)
    dedup={}
    for e in edges:
        dedup[(e["a"],e["b"],e["kind"])]=e
    edges=list(dedup.values())
    for n in records:
        n["label"]=" ".join(n["content"].split())[:54]
        del n["content"]
        del n["order"]
    total=db.execute("SELECT COUNT(*) FROM messages WHERE role='user' OR (role='assistant' AND content != ?)",("Сообщение сохранено локально. Для ответа подключите Cloud.ru через меню аватара.",)).fetchone()[0]+db.execute("SELECT COUNT(*) FROM memory_notes").fetchone()[0]
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='chronicle_diary'").fetchone():
        total+=db.execute("SELECT COUNT(*) FROM chronicle_diary").fetchone()[0]+db.execute("SELECT COUNT(*) FROM chronicle_drafts WHERE status='approved'").fetchone()[0]
    total+=len(permanent)+int(pending is not None)
    return {"records":records,"edges":edges,"total":total,"limited":total>len(records)}

def add_note(db,kind,content):
    if type(kind) is not int or kind not in (1,3) or not isinstance(content,str) or not content.strip() or len(content)>12000:
        raise ValueError("Invalid note")
    db.execute("INSERT INTO memory_notes(kind,content) VALUES(?,?)",(kind,content.strip()))
