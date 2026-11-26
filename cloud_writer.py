"""Cloud.ru writer selection; no credentials on disk and no automatic model fallback."""
import json
from urllib.request import Request
from datetime import datetime,timezone

PREFERRED="GLM-5.3"
MODELS_URL="https://foundation-models.api.cloud.ru/v1/models"
LIMIT=1800

def init(db):
    db.execute("CREATE TABLE IF NOT EXISTS cloud_writer(id INTEGER PRIMARY KEY CHECK(id=1), model TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS cloud_writer_usage(day TEXT PRIMARY KEY, model TEXT NOT NULL, input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL)")

def selected(db):
    row=db.execute("SELECT model FROM cloud_writer WHERE id=1").fetchone()
    return row[0] if row else ""

def choose(db,model):
    db.execute("INSERT OR REPLACE INTO cloud_writer VALUES(1,?)",(model,))

def list_models(key,opener):
    req=Request(MODELS_URL,headers={"Authorization":"Bearer "+key,"Accept":"application/json"})
    with opener(req,timeout=15) as response:
        raw=response.read(2_000_001)
    if len(raw)>2_000_000:raise ValueError("large model list")
    data=json.loads(raw)["data"]
    if not isinstance(data,list):raise ValueError("bad model list")
    return sorted({x["id"] for x in data if isinstance(x,dict) and isinstance(x.get("id"),str) and 0<len(x["id"])<=200 and all(32<=ord(c)<127 for c in x["id"])})

def match(ids,requested):
    exact=[x for x in ids if x.casefold()==requested.casefold()]
    if len(exact)==1:return exact[0]
    suffix=[x for x in ids if x.rsplit("/",1)[-1].casefold()==requested.casefold()]
    return suffix[0] if len(suffix)==1 else None

def usage(db,day,model,result):
    u=result.get("usage")
    if not isinstance(u,dict):return
    a,b=u.get("prompt_tokens"),u.get("completion_tokens")
    if type(a) is int and type(b) is int and a>=0 and b>=0:
        db.execute("INSERT OR IGNORE INTO cloud_writer_usage VALUES(?,?,?,?)",(day,model,a,b))

def usage_text(db):
    rows=db.execute("SELECT day,model,input_tokens,output_tokens FROM cloud_writer_usage ORDER BY day DESC LIMIT 7").fetchall()
    return "Токены по ответам Cloud.ru (не денежный счёт):\n"+"\n".join(f"{d}: {m} — вход {a}, выход {b}" for d,m,a,b in rows) if rows else "Cloud.ru пока не вернул статистику литературных запросов."

def style(plan):
    if not plan:return ""
    return (" Литературный стандарт: современная выразительная русская проза, естественный синтаксис, "
            "индивидуальные голоса, конкретные чувственные детали вместо нагромождения эпитетов. "
            "В каждой сцене есть желание персонажа, препятствие, выбор, неожиданное, но подготовленное последствие. "
            "Сохраняй постепенное сближение, взаимную нежность, юмор и достоинство Хакурэи; не делай героев всезнающими. "
            "Показывай действие и подтекст вместо объяснения эмоций. Чередуй темп: тихая сцена, напряжение, разрядка. "
            "Не начинай с описания внешности по шаблону, не повторяй одну метафору, не заканчивай каждую главу одинаковым клиффхэнгером. "
            "Пиши законченную сцену, а не краткий план. При ограниченном бюджете оставь место для текста и нужной сюжетной отметки; "
            "лишние необязательные метаданные опускай. Верни валидный JSON без markdown, без текста вне объекта. "
            "Сохрани текущий канон и границы знания персонажей.")
