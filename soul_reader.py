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
    db.execute("INSERT OR REPLACE INTO book_reader VALUES(1,?,?,?,1)",(n,p,check))
    soul_omega.mark(db,n)
    if p==len(pages)-1:
        import soul_evolution
        soul_evolution.mark_read(db,n)
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
        return f"Глава {row[0]}, страница {row[1]+1}." if row else "Чтение ещё не начато."
    if action=="start":return display(db,1,0)
    if action=="chapter":return display(db,n,0)
    if action=="latest":return display(db,latest(db),0)
    if row is None:return display(db,soul_omega.bookmark(db),0)
    chapter,p,check,_=row
    loaded=load(db,chapter)
    if loaded is None:return "Сохранённая глава недоступна. Закладка сохранена."
    pages,new_check=loaded
    if check!=new_check or p>=len(pages):
        return "Текст сохранённой главы изменился. Откройте её заново; закладка сохранена."
    if action=="resume":return display(db,chapter,p,loaded)
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
    return {"chapter":n,"title":index[0],"volume":volume,"page":p+1,"pages":len(pages),
      "text":body.strip(),"chapter_progress":(p+1)/len(pages),
      "volume_progress":min(1,(ordinal-1+(p+1)/len(pages))/max(1,count)),
      "can_back":n>1 or p>0,"can_next":n<latest(db) or p+1<len(pages),
      "last_published":n==latest(db) and p+1==len(pages)}
