"""Local graph, backed exclusively by persisted records. No invented nodes."""
import re
import soul_chronicle
import soul_omega
from contextlib import closing

KINDS = ("Запросы", "Знания", "Ответы", "Опыт", "Биография")
WORD = re.compile(r"[\w]{4,}", re.UNICODE)
STOP = {"который","которые","чтобы","этого","этот","этого","также","можно","your","with","this","that","have","from","about","сообщение","сохранено","локально","подключите"}

def init(db):
    db.execute("CREATE TABLE IF NOT EXISTS memory_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, kind INTEGER NOT NULL CHECK(kind IN (1,3)), content TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP)")

    db.execute("CREATE TABLE IF NOT EXISTS graph_slots (key TEXT PRIMARY KEY, group_id INTEGER NOT NULL, slot INTEGER NOT NULL, UNIQUE(group_id,slot))")

def assign_slots(db,records):
    # Existing stars keep their local lattice cell, even when old records leave the view.
    existing={}
    for start in range(0,len(records),400):
        keys=[n["key"] for n in records[start:start+400]]
        if keys:
            rows=db.execute("SELECT key,group_id,slot FROM graph_slots WHERE key IN ("+",".join("?" for _ in keys)+")",keys)
            existing.update({key:(g,slot) for key,g,slot in rows})
    missing=[n for n in records if n["key"] not in existing]
    if missing:
        # Serialize allocation across HTTP readers via SQLite's write transaction.
        db.execute("INSERT OR IGNORE INTO graph_slots(key,group_id,slot) SELECT ?,?,COALESCE(MAX(slot),-1)+1 FROM graph_slots WHERE group_id=?",(missing[0]["key"],missing[0]["group"],missing[0]["group"]))
        for n in missing:
            db.execute("INSERT OR IGNORE INTO graph_slots(key,group_id,slot) SELECT ?,?,COALESCE(MAX(slot),-1)+1 FROM graph_slots WHERE group_id=?",(n["key"],n["group"],n["group"]))
            existing[n["key"]]=db.execute("SELECT group_id,slot FROM graph_slots WHERE key=?",(n["key"],)).fetchone()
    for n in records:
        n["slot"]=existing[n["key"]][1]

def tokens(s):
    return set(WORD.findall(s.lower())) - STOP

def reconcile_actors(records,edges):
    """Resolve duplicate visual representations of exact known names, not fuzzy identities."""
    import soul_intelligence as li
    import soul_destiny as de
    known={li.norm(name):"destiny:actor:"+key for key,name,_ in de.CAST}
    present={n["key"] for n in records}
    alias={}
    for n in records:
        k=n["key"]
        if not k.startswith(("actor:","lit:actor:","infinite:character:")):continue
        name=li.norm(n["content"])
        target=li.actor_key(name)
        if target.startswith("lit:actor:"):
            named=known.get(name)
            target=named if named in present else target
        # The canonical key stays the same even if the earlier Omega layer leaves the viewport.
        alias[k]=target
    result={}
    for n in records:
        k=n["key"];target=alias.get(k,k)
        if target!=k:
            n={**n,"key":target}
            if target.startswith("lit:actor:"):
                n["kind"]="lit_character";n["infinite_group"]=target
        group=n.get("infinite_group")
        if group in alias:n={**n,"infinite_group":alias[group]}
        if target not in result or k==target:result[target]=n
    links=[]
    for e in edges:
        a,b=alias.get(e["a"],e["a"]),alias.get(e["b"],e["b"])
        if a!=b:links.append({**e,"a":a,"b":b})
    return list(result.values()),links

def snapshot(db, limit=5000):
    limit=max(14,min(5000,int(limit)))
    rows = db.execute("SELECT id,role,content,created FROM messages ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
    notes = db.execute("SELECT id,kind,content,created FROM memory_notes ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
    records = [{"key":f"m:{i}","group":0 if r=="user" else 2,"content":c,"created":t,"order":i} for i,r,c,t in reversed(rows) if r in ("user","assistant") and not (r=="assistant" and c=="Сообщение сохранено локально. Для ответа подключите Cloud.ru через меню аватара.")]
    records += [{"key":f"n:{i}","group":g,"content":c,"created":t,"order":i} for i,g,c,t in reversed(notes)]
    extra, chronicle_edges = soul_chronicle.graph(db,limit) if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='chronicle_diary'").fetchone() else ([],[])
    records += extra
    permanent,biography_edges,pending=soul_chronicle.constellation(db,limit) if db.execute("SELECT 1 FROM sqlite_master WHERE name='chronicle_diary'").fetchone() else ([],[],None)
    records.sort(key=lambda n:(n["created"] or "",n["key"][0],n["order"]))
    # Preserve the original canon and a real pending draft even under memory pressure.
    # Deduplicate before allocating slots. Service/canon hubs take priority over decorative detail.
    permanent,biography_edges=reconcile_actors(permanent,biography_edges)
    unique={n["key"]:n for n in permanent}
    permanent=list(unique.values())
    def priority(n):
        k=n["key"];kind=n.get("kind","")
        if k.startswith("canon:"):return 0
        if k.startswith("brain:") or k=="lit:db":return 1
        if k.startswith(("character:","guardian:","era:","arc:")) or kind.endswith("_root"):return 2
        if kind in ("book","book_segment","novel_epoch","director_saga","dynasty_saga"):return 3
        return 4
    total_permanent=len(permanent)
    permanent=sorted(permanent,key=priority)[:max(0,limit-int(pending is not None))]
    budget=max(0,limit-len(permanent)-int(pending is not None))
    keys={n["key"] for n in permanent}
    candidates=[n for n in records if n["key"] not in keys]
    records=permanent+(candidates[-budget:] if budget else [])+([pending] if pending else [])
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
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='omega_index'").fetchone():
        chapter_map={("canon:"+str(n) if did is None else "c:"+str(did)):(arc,n) for n,arc,did in db.execute("SELECT number,arc,draft_id FROM omega_index")}
        volume_counts={}
        for _,num in chapter_map.values():
            v=soul_omega.volume(num);volume_counts[v]=volume_counts.get(v,0)+1
        completed_volumes={v for v,count in volume_counts.items() if count==(13 if v==1 else soul_omega.VOLUME_SIZE)}
        for n in records:
            pair=chapter_map.get(n["key"])
            if pair:
                arc,num=pair
                n.update(sector=arc,book=soul_omega.volume(num),chapter_slot=num-1 if num<=13 else (num-14)%12)
            elif n["key"] in tuple(f"realm:{i}" for i in range(1,10)):
                n.update(destiny_topic=n["key"],destiny_slot=-1)
            elif n["key"].startswith("era:") and n["key"][4:] in soul_omega.ARCS:
                n.update(sector=n["key"][4:],book=0,chapter_slot=0)
            elif n["key"].startswith("segment:"):
                _,arc,v=n["key"].split(":")
                n.update(sector=arc,book=int(v),chapter_slot=-1,volume_complete=int(v) in completed_volumes)
            elif n["key"].startswith("book:") and n["key"][5:].isdigit():
                n["volume_complete"]=int(n["key"][5:]) in completed_volumes
    # Real local quality notices on the pending draft, not semantic contradiction detection.
    if pending and pending in records:
        did=int(pending["key"].split(":")[1])
        warnings=[]
        try:
            import soul_romance, soul_immortal, soul_infinite
            meta=soul_omega.metadata(db,did)
            report=soul_romance.report(db,did)
            for value in (meta,report):
                if value:warnings.extend(value.get("warnings",[]))
            for mod in (soul_immortal,soul_infinite):
                item=mod.read(db,did)
                if item:warnings.extend(item.get("quality",{}).get("warnings",[]))
            import soul_dynasty
            dynasty=soul_dynasty.read(db,did)
            if dynasty and dynasty["target"] and not dynasty["step"]:warnings.append("Этап Династии ещё не подтверждён")
            if dynasty and dynasty.get("warning"):warnings.append(dynasty["warning"])
            editor=soul_immortal.editor_report(db,did)
            if editor:
                for note in editor.get("notes",[]):
                    if note.get("kind") in ("canon","logic"):
                        warnings.append("Редактор (оценка модели): "+str(note.get("issue","")))
                if editor.get("verdict")=="revise":warnings.append("Редактор (оценка модели): нужна доработка")
        except (ValueError,TypeError,KeyError,IndexError):
            warnings.append("Не удалось прочитать локальный отчёт проверки")
        pending["review_warnings"]=list(dict.fromkeys(w[:160] for w in warnings if isinstance(w,str)))[:6]
    try:
        import soul_intellect
        soul_intellect.refresh(db)
        soul_intellect.graph_notices(db,records)
    except (ValueError,TypeError,KeyError,IndexError,sqlite3.Error):
        pass
    assign_slots(db,records)
    visible={n["key"] for n in records}
    edges.extend(e for e in chronicle_edges+biography_edges if e["a"] in visible and e["b"] in visible)
    dedup={}
    for e in edges:
        dedup[(e["a"],e["b"],e["kind"])]=e
    edges=list(dedup.values())
    # Preserve structural links before lexical edges, with a hard cap.
    edges.sort(key=lambda e:e["kind"]=="keywords")
    omitted_edges=max(0,len(edges)-10000)
    edges=edges[:10000]
    for n in records:
        n["label"]=" ".join(n["content"].split())[:54]
        del n["content"]
        del n["order"]
    total=db.execute("SELECT COUNT(*) FROM messages WHERE role='user' OR (role='assistant' AND content != ?)",("Сообщение сохранено локально. Для ответа подключите Cloud.ru через меню аватара.",)).fetchone()[0]+db.execute("SELECT COUNT(*) FROM memory_notes").fetchone()[0]
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='chronicle_diary'").fetchone():
        total+=db.execute("SELECT COUNT(*) FROM chronicle_diary").fetchone()[0]+db.execute("SELECT COUNT(*) FROM chronicle_drafts WHERE status='approved'").fetchone()[0]
    total+=total_permanent+int(pending is not None)
    publication=None
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='omega_index'").fetchone():
        last=db.execute("SELECT number,arc,draft_id FROM omega_index WHERE draft_id IS NOT NULL ORDER BY number DESC LIMIT 1").fetchone()
        if last:
            n,arc,did=last;v=soul_omega.volume(n)
            import soul_evolution
            publication={"number":n,"key":f"c:{did}","volume":v,"segment":f"segment:{arc}:{v}","details":soul_evolution.readable(db,n),
                "first":(n-14)%12==0,"complete":(n-14)%12==11,"epoch":1+(v-1)//8}
    return {"records":records,"edges":edges,"total":total,"limited":total>len(records),"publication":publication,"omitted_edges":omitted_edges}

def add_note(db,kind,content):
    if type(kind) is not int or kind not in (1,3) or not isinstance(content,str) or not content.strip() or len(content)>12000:
        raise ValueError("Invalid note")
    db.execute("INSERT INTO memory_notes(kind,content) VALUES(?,?)",(kind,content.strip()))
