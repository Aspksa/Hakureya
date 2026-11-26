"""Offline book reader. No generation, no skipped or rewritten source text."""
import re
import hashlib
import soul_saga
import soul_omega

PAGE_SIZE=1500

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS book_reader(
       id INTEGER PRIMARY KEY CHECK(id=1), chapter INTEGER NOT NULL,
       page INTEGER NOT NULL, source_hash TEXT NOT NULL, active INTEGER NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS book_reader_position(
       id INTEGER PRIMARY KEY CHECK(id=1), chapter INTEGER NOT NULL, offset INTEGER NOT NULL, source_hash TEXT NOT NULL)""")

    db.execute("CREATE TABLE IF NOT EXISTS reader_anchor(id INTEGER PRIMARY KEY CHECK(id=1), chapter INTEGER NOT NULL, source_hash TEXT NOT NULL, offset INTEGER NOT NULL,text TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS reader_migrations(id INTEGER PRIMARY KEY,chapter INTEGER NOT NULL,page INTEGER NOT NULL,source_hash TEXT NOT NULL)")
    db.execute("""CREATE TABLE IF NOT EXISTS reader_coverage(
       chapter INTEGER NOT NULL, source_hash TEXT NOT NULL, start INTEGER NOT NULL, end INTEGER NOT NULL,
       PRIMARY KEY(chapter,source_hash,start))""")

def anchor(db,part,offset):
    text=part["body"][offset:offset+100]
    db.execute("INSERT OR REPLACE INTO reader_anchor VALUES(1,?,?,?,?)",(part["number"],part["hash"],offset,text))

def recover_bookmark(db,row,loaded):
    # Old editions have no textual anchor: restart the same chapter, never skip unseen text.
    n,p,check,_=row
    part=source(db,n)
    saved=db.execute("SELECT text FROM reader_anchor WHERE chapter=?",(n,)).fetchone()
    offset=0
    if saved and saved[0] and part["body"].count(saved[0])==1:
        offset=part["body"].index(saved[0])
    db.execute("INSERT INTO reader_migrations(chapter,page,source_hash) VALUES(?,?,?)",(n,p,check))
    pages,new_check=loaded
    raw_offset=offset+part["prefix"]
    page=0;boundary=0
    for i,chunk in enumerate(pages):
        page=i;boundary+=len(chunk)
        if raw_offset<boundary:break
    db.execute("INSERT OR REPLACE INTO book_reader VALUES(1,?,?,?,1)",(n,page,new_check))
    db.execute("INSERT OR REPLACE INTO book_reader_position VALUES(1,?,?,?)",(n,offset,part["hash"]))
    anchor(db,part,offset)
    return f"Глава {n} · Страница {page+1}/{len(pages)}\n\n"+pages[page].strip()+"\n\nИздание обновилось. Позиция восстановлена по тексту либо с начала главы."

def cover(db,n,check,start,end,length):
    # Only continuous displayed ranges qualify; opening the last page is not sufficient.
    if not 0<=start<end<=length:return
    rows=db.execute("SELECT start,end FROM reader_coverage WHERE chapter=? AND source_hash=? AND end>=? AND start<=?",(n,check,start,end)).fetchall()
    for a,b in rows:start=min(start,a);end=max(end,b)
    db.execute("DELETE FROM reader_coverage WHERE chapter=? AND source_hash=? AND end>=? AND start<=?",(n,check,start,end))
    db.execute("INSERT INTO reader_coverage VALUES(?,?,?,?)",(n,check,start,end))
    if start==0 and end==length:
        import soul_evolution
        soul_evolution.mark_read(db,n)

def paginate(text, size=PAGE_SIZE):
    """Keep all source characters, prefer paragraph then sentence/word boundaries."""
    pages=[]; start=0
    while start<len(text):
        end=min(len(text),start+size)
        if end<len(text):
            window=text[start:end]
            floor=size//2
            candidates=[m.end() for m in re.finditer(r"\n\n+|[.!?…][»”]?\s+",window) if m.end()>=floor]
            paragraphs=[m.end() for m in re.finditer(r"\n\n+",window) if m.end()>=floor]
            if paragraphs:end=start+paragraphs[-1]
            elif candidates:end=start+candidates[-1]
            else:
                spaces=[m.end() for m in re.finditer(r"\s+",window) if m.end()>=floor]
                if spaces:end=start+spaces[-1]
        pages.append(text[start:end]);start=end
    return pages or [""]

def bookmark(db):
    return db.execute("SELECT chapter,page,source_hash,active FROM book_reader WHERE id=1").fetchone()

def active(db):
    row=bookmark(db)
    return bool(row and row[3])

def load(db,n):
    import soul_chronicle
    if not soul_chronicle.canon_ok(db):return None
    result=soul_saga.read(db,n)
    if not result.startswith(("Художественный канон\n\n","Художественная глава ")):return None
    # Legacy reader output is preserved for compatibility; pagination never regenerates it.
    return paginate(result),hashlib.sha256(result.encode("utf-8")).hexdigest()

def latest(db):
    return db.execute("SELECT COALESCE(MAX(number),13) FROM saga_arcs WHERE number IS NOT NULL").fetchone()[0]

def display(db,n,p,loaded=None):
    loaded=loaded or load(db,n)
    if loaded is None:return "Глава недоступна или повреждена. Закладка сохранена."
    pages,check=loaded
    if not 0<=p<len(pages):return "Такой страницы нет. Закладка сохранена."
    db.execute("DELETE FROM book_reader_position")
    db.execute("INSERT OR REPLACE INTO book_reader VALUES(1,?,?,?,1)",(n,p,check))
    soul_omega.mark(db,n)
    part=source(db,n)
    start=sum(map(len,pages[:p]))-part["prefix"]
    end=start+len(pages[p])
    anchor(db,part,max(0,start))
    cover(db,n,part["hash"],max(0,start),min(len(part["body"]),end),len(part["body"]))
    end="\n\nВсе опубликованные главы прочитаны. Новые появятся после утверждения." if n==latest(db) and p==len(pages)-1 else ""
    return f"Глава {n} · Страница {p+1}/{len(pages)}\n\n"+pages[p].strip()+end

def move(db,action,n=None):
    import soul_chronicle
    if not soul_chronicle.canon_ok(db):return "Целостность исходной летописи нарушена; закладка сохранена."
    row=bookmark(db)
    if action=="pause":
        if row:
            db.execute("UPDATE book_reader SET active=0 WHERE id=1")
            return f"Закладка сохранена: глава {row[0]}, страница {row[1]+1}."
        return "Чтение ещё не начато."
    if action=="where":
        if not row:return "Чтение ещё не начато."
        exact=db.execute("SELECT offset FROM book_reader_position WHERE chapter=?",(row[0],)).fetchone()
        return f"Глава {row[0]}, позиция текста {exact[0]}." if exact else f"Глава {row[0]}, страница {row[1]+1}."
    if action=="start":return display(db,1,0)
    if action=="chapter":return display(db,n,0)
    if action=="latest":return display(db,latest(db),0)
    if row is None:return display(db,soul_omega.bookmark(db),0)
    chapter,p,check,_=row
    loaded=load(db,chapter)
    if loaded is None:return "Сохранённая глава недоступна. Закладка сохранена."
    pages,new_check=loaded
    if check!=new_check or p>=len(pages):
        if action=="resume" and 1<=chapter<=13:return recover_bookmark(db,row,loaded)
        return "Текст сохранённой главы изменился. Откройте её заново; закладка сохранена."
    if action=="resume":
        # Preserve the exact adaptive bookmark when reopening through the old chat command.
        pos=db.execute("SELECT chapter FROM book_reader_position WHERE id=1").fetchone()
        if pos and pos[0]==chapter:
            db.execute("UPDATE book_reader SET active=1 WHERE id=1")
            return f"Глава {chapter} · Страница {p+1}/{len(pages)}\n\n"+pages[p].strip()
        return display(db,chapter,p,loaded)
    if action=="next":
        if p+1<len(pages):return display(db,chapter,p+1,loaded)
        if chapter>=latest(db):return "Вы на последней опубликованной странице. Закладка сохранена."
        return display(db,chapter+1,0)
    if action=="back":
        if p>0:return display(db,chapter,p-1,loaded)
        if chapter==1:return "Вы на первой странице книги."
        prev=load(db,chapter-1)
        if prev is None:return "Предыдущая глава недоступна. Закладка сохранена."
        return display(db,chapter-1,len(prev[0])-1,prev)
    raise ValueError("unknown reader action")

def view(db):
    """Render exactly the existing bookmark; no implicit move or model request."""
    row=bookmark(db)
    if not row or not row[3]:return None
    n,p,check,_=row
    loaded=load(db,n)
    if loaded is None or loaded[1]!=check or not 0<=p<len(loaded[0]):return None
    pages=loaded[0]
    index=db.execute("SELECT title FROM omega_index WHERE number=?",(n,)).fetchone()
    if not index:return None
    body=pages[p]
    if p==0:
        # Strip only known wrapper headings; original stored text and pagination remain unchanged.
        if n<=13:body=re.sub(r"^Художественный канон\n\n### Глава [IVX]+\. [^\n]+\n*", "",body,count=1)
        else:body=re.sub(r"^Художественная глава [0-9]+\. [^\n]+\n[^\n]+\n\n", "",body,count=1)
    volume=soul_omega.volume(n)
    count=db.execute("SELECT COUNT(*) FROM omega_index WHERE number BETWEEN ? AND ?",
        (1 if volume==1 else 14+(volume-2)*12,13 if volume==1 else 25+(volume-2)*12)).fetchone()[0]
    ordinal=n if volume==1 else (n-14)%12+1
    result={"chapter":n,"title":index[0],"volume":volume,"page":p+1,"pages":len(pages),
      "text":body.strip(),"chapter_progress":(p+1)/len(pages),
      "volume_progress":min(1,(ordinal-1+(p+1)/len(pages))/max(1,count)),
      "can_back":n>1 or p>0,"can_next":n<latest(db) or p+1<len(pages),
      "last_published":n==latest(db) and p+1==len(pages)}
    result["document"]=document(db)
    return result


def source(db,n):
    """Use the approved immutable source; remove only the known technical wrapper."""
    raw=soul_saga.read(db,n)
    if not raw.startswith(("Художественный канон\n\n","Художественная глава ")):raise ValueError("chapter unavailable")
    if n<=13:
        match=re.match(r"^Художественный канон\n\n### Глава [IVX]+\. [^\n]+\n*",raw)
    else:
        match=re.match(r"^Художественная глава [0-9]+\. [^\n]+\n[^\n]+\n\n",raw)
    prefix=match.end() if match else 0
    body=raw[prefix:]
    title=db.execute("SELECT title FROM omega_index WHERE number=?",(n,)).fetchone()[0]
    return {"number":n,"title":title,"body":body,"hash":hashlib.sha256(body.encode("utf-8")).hexdigest(),"prefix":prefix,"raw":raw}

def document(db):
    """Return a logical chapter of contiguous, checked published parts, not drafts."""
    row=bookmark(db)
    if not row or not row[3]:return None
    n,p,check,_=row
    import soul_novel
    group=soul_novel.group_for(db,n)
    nums=[x["number"] for x in group] if group else [n]
    sources=[source(db,k) for k in nums]
    text="";segments=[]
    for part in sources:
        if text:text+="\n\n"
        start=len(text);text+=part["body"]
        segments.append({"number":part["number"],"start":start,"end":len(text),"hash":part["hash"]})
    part=sources[nums.index(n)];segment=segments[nums.index(n)]
    if hashlib.sha256(part["raw"].encode("utf-8")).hexdigest()!=check:raise ValueError("source changed")
    pos=db.execute("SELECT chapter,offset,source_hash FROM book_reader_position WHERE id=1").fetchone()
    if pos and pos[0]==n:
        if pos[2]!=part["hash"] or not 0<=pos[1]<=len(part["body"]):raise ValueError("reader position damaged")
        offset=pos[1]
    else:
        legacy=paginate(part["raw"])
        offset=max(0,min(len(part["body"]),sum(map(len,legacy[:p]))-part["prefix"]))
    volume=soul_omega.volume(nums[0])
    total=db.execute("SELECT COUNT(*) FROM omega_index WHERE number BETWEEN ? AND ?",(1 if volume==1 else 14+(volume-2)*12,13 if volume==1 else 25+(volume-2)*12)).fetchone()[0]
    return {"chapter":nums[0],"last_chapter":nums[-1],"title":sources[0]["title"],"volume":volume,"text":text,
      "hash":hashlib.sha256(text.encode("utf-8")).hexdigest(),"offset":segment["start"]+offset,
      "segments":segments,"latest":latest(db),"volume_count":total,
      "volume_ordinal":nums[0] if volume==1 else (nums[0]-14)%12+1,
      "parts":len(nums),"epoch":1+(volume-1)//8}

def position(db,hash_value,start,end):
    """Persist code-point offset, also keep the old chapter/page bookmark compatible."""
    doc=document(db)
    if not doc:raise ValueError("reader source changed")
    maximum=len(doc["text"])
    if hash_value!=doc["hash"]:
        # Accept only a verified previously published prefix, never a changed manuscript.
        maximum=next((seg["end"] for seg in doc["segments"][:-1] if hashlib.sha256(doc["text"][:seg["end"]].encode("utf-8")).hexdigest()==hash_value),-1)
        if maximum<0:raise ValueError("reader source changed")
    if type(start) is not int or type(end) is not int or not 0<=start<=end<=maximum:raise ValueError("invalid reader offset")
    # Separators belong to the previous source; offsets remain stable after a new part is appended.
    segment=next((x for x in reversed(doc["segments"]) if x["start"]<=start),doc["segments"][0])
    n=segment["number"];part=source(db,n);offset=min(len(part["body"]),start-segment["start"])
    raw_offset=part["prefix"]+offset
    pages=paginate(part["raw"]);p=0;boundary=0
    for i,page in enumerate(pages):
        p=i;boundary+=len(page)
        if raw_offset<boundary:break
    check=hashlib.sha256(part["raw"].encode("utf-8")).hexdigest()
    db.execute("INSERT OR REPLACE INTO book_reader VALUES(1,?,?,?,1)",(n,p,check))
    db.execute("INSERT OR REPLACE INTO book_reader_position VALUES(1,?,?,?)",(n,offset,part["hash"]))
    soul_omega.mark(db,n)
    anchor(db,part,offset)
    for seg in doc["segments"]:
        a=max(start,seg["start"]);b=min(end,seg["end"])
        if a<b:cover(db,seg["number"],seg["hash"],a-seg["start"],b-seg["start"],seg["end"]-seg["start"])
    return document(db)

def adjacent(db,direction):
    doc=document(db)
    if not doc:return move(db,"resume")
    if direction=="advance":
        n=doc["last_chapter"]+1
        if n>latest(db):return "Продолжение ещё не опубликовано."
        return display(db,n,0)
    n=doc["chapter"]-1
    if n<1:return "Вы на первой странице книги."
    loaded=load(db,n)
    if not loaded:return "Предыдущая глава недоступна."
    reply=display(db,n,len(loaded[0])-1,loaded)
    prev=document(db)
    if prev:
        pos=len(prev["text"])
        position(db,prev["hash"],pos,pos)
    return reply
