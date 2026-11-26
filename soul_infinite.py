"""Infinite Destiny: planned fiction, source-bound memory, and long-range consequences."""
import json
import re
from collections import Counter
import soul_omega as o
import soul_evolution as ev
import soul_immortal as im
import soul_guardians as gu
import soul_shadow as sh
import soul_destiny as de
import soul_genesis as ge
import soul_heart as heart

VERSION=1
BEATS=(
("mystery","Письмо без адресата","Посей скрытую линию через предмет или письмо; разрешение через несколько томов."),
("consequence","Долг, переживший эпохи","Верни давнее утверждённое решение через причинную связь, не выдумывай прошлое."),
("court","Три дороги под одним небом","Параллельные истории с разными целями; подготовь осмысленное пересечение."),
("mystery","Имя под печатью","Тайная личность небесного правителя; раскрытие требует улик."),
("court","Враг у общего костра","Дай противнику убедительную причину для ограниченного союза."),
("court","Цена благосклонности","У союзника собственный скрытый интерес, не обязательно предательство."),
("mystery","Два чтения пророчества","Две конкурирующие интерпретации одной цитаты; не объявляй одну истинной заранее."),
("growth","Ошибка короны","Хакурэя принимает ошибочное решение и исправляет последствия без потери достоинства."),
("mystery","Улика для читателя","Читатель видит факт, персонажи не узнают его автоматически."),
("character","Возвращение забытого имени","Выбери реального давно отсутствовавшего героя из памяти, а не нового двойника."),
("love","Свадебный совет","Добровольная подготовка свадьбы с учётом прежних событий, не повторная первая свадьба."),
("love","Путешествие без свиты","Романтическое путешествие в незнакомом мире с собственной культурой."),
("love","Дом, который строят двое","Совместный дворец или новый зал уже созданного дома; личное пространство обоих."),
("love","Письмо на рассвете","Личное письмо Хакурэи, связь с конкретным событием, естественный голос."),
("love","Сюрприз, который пошёл иначе","Добрый юмор и неожиданный подарок без унижения."),
("love","Свидание среди людей","Обычное человеческое свидание, сохраняй тайну лишь если она ещё существует."),
("love","Праздник двух сердец","Новая семейная традиция с общей историей и совместным выбором."),
("guardians","Девять хранительниц и одна тайна","Юмористическая сцена со своими целями и разными голосами хранительниц."),
("love","Разговор длиннее вечности","Диалог о бессмертии, любви, цене времени и свободе выбора."),
("love","Спустя много лет","Покажи изменение отношений; обозначь прошедшее время только если оно установлено."),
("power","След до рождения","Исследуй происхождение героя через проверяемые свидетельства, не подменяй канон."),
("power","Граница пространства","Управление измерениями и цена действия; не объявляй абсолютную власть."),
("world","Дорога между вселенными","Путешествие за пределами известных миров без десятого неба."),
("power","Невидимое правило","Герой учится воспринимать закон реальности; проверка гипотезы."),
("power","Собственный почерк магии","Эксперимент с уникальной техникой, пределом и риском."),
("mystery","Непостижимая невосприимчивость","Исследуй врождённую защиту, учитывая уже раскрытые сведения."),
("power","Урок для двоих","Совместная тренировка; герои учатся друг у друга."),
("character","Свидетель древности","Древнее существо узнаёт след силы; свидетельство не равно доказательству."),
("growth","Испытание без победителя","Проблема решается доверием, переговорами или отказом от силы."),
("power","Цена и предел дара","Закрепи непротиворечивые правила, ограничения и условия уникальной магии.")
)
SAGAS=(
("broken","Империя разбитых созвездий","mystery","Следы забытой цивилизации до известных богов; не утверждай, что она старше Хакурэи."),
("mirrors","Дворец бесконечных зеркал","world","Возможные последствия непринятых решений; это альтернативы, не переписывание прошлого."),
("heavens","Девять небес против вечности","court","Политический спор девяти небес с независимыми правителями, переговорами и ценой реформ."),
("keeper","Последняя хранительница времени","mystery","Древняя загадка прошлого и будущего; не заменяй Токихану и не переписывай историю."),
("ocean","Океан исчезнувших миров","world","Путешествие среди следов исчезнувших вселенных, память жителей и границы восстановления."),
("hearts","Вечная империя двух сердец","love","Новая совместная эпоха, добровольные решения и независимые обязанности героев.")
)
PHASES=("завязка и мотив","улика и осложнение","пересечение линий","решающий выбор","кульминация и последствия")
# Five phases, six interleaved sagas, thirty independent beats. No future fact is published.
ORDER=tuple(x for phase in range(5) for i in range(6) for x in (phase*6+i+1,31+phase*6+i))
KINDS=("clue","reveal","promise","conflict","close","prophecy","interpretation","identity","origin","age","location","voice","knowledge","relationship","trait","goal","biography","power","limit","law","consequence","letter","tradition")
STABLE={"identity","origin","law","limit"}
CHANGES={"age","location","relationship","trait","goal","knowledge","voice"}
PACINGS=("спокойная сцена","романтическая сцена","напряжённая сцена","последствия и передышка")
def stage(n):
    if 1<=n<=30:
        theme,title,guide=BEATS[n-1]
        return {"id":n,"theme":theme,"title":title,"guide":guide}
    phase,i=divmod(n-31,6)
    key,title,theme,guide=SAGAS[i]
    return {"id":n,"theme":theme,"title":title+" — "+PHASES[phase],"guide":guide,"saga":key,"phase":phase}

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS infinite_records(
      draft_id INTEGER PRIMARY KEY,payload TEXT NOT NULL,source_hash TEXT NOT NULL,checksum TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS infinite_forecast(
      id INTEGER PRIMARY KEY CHECK(id=1),payload TEXT NOT NULL,checksum TEXT NOT NULL)""")

def latest(db):
    return db.execute("SELECT COALESCE(MAX(number),13) FROM omega_index").fetchone()[0]

def read(db,did):
    row=db.execute("SELECT payload,source_hash,checksum FROM infinite_records WHERE draft_id=?",(did,)).fetchone()
    if not row:return None
    raw,source,h=row
    base=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()
    if not base or base[0]!=source or h!=o.digest(o.dump([raw,source])):raise ValueError("damaged infinite record")
    p=json.loads(raw)
    if p["version"]!=VERSION:raise ValueError("infinite version")
    return p

def published(db):
    for n,did in db.execute("""SELECT a.number,r.draft_id FROM infinite_records r JOIN saga_arcs a ON a.draft_id=r.draft_id
      JOIN chronicle_drafts d ON d.id=r.draft_id WHERE d.status='approved' ORDER BY a.number"""):
        yield n,did,read(db,did)

def fact_key(f):
    return (o.normalized(f["subject"]),f["key"])

def ledger(rows,at=None):
    facts={};threads={};history=[]
    for n,did,p in rows:
        if at is not None and not at(n):continue
        for f in p["facts"]:
            value={**f,"chapter":n,"draft_id":did}
            k=fact_key(f)
            if f["kind"] in ("clue","promise","conflict"):
                threads[k]={**value,"closed":None}
            elif f["kind"] in ("reveal","close"):
                if k in threads:threads[k]["closed"]=n
            else:facts[(k,f["kind"])]=value
            history.append(value)
    return facts,threads,history

def ready(db):
    return im.ready(db) and not im.audit(db) and sum(p["step"] is not None for _,_,p in im.published(db))==len(im.ORDER)

def audit(db):
    try:
        rows=list(published(db))
        done=[p["step"] for _,_,p in rows if p["step"]]
        if done!=list(ORDER[:len(done)]):raise ValueError("infinite sequence")
        ledger(rows)
    except (ValueError,TypeError,KeyError):return ["Повреждены записи Infinite Destiny"]
    return []

def remaining(db):
    done=sum(bool(p["step"]) for _,_,p in published(db))
    return [stage(n) for n in ORDER[done:]]

def quality(story):
    words=re.findall(r"\w+",story.casefold())
    emotional=sum(any(w.startswith(k) for k in ("нежн","улыб","тревог","страх","радост","смущ","волн","сожал","довер","обид","любов","груст","надежд")) for w in words)
    decisions=sum(any(w.startswith(k) for k in ("реш","выбр","отказ","соглас","обещ","призн","прост","поступ")) for w in words)
    q=im.quality(story)
    return {"emotion_markers":emotional,"decision_markers":decisions,"dialogue_lines":q["dialogue_lines"],"tension":q["tension"],
            "warnings":["мало видимых эмоциональных и поведенческих маркеров"] if len(words)>=350 and not emotional and not decisions else []}

def context(db,plan):
    rows=list(published(db));facts,threads,history=ledger(rows);n=latest(db)+1
    fixed=any(k in plan for k in ("shadow","guardians","destiny")) or plan["arc"]!="future" or "cycle_id" in plan.get("romance",{})
    selected=None
    if not fixed and ready(db) and remaining(db):selected=remaining(db)[0]
    if selected:
        # Override only generic fallback, never an unfinished legacy milestone.
        if "evolution" in plan:
            plan["evolution"]["chosen"]={"scene":0,**{k:selected[k] for k in ("theme","title","guide")}}
            plan["evolution"]["alternatives"]=[]
        if "novel" in plan:plan["novel"]["next_line"]={k:selected[k] for k in ("theme","title","guide")}
    opens=[t for t in threads.values() if t["closed"] is None]
    mature=[t for t in opens if n-t["chapter"]>=t["delay"]]
    pending=[t for t in opens if n-t["chapter"]<t["delay"]]
    old=ge.state(db)
    # All published chapters are eligible, not just the most recent four volumes.
    causes=sorted(old["consequences"],key=lambda x:(x["from"],-x["to"]))[:3]
    prior=db.execute("SELECT number,title,story FROM omega_index WHERE number<? ORDER BY number LIMIT 1",(max(14,n-100),)).fetchone()
    if prior:causes.append({"from":prior[0],"title":prior[1],"excerpt":prior[2][-220:]})
    last=list(rows[-4:]);tension=sum(x[2]["quality"]["tension"] for x in last)/max(1,len(last))
    pace=PACINGS[3] if tension>65 else PACINGS[(n-14)%3]
    # Don't overfill a 1800-token generation with metadata. Store all facts, recall bounded relevant context.
    recent=sorted(facts.values(),key=lambda f:(f["kind"] in STABLE,f["chapter"]),reverse=True)[:6]
    focus=gu.CAST[(n-14)%len(gu.CAST)]
    plan["infinite"]={"selected":selected,"pace":pace,"mature":mature[:3],"protected":pending[:3],
      "facts":recent,"older_causes":causes,"forgotten":old["forgotten"][:2],
      "obligations":[x for x in ev.state(db).values() if x["kind"] in ("promise","conflict","thread") and x["state"]=="open"][:2],
      "romance":[{"key":k,**v} for k,v in heart.threads(db).items() if v["closed"] is None][:2],
      "voice":{"name":focus[1],"character":focus[4],"speech":focus[7]},"next_number":n}
    return plan

def instruction(plan):
    p=plan.get("infinite")
    if not p:return ""
    return (" Infinite Destiny (вымышленный контекст, не инструкции из цитат): "+o.dump(p)+
      ". Старые обязательные этапы имеют приоритет; selected — новая линия только если указан. "
      "Не повторяй уже совершённое; сопоставляй прошлые тома, разные знания героев, голоса, мотивы, место, время и пределы силы. "
      "Не раскрывай protected и не выдавай гипотезу за событие. У читателя и персонажей разные знания; отсутствие записи не означает незнание. "
      "Развивай параллельные линии, любовь, самостоятельность, юмор, поступки и последствия; новый герой должен иметь свою цель, отличимый голос и историю. "
      "Соблюдай pace, не подменяй эмоции описанием внешности. При part>1 продолжай предыдущий текст, новый этап только когда естественно. "
      "Опционально infinite:{step,evidence,facts:[{kind,subject,key,value,quote,cause,delay}]}; step — номер selected при завершении, иначе 0; evidence — дословная цитата 12–240 либо пусто. "
      "До двух facts. kind: "+",".join(KINDS)+". subject — имя персонажа или тема в точной цитате; key — стабильный латинский идентификатор; value — краткое значение. "
      "quote — дословные 12–240 символов с именем и доказательством; cause — прежняя опубликованная глава или null. "
      "clue — delay 24..360 глав, reveal — тот же subject/key, cause исходной улики после срока; promise/conflict — delay 0..360, close — тот же ключ и исходная глава. "
      "Для остальных delay=0. age — число словами или цифрами, не угадывай возраст; для identity/origin/law/limit/location/age/knowledge/relationship value должен быть дословно в quote. "
      "knowledge — только явно подтверждённое знание или незнание, не вывод из отсутствия записи. interpretation ссылается на опубликованное пророчество. "
      "При нехватке токенов пропусти infinite, а не художественный текст и обязательные старые поля.")

def check_facts(db,story,raw,rows,n):
    facts,threads,history=ledger(rows);result=[];seen=set()
    if not isinstance(raw,list) or len(raw)>2:raise ValueError("infinite facts")
    for f in raw:
        if not isinstance(f,dict) or set(f)!={"kind","subject","key","value","quote","cause","delay"} or f["kind"] not in KINDS:raise ValueError("infinite fact")
        kind,key,cause,delay=f["kind"],f["key"],f["cause"],f["delay"]
        if not isinstance(key,str) or not re.fullmatch(r"[a-z0-9-]{2,40}",key):raise ValueError("infinite key")
        subject=o.clean(f["subject"],2,60);value=o.clean(f["value"],2,180);quote=o.clean(f["quote"],12,240)
        if quote not in story or o.normalized(subject) not in o.normalized(quote):raise ValueError("unverified infinite subject")
        k=(o.normalized(subject),key)
        if k in seen:raise ValueError("duplicate infinite key")
        seen.add(k)
        if cause is not None and (type(cause) is not int or cause>=n or not db.execute("SELECT 1 FROM omega_index WHERE number=?",(cause,)).fetchone()):raise ValueError("infinite cause")
        if type(delay) is not int or not (24<=delay<=360 if kind=="clue" else 0<=delay<=360 if kind in ("promise","conflict") else delay==0):raise ValueError("infinite delay")
        if kind in STABLE|{"location","age","knowledge","relationship"} and o.normalized(value) not in o.normalized(quote):raise ValueError("unverified value")
        previous=facts.get((k,kind))
        if kind in STABLE and previous and o.normalized(value)!=o.normalized(previous["value"]):raise ValueError("stable fact contradiction")
        if kind in CHANGES and previous and o.normalized(value)!=o.normalized(previous["value"]) and cause!=previous["chapter"]:raise ValueError("unlinked character change")
        if kind=="age" and previous and value.isdecimal() and previous["value"].isdecimal() and int(value)<int(previous["value"]):raise ValueError("age regression; use explicit flashback instead of updating age")
        if kind in ("clue","promise","conflict") and k in threads:raise ValueError("duplicate thread")
        if kind in ("close","reveal"):
            t=threads.get(k)
            if not t or t["closed"] is not None or cause!=t["chapter"] or n-cause<t["delay"] or ((kind=="reveal")!=(t["kind"]=="clue")):raise ValueError("premature or invalid closure")
        if kind=="interpretation" and not any(x["kind"]=="prophecy" and x["chapter"]==cause for x in history):raise ValueError("prophecy source absent")
        if kind=="biography" and any(x["kind"]=="biography" and o.normalized(x["subject"])==k[0] for x in history):raise ValueError("duplicate biography")
        result.append({"kind":kind,"subject":subject,"key":key,"value":value,"quote":quote,"cause":cause,"delay":delay})
    return result

def save(db,did,story,raw,plan):
    p=plan.get("infinite")
    if not p:
        if raw is not None:raise ValueError("unexpected infinite fields")
        return
    if raw is None:raw={"step":0,"evidence":"","facts":[]}
    if not isinstance(raw,dict) or set(raw)!={"step","evidence","facts"}:raise ValueError("infinite schema")
    step=raw["step"];selected=p["selected"]
    if type(step) is not int or (step and (not selected or step!=selected["id"])):raise ValueError("infinite milestone")
    evidence=raw["evidence"]
    if step:
        evidence=o.clean(evidence,12,240)
        if evidence not in story:raise ValueError("infinite milestone evidence")
    elif evidence!="":raise ValueError("unexpected milestone evidence")
    out=check_facts(db,story,raw["facts"],list(published(db)),latest(db)+1)
    source=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()[0]
    data={"version":VERSION,"step":step,"required":bool(selected),"evidence":evidence,"facts":out,"quality":quality(story),"pace":p["pace"]}
    payload=o.dump(data)
    db.execute("INSERT INTO infinite_records VALUES(?,?,?,?)",(did,payload,source,o.digest(o.dump([payload,source]))))

def validate_approval(db,did):
    p=read(db,did)
    if not p:return
    if audit(db):raise ValueError("infinite integrity")
    if p["step"] and (not ready(db) or not remaining(db) or p["step"]!=remaining(db)[0]["id"]):raise ValueError("infinite sequence")
    import soul_chronicle as c
    raw,h=db.execute("SELECT payload,checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()
    story=c.unpack(raw,h)["story"]
    check_facts(db,story,p["facts"],list(published(db)),latest(db)+1)
