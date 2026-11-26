"""Daily prose target, separate request safety ceiling, legacy-compatible attempt IDs."""
from datetime import datetime, timezone
import json

PAGE_CHARS=1800
TARGET_PAGES=15
GOALS=(0,5,10,15,20,30)
MAX_ATTEMPTS=20

def init(db):
    db.execute("CREATE TABLE IF NOT EXISTS writer_volume(id INTEGER PRIMARY KEY CHECK(id=1), target INTEGER NOT NULL CHECK(target IN (0,15)))")
    db.execute("INSERT OR IGNORE INTO writer_volume VALUES(1,0)")
    db.execute("CREATE TABLE IF NOT EXISTS writer_daily_goal(id INTEGER PRIMARY KEY CHECK(id=1), target INTEGER NOT NULL CHECK(target IN (0,5,10,15,20,30)))")
    db.execute("INSERT OR IGNORE INTO writer_daily_goal SELECT id,target FROM writer_volume")

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
    return MAX_ATTEMPTS if target(db) else 1

def next_id(db,day,editor=False):
    if db.execute("SELECT 1 FROM chronicle_attempts WHERE status='reserved'").fetchone():return None
    rows=attempts(db,day)
    if len(rows)>=limit(db):return None
    pages=target(db)
    if pages and not editor and published_chars(db,day)>=pages*PAGE_CHARS:return None
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
