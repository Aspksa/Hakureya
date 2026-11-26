"""Local fictional writing scheduler. Consent is persisted; optional credentials are stored outside SQLite by cloud_vault."""
import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
import writer_volume
import soul_omega as o
import soul_genesis as g
import soul_shadow as sh
import soul_guardians as gu
import soul_destiny as de

VERSION=1
THEMES=(
 ("love","Новая совместная традиция","Событие раскрывает любовь через выбор, юмор, заботу или письмо, без повторения признания."),
 ("character","Собственная жизнь героя","Развивай личную цель второстепенного персонажа независимо от императрицы."),
 ("world","Новый мир","Открой культуру, обычай, магический закон или артефакт; покажи ограничения и последствия."),
 ("court","Последствия правления","Развивай дипломатический конфликт или реформу, учитывая разные интересы."),
 ("power","Цена дара","Новый ограниченный эффект пространственного дара; выбор, ответственность и последствия."),
 ("mystery","Старая загадка","Вернись к открытой загадке, найди новую улику, не разрешай всё сразу."),
 ("guardians","Девять самостоятельных судеб","Одна хранительница принимает решение, развивает дружбу или личное стремление."),
 ("growth","Изменение Хакурэи","Конкретный поступок раскрывает изменение характера, сохраняя её достоинство и свободу.")
)
KINDS=("goal","belief","secret","relationship","culture","law","artifact","tradition","consequence","thread")
def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS living_settings(
      id INTEGER PRIMARY KEY CHECK(id=1), mode TEXT NOT NULL CHECK(mode IN ('off','draft','auto')))""")
    db.execute("INSERT OR IGNORE INTO living_settings VALUES(1,'off')")
    db.execute("""CREATE TABLE IF NOT EXISTS living_queue(
      id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL, checksum TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS living_records(
      draft_id INTEGER PRIMARY KEY, payload TEXT NOT NULL, source_hash TEXT NOT NULL, checksum TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS living_log(
      id INTEGER PRIMARY KEY, event TEXT NOT NULL, detail TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP)""")
    db.execute("""CREATE TABLE IF NOT EXISTS living_backups(day TEXT PRIMARY KEY, filename TEXT NOT NULL)""")

def mode(db):
    return db.execute("SELECT mode FROM living_settings WHERE id=1").fetchone()[0]

def log(db,event,detail=""):
    db.execute("INSERT INTO living_log(event,detail) VALUES(?,?)",(event,detail[:300]))
    db.execute("DELETE FROM living_log WHERE id NOT IN (SELECT id FROM living_log ORDER BY id DESC LIMIT 200)")

def set_mode(db,value):
    if value not in ("off","draft","auto"):raise ValueError("invalid mode")
    if value!="auto":writer_volume.cancel_job(db)
    db.execute("UPDATE living_settings SET mode=? WHERE id=1",(value,))
    log(db,"mode",value)

def record(db,did):
    row=db.execute("SELECT payload,source_hash,checksum FROM living_records WHERE draft_id=?",(did,)).fetchone()
    if not row:return None
    raw,source,h=row
    d=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()
    if not d or source!=d[0] or o.digest(o.dump([raw,source]))!=h:raise ValueError("damaged living record")
    return json.loads(raw)

def published(db):
    for did,n in db.execute("""SELECT r.draft_id,a.number FROM living_records r JOIN saga_arcs a ON a.draft_id=r.draft_id
        JOIN chronicle_drafts d ON d.id=r.draft_id WHERE d.status='approved' ORDER BY a.number"""):
        yield n,did,record(db,did)

def audit(db):
    try:
        for _,_,p in published(db):
            if not isinstance(p,dict) or p.get("version")!=VERSION:raise ValueError("version")
    except (ValueError,TypeError,KeyError):return ["Повреждены записи Living Universe"]
    return []

def queue(db,limit=100):
    """Rolling 100-slot forecast. Only the head is committed as a writing intention."""
    latest=db.execute("SELECT COALESCE(MAX(number),13) FROM omega_index").fetchone()[0]
    cached=db.execute("SELECT payload,checksum FROM living_queue WHERE id=1").fetchone()
    if limit==100 and cached and o.digest(cached[0])==cached[1]:
        try:
            q=json.loads(cached[0])
            if q.get("version")==VERSION and q.get("based_on")==latest and len(q["items"])==100:return q
        except (ValueError,TypeError,KeyError):pass
    data=g.state(db)
    old=list(published(db))
    count=len(old)
    recent=[p["theme"] for _,_,p in old[-8:]]
    candidates=[]
    for i,(key,title,guide) in enumerate(THEMES):
        score=10-3*recent.count(key)
        if key=="mystery" and data["open"]:score+=5
        if key=="character" and data["forgotten"]:score+=5
        candidates.append((score,-((i-count)%len(THEMES)),key,title,guide))
    ranked=sorted(candidates,reverse=True)
    result=[]
    for i in range(limit):
        _,_,key,title,guide=ranked[i%len(ranked)]
        result.append({"number":latest+i+1,"volume":o.volume(latest+i+1),"theme":key,"title":title,"guide":guide})
    # Simulate remaining approved-stage prerequisites without advancing the actual saga.
    fixed=None
    if not (gu.audit(db) or sh.audit(db) or de.audit(db)):
        si,gi,di=len(sh.completed(db)),len(gu.published(db)),len(de.published(db))
        for item in result:
            if gi<len(gu.STEPS) and si>=gu.STEPS[gi][0]:
                _,title,_,guide=gu.STEPS[gi];gi+=1
            elif si<len(sh.STEPS):
                _,title,guide=sh.STEPS[si];si+=1
            elif gi<len(gu.STEPS):
                break
            elif di<len(de.ORDER):
                title,guide=de.BEATS[de.ORDER[di]-1];di+=1
            else:break
            item.update(title=title,guide=guide,theme="fixed")
            fixed=True
    payload={"version":VERSION,"based_on":latest,"items":result,
             "forgotten":data["forgotten"][:4],"open":data["open"][:4],
             "romance_threads":[]}
    import soul_heart
    payload["romance_threads"]=[{"key":k,**v} for k,v in soul_heart.threads(db).items() if v["closed"] is None][:4]
    if not fixed:
        head=result[0]
        if head["theme"]=="character" and payload["forgotten"]:
            actor=payload["forgotten"][0];head["title"]="Возвращение: "+actor["name"];head["guide"]+=" Верни персонажа "+actor["name"]+" из главы "+str(actor["last"])+", сохрани мотивы."
        if head["theme"]=="mystery" and payload["open"]:
            mystery=payload["open"][0];head["title"]="Новая улика: "+mystery["question"][:70];head["guide"]+=" Исследуй вопрос: "+mystery["question"]
        if head["theme"]=="love" and payload["romance_threads"]:
            head["guide"]+=" Развивай открытую линию: "+payload["romance_threads"][0]["title"]
    raw=o.dump(payload)
    if limit==100:db.execute("INSERT INTO living_queue VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,checksum=excluded.checksum WHERE checksum!=excluded.checksum",(raw,o.digest(raw)))
    return payload

def enrich(db,plan,background=False):
    q=queue(db)
    fixed=bool(plan.get("dynasty_lane")) or any(k in plan for k in ("shadow","guardians","destiny")) or "cycle_id" in plan.get("romance",{}) or plan["arc"]!="future"
    head=q["items"][0]
    if fixed:head={**head,"theme":"fixed","guide":"Следуй главному замыслу текущей ветки."}
    elif head["theme"]=="fixed":head={**head,"theme":"growth","guide":"Продолжай явно выбранную ветку без раскрытия чужих тайн."}
    known=list(published(db))[-8:]
    # Keep the latest source-linked fact per subject rather than inventing character memories.
    subjects={}
    for n,_,p in published(db):
        for fact in p["facts"]:subjects[(o.normalized(fact["name"]),fact["kind"])]=dict(chapter=n,**fact)
    context=sorted(subjects.values(),key=lambda x:x["chapter"],reverse=True)[:6]
    plan["living"]={"theme":head["theme"],"head":head,"background":bool(background),
        "forgotten":q["forgotten"],"open":q["open"],"romance_threads":q["romance_threads"],
        "recent":[{"chapter":n,"facts":p["facts"][:1]} for n,_,p in known],"subject_context":context}
    return plan

def instruction(plan):
    p=plan.get("living")
    if not p:return ""
    return (" Living Universe — перспективный замысел, не установленные факты: "+o.dump({k:v for k,v in p.items() if k!="background"})+
       ". Сначала соблюди текущую сагу и тайны. Если фиксированных этапов нет, придумай новое событие из предложенной темы, связанное с уже утверждённой историей. "
       "Не повторяй спасения, признания, внешность и одинаковые реакции. У персонажей свои цели и границы знания; новые миры имеют собственные культуру, ограничения магии и последствия. "
       "Выбери один из нескольких мысленно рассмотренных поворотов, отредактируй текст перед выдачей. "
       "Опционально living:{facts:[{kind,name,detail,evidence,cause}]}, максимум два. kind из "+", ".join(KINDS)+
       "; name — имя героя, мира, предмета или линии (2–60 символов); detail — краткий вывод; evidence — дословная цитата из story с именем; cause — номер опубликованной главы или null. "
       "Не выдавай гипотезу за истину, не меняй канон. При нехватке места важнее законченный текст и обязательные метаданные текущего этапа.")

def save(db,did,story,raw,plan):
    p=plan.get("living")
    if not p:
        if raw is not None:raise ValueError("unexpected living fields")
        return
    facts=[] if raw is None else raw.get("facts") if isinstance(raw,dict) and set(raw)=={"facts"} else None
    if not isinstance(facts,list) or len(facts)>2:raise ValueError("invalid living facts")
    out=[]
    for f in facts:
        if not isinstance(f,dict) or set(f)!={"kind","name","detail","evidence","cause"} or f["kind"] not in KINDS:raise ValueError("invalid living fact")
        name=o.clean(f["name"],2,60);quote=o.clean(f["evidence"],12,240);cause=f["cause"]
        if quote not in story or o.normalized(name) not in o.normalized(quote):raise ValueError("living excerpt absent")
        if cause is not None and (type(cause) is not int or not db.execute("SELECT 1 FROM omega_index WHERE number=?",(cause,)).fetchone()):raise ValueError("invalid living cause")
        out.append({"kind":f["kind"],"name":name,"detail":o.clean(f["detail"],8,180),"evidence":quote,"cause":cause})
    raw=o.dump({"version":VERSION,"theme":p["theme"],"background":p["background"],"facts":out,
                "required":[k for k in ("shadow","guardians","destiny") if k in plan]})
    source=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()[0]
    db.execute("INSERT INTO living_records VALUES(?,?,?,?)",(did,raw,source,o.digest(o.dump([raw,source]))))

def eligible(db,did):
    """Conservative heuristic gate. Never certify semantic correctness."""
    import soul_chronicle as c
    import soul_romance as r
    import soul_heart as h
    p=record(db,did)
    if mode(db)!="auto" or not p or not p["background"]:return False
    if not c.canon_ok(db) or g.audit(db)+h.audit(db)+sh.audit(db)+gu.audit(db)+de.audit(db)+audit(db):return False
    for k,mod in (("shadow",sh),("guardians",gu),("destiny",de)):
        if k in p["required"] and not mod.read(db,did):return False
    import soul_immortal
    im=soul_immortal.read(db,did)
    if im and (im["quality"]["warnings"] or (im.get("required") and im["step"] is None)):return False
    import soul_infinite
    inf=soul_infinite.read(db,did)
    if inf and (inf["quality"]["warnings"] or (inf["required"] and not inf["step"])):return False
    import soul_dynasty
    dynasty=soul_dynasty.read(db,did)
    if dynasty:
        if soul_dynasty.audit(db) or dynasty.get("warning"):return False
        if dynasty["target"] and not dynasty["step"]:
            import soul_novel
            part=soul_novel.record(db,did)
            if not part or part["part"]>=12:return False
            rows=soul_novel.published_group(db,part["start"])
            raw,check=db.execute("SELECT payload,checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()
            text=c.unpack(raw,check)["story"]
            import re
            words=sum(len(re.findall(r"\b\w+\b",r["story"])) for r in rows)+len(re.findall(r"\b\w+\b",text))
            if words>=part["target"] or o.volume(part["start"]+part["part"])!=o.volume(part["start"]):return False
    if db.execute("SELECT 1 FROM lit_rejections WHERE draft_id=?",(did,)).fetchone():return False
    m=o.metadata(db,did);review=r.report(db,did)
    return bool(m and review and m["score"]>=85 and not m["warnings"] and review["originality_heuristic"]>=80 and not review["warnings"] and review["words"]>=350)

def publish_if_allowed(db,did):
    import soul_chronicle as c
    try:allowed=eligible(db,did)
    except (ValueError,TypeError,KeyError,sqlite3.Error):allowed=False
    if not allowed:
        log(db,"manual_review","Черновик оставлен на ручную проверку")
        return False
    db.execute("SAVEPOINT living_publish")
    try:
        ok=c.decide(db,did,True)
        if ok:
            log(db,"auto_publish",str(did))
            queue(db)
        db.execute("RELEASE living_publish")
        return ok
    except (ValueError,TypeError,KeyError,sqlite3.Error):
        db.execute("ROLLBACK TO living_publish")
        db.execute("RELEASE living_publish")
        log(db,"manual_review","Проверка публикации не пройдена")
        return False

def backup(db_path,folder):
    """Atomic daily SQLite backup, retains seven snapshots. No credentials in DB."""
    day=datetime.now(timezone.utc).date().isoformat()
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    target=folder/("hakureya-"+day+".sqlite3")
    if target.exists():
        from contextlib import closing
        with closing(sqlite3.connect(target)) as check:
            if check.execute("PRAGMA quick_check").fetchone()[0]!="ok":raise ValueError("damaged backup")
        return target.name
    tmp=target.with_suffix(".tmp")
    from contextlib import closing
    try:
        with closing(sqlite3.connect(str(db_path),timeout=10)) as src, closing(sqlite3.connect(str(tmp))) as dst:
            src.backup(dst)
            if dst.execute("PRAGMA quick_check").fetchone()[0]!="ok":raise ValueError("backup integrity")
        os.replace(tmp,target)
    finally:
        if tmp.exists():tmp.unlink()
    for old in sorted(folder.glob("hakureya-????-??-??.sqlite3"),reverse=True)[7:]:old.unlink()
    return target.name

def status(db):
    pending=db.execute("SELECT COUNT(*) FROM chronicle_drafts WHERE status='pending'").fetchone()[0]
    day=writer_volume.today()
    attempts=writer_volume.attempts(db,day)
    pages=writer_volume.target(db)
    task=writer_volume.job(db)
    if task and task["state"]=="active":
        return f"Разовое задание: {task['chars']}/{task['pages']*writer_volume.PAGE_CHARS} символов утверждённой прозы. Черновиков: {pending}. Запросов задания: {task['attempts']}/{task['limit']}. До {writer_volume.JOB_OUTPUT_LIMIT} выходных токенов на запрос."
    return ("Развитие: "+{"off":"выключено","draft":"черновики","auto":"автопубликация с проверками"}[mode(db)]+
        f". Черновиков: {pending}. Запросов UTC сегодня: {len(attempts)}/{writer_volume.limit(db)}."+
        (f" Цель: {pages} условных страниц А4 (по {writer_volume.PAGE_CHARS} символов)." if pages else " Обычный режим: одна попытка в сутки.")+
        " До 1800 выходных токенов на запрос. Подключение и причины ожидания: панель писателя.")

def news(db):
    rows=db.execute("SELECT number,title FROM omega_index WHERE number>13 ORDER BY number DESC LIMIT 5").fetchall()
    pending=db.execute("SELECT COUNT(*) FROM chronicle_drafts WHERE status='pending'").fetchone()[0]
    result="Последние утверждённые главы:\n"+"\n".join(f"{n}. {t}" for n,t in rows) if rows else "Новых утверждённых глав пока нет."
    return result+("\n\nЕсть черновик: «Покажи черновик»." if pending else "")

def graph(db):
    nodes=[];edges=[];seen=set()
    def node(k,label,kind):
        if k not in seen:
            seen.add(k);nodes.append({"key":k,"group":4,"kind":kind,"content":label,"created":"","order":len(nodes)})
    node("living:root","Живая художественная вселенная","living_root")
    edges.append({"a":"destiny:root","b":"living:root","kind":"living_branch"})
    if audit(db):return nodes,edges
    # Bounded recent detail; old facts remain in the archive.
    all_rows=list(published(db));rows=all_rows[-80:]
    if len(all_rows)>80:
        node("living:archive",f"Архив: {len(all_rows)-80} глав","living_root")
        edges.append({"a":"living:root","b":"living:archive","kind":"living_archive"})
    for n,did,p in rows:
        t="living:theme:"+p["theme"];node(t,next((v[1] for v in THEMES if v[0]==p["theme"]),"Основная сага"),"living_topic")
        edges.extend([{"a":"living:root","b":t,"kind":"living_branch"},{"a":t,"b":f"c:{did}","kind":"living_chapter"}])
        for j,f in enumerate(p["facts"]):
            key=f"living:fact:{did}:{j}";hub="living:subject:"+o.digest(o.normalized(f["name"]))[:20]
            node(hub,f["name"],"living_subject");node(key,f["detail"],"living_fact")
            edges.extend([{"a":t,"b":hub,"kind":"living_subject"},{"a":hub,"b":key,"kind":"living_fact"},{"a":f"c:{did}","b":key,"kind":"living_source"}])
            if f["cause"] is not None:
                r=db.execute("SELECT draft_id FROM omega_index WHERE number=?",(f["cause"],)).fetchone()
                edges.append({"a":f"c:{r[0]}" if r and r[0] is not None else f"canon:{f['cause']}","b":key,"kind":"living_cause"})
    return nodes,edges
