"""Daily prose target, separate request safety ceiling, legacy-compatible attempt IDs."""
from datetime import datetime, timezone
import json

PAGE_CHARS=1800
TARGET_PAGES=15
GOALS=(0,5,10,15,20,30)
MAX_ATTEMPTS=20
JOB_OUTPUT_LIMIT=4096

def init(db):
    db.execute("CREATE TABLE IF NOT EXISTS writer_volume(id INTEGER PRIMARY KEY CHECK(id=1), target INTEGER NOT NULL CHECK(target IN (0,15)))")
    db.execute("INSERT OR IGNORE INTO writer_volume VALUES(1,0)")
    db.execute("CREATE TABLE IF NOT EXISTS writer_daily_goal(id INTEGER PRIMARY KEY CHECK(id=1), target INTEGER NOT NULL CHECK(target IN (0,5,10,15,20,30)))")
    db.execute("INSERT OR IGNORE INTO writer_daily_goal SELECT id,target FROM writer_volume")
    db.execute("""CREATE TABLE IF NOT EXISTS writer_job(
        id INTEGER PRIMARY KEY CHECK(id=1), pages INTEGER NOT NULL,
        model TEXT NOT NULL, state TEXT NOT NULL, reason TEXT NOT NULL)""")
    db.execute("CREATE TABLE IF NOT EXISTS writer_job_attempt(day TEXT PRIMARY KEY)")
    db.execute("CREATE TABLE IF NOT EXISTS writer_job_ack(day TEXT PRIMARY KEY)")

def target(db):
    row=db.execute("SELECT target FROM writer_daily_goal WHERE id=1").fetchone()
    return row[0] if row else 0

def set_target(db,pages):
    if type(pages) is not int or pages not in GOALS:raise ValueError("invalid daily target")
    db.execute("UPDATE writer_daily_goal SET target=? WHERE id=1",(pages,))
    # Retain compatible legacy setting without changing the existing CHECK constraint.
    db.execute("UPDATE writer_volume SET target=? WHERE id=1",(15 if pages else 0,))

def today(now=None):
    return (now or datetime.now(timezone.utc)).date().isoformat()

def attempts(db,day):
    return db.execute("SELECT day,status FROM chronicle_attempts WHERE day=? OR day LIKE ? ORDER BY day",(day,day+"#%")).fetchall()

def published_chars(db,day):
    total=0
    for raw, in db.execute("SELECT payload FROM chronicle_drafts WHERE status='approved' AND substr(decided,1,10)=?",(day,)):
        value=json.loads(raw)
        story=value.get("story")
        if not isinstance(story,str):raise ValueError("invalid published story")
        total+=len(story)
    return total

def limit(db):
    return MAX_ATTEMPTS if active_job(db) or target(db) else 1

def next_id(db,day,editor=False):
    if db.execute("SELECT 1 FROM chronicle_attempts WHERE status='reserved'").fetchone():return None
    rows=attempts(db,day)
    if len(rows)>=limit(db):return None
    pages=target(db)
    if active_job(db):
        if not editor and (job(db)["chars"]>=job(db)["pages"]*PAGE_CHARS or job(db)["attempts"]>=MAX_ATTEMPTS):return None
    elif pages and not editor and published_chars(db,day)>=pages*PAGE_CHARS:return None
    if not rows:return day
    used={key for key,_ in rows}
    for i in range(2,MAX_ATTEMPTS+2):
        key=day+"#"+str(i).zfill(4)
        if key not in used:return key
    return None

def budget_ready(db,model):
    row=db.execute("SELECT model FROM evolution_budget WHERE id=1").fetchone()
    return bool(row and row[0]==model)

def auto_block(db,day):
    """Stop repeated automatic charges after an uncertain or rejected generation."""
    rows=attempts(db,day)
    return any(status in ("failed","interrupted") for _,status in rows)


def cooldown(db,interval):
    row=db.execute("SELECT MAX(created) FROM chronicle_attempts").fetchone()
    if not row or not row[0]:return 0
    try:when=datetime.fromisoformat(row[0]).replace(tzinfo=timezone.utc)
    except ValueError:return interval
    elapsed=(datetime.now(timezone.utc)-when).total_seconds()
    return max(0,min(interval,int(interval-elapsed)))


def active_job(db):
    return bool(db.execute("SELECT 1 FROM writer_job WHERE id=1 AND state='active'").fetchone())

def job(db):
    row=db.execute("SELECT pages,model,state,reason FROM writer_job WHERE id=1").fetchone()
    if not row:return None
    import soul_chronicle as ch
    chars=0
    for raw,check in db.execute("""SELECT d.payload,d.checksum FROM writer_job_attempt j
        JOIN chronicle_attempts a ON a.day=j.day JOIN chronicle_drafts d ON d.diary_id=a.diary_id
        WHERE d.status='approved' AND a.status='draft'"""):
        chars+=len(ch.unpack(raw,check)["story"])
    count=db.execute("SELECT COUNT(*) FROM writer_job_attempt").fetchone()[0]
    return dict(pages=row[0],model=row[1],state=row[2],reason=row[3],chars=chars,attempts=count,limit=MAX_ATTEMPTS)

def start_job(db,pages,model):
    if type(pages) is not int or pages not in GOALS[1:] or not model:raise ValueError("invalid job")
    if active_job(db) or db.execute("SELECT 1 FROM chronicle_attempts WHERE status='reserved'").fetchone() or db.execute("SELECT 1 FROM chronicle_drafts WHERE status='pending'").fetchone():
        raise ValueError("existing job, request or pending draft")
    if len(attempts(db,today()))>=MAX_ATTEMPTS:raise ValueError("daily ceiling")
    db.execute("DELETE FROM writer_job_attempt")
    db.execute("DELETE FROM writer_job_ack")
    db.execute("INSERT OR REPLACE INTO writer_job VALUES(1,?,?,'active','')",(pages,model))
    set_target(db,0)

def register_job_attempt(db,day):
    if active_job(db):db.execute("INSERT INTO writer_job_attempt VALUES(?)",(day,))

def cancel_job(db):
    db.execute("UPDATE writer_job SET state='stopped',reason='Остановлено пользователем' WHERE id=1 AND state='active'")

def close_job(db,state,reason):
    db.execute("UPDATE writer_job SET state=?,reason=? WHERE id=1 AND state='active'",(state,reason))
    import soul_living
    soul_living.set_mode(db,"off")

def reconcile_job(db):
    if not active_job(db):return
    st=job(db)
    if st["chars"]>=st["pages"]*PAGE_CHARS:
        close_job(db,"done","Разовое задание выполнено. Писатель выключен.")
        return
    if db.execute("""SELECT 1 FROM writer_job_attempt j JOIN chronicle_attempts a ON a.day=j.day
        WHERE a.status IN ('failed','interrupted') AND NOT EXISTS (SELECT 1 FROM writer_job_ack k WHERE k.day=a.day)""").fetchone():
        close_job(db,"error","Задание остановлено после ошибки. Повторный платный запрос не отправлен.")
        return
    if db.execute("""SELECT 1 FROM writer_job_attempt j JOIN chronicle_attempts a ON a.day=j.day
        JOIN chronicle_drafts d ON d.diary_id=a.diary_id WHERE d.status='rejected'""").fetchone():
        close_job(db,"stopped","Задание остановлено: черновик отклонён.")
        return
    if db.execute("SELECT 1 FROM chronicle_drafts WHERE status='pending'").fetchone():return
    if db.execute("SELECT 1 FROM chronicle_attempts WHERE status='reserved'").fetchone():return
    if st["attempts"]>=MAX_ATTEMPTS or len(attempts(db,today()))>=MAX_ATTEMPTS:
        close_job(db,"limit","Задание остановлено: достигнут защитный предел запросов.")


def resume_job(db,model):
    st=job(db)
    if not st or st["state"]!="error":raise ValueError("Нет остановленного задания после ошибки.")
    if model!=st["model"]:raise ValueError("Модель изменилась. Создайте новое задание.")
    if st["chars"]>=st["pages"]*PAGE_CHARS or st["attempts"]>=MAX_ATTEMPTS or len(attempts(db,today()))>=MAX_ATTEMPTS:
        raise ValueError("Цель или защитный предел уже достигнут.")
    if db.execute("SELECT 1 FROM chronicle_attempts WHERE status='reserved'").fetchone() or db.execute("SELECT 1 FROM chronicle_drafts WHERE status='pending'").fetchone():
        raise ValueError("Сначала завершите текущую попытку или черновик.")
    db.execute("""INSERT OR IGNORE INTO writer_job_ack SELECT j.day FROM writer_job_attempt j
        JOIN chronicle_attempts a ON a.day=j.day WHERE a.status IN ('failed','interrupted')""")
    db.execute("UPDATE writer_job SET state='active',reason='' WHERE id=1")
    set_target(db,0)
    import soul_living
    soul_living.set_mode(db,"auto")
