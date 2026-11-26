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
    fixed=bool(plan.get("dynasty_lane")) or any(k in plan for k in ("shadow","guardians","destiny")) or plan["arc"]!="future" or "cycle_id" in plan.get("romance",{})
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
    # Rotate through genuinely old source material rather than repeatedly recalling chapter one.
    cutoff=max(14,n-100)
    recall=1+(n*37)%max(1,cutoff-1)
    prior=db.execute("SELECT number,title,story FROM omega_index WHERE number<=? ORDER BY number DESC LIMIT 1",(recall,)).fetchone()
    if prior:causes.append({"from":prior[0],"title":prior[1],"excerpt":prior[2][-220:]})
    last=list(rows[-4:]);tension=sum(x[2]["quality"]["tension"] for x in last)/max(1,len(last))
    pace=PACINGS[3] if tension>65 else PACINGS[(n-14)%3]
    # Don't overfill a 1800-token generation with metadata. Store all facts, recall bounded relevant context.
    recent=sorted(facts.values(),key=lambda f:(f["kind"] in STABLE,f["chapter"]),reverse=True)[:6]
    if selected is None and not fixed and ready(db):
        # After all fixed stages, choose a bounded long-range proposal for the actual next scene.
        proposal=forecast(db)["items"][0]
        if "novel" in plan:plan["novel"]["next_line"]={k:proposal[k] for k in ("theme","title","guide")}
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


# Additional proposals are varied by setting, conflict, lens, and volume phase.
# A forecast never asserts that a future event occurred.
SETTINGS=("небесная библиотека","пограничный город","дом в человеческом мире","дворцовый сад","звёздная пристань","архив забытых цивилизаций","морское побережье","совет правителей","обсерватория","праздник в другом мире","мастерская","перевал между мирами","древний храм","неизвестная долина","зал переговоров","корабль исследователей","семейный дворец","небесная школа","рынок ремесленников","мир зеркал")
CONFLICTS=("неожиданное последствие обещания","противоречивое свидетельство","цена добровольного выбора","доверие бывшему противнику","исчезновение важной улики","ошибка в толковании закона","соперничество без вражды","столкновение обязанностей","проверка границ дара","маленькая тайна повседневности","случайное недоразумение","возвращение давнего долга")
LENSES=("Хакурэя","герой","одна хранительница","небесный дипломат","местный житель","бывший противник","новый свидетель","друг семьи","учёный","другой участник события")
def forecast(db):
    import soul_living
    n=latest(db)
    base=soul_living.queue(db,limit=118)
    items=[dict(x) for x in base["items"] if x["theme"]=="fixed"]
    for p in ev.candidates(db,list(ev.published(db))):
        if p["scene"]:items.append({"title":p["title"],"theme":p["theme"],"guide":p["guide"]})
    done=sum(p["step"] is not None for _,_,p in im.published(db))
    for i,phase in im.ORDER[done:]:
        if i<10:
            _,title,theme,guide=im.SAGAS[i];title+=" — "+im.PHASES[phase]
        else:title,guide=im.DAILY[i-10];theme="love"
        items.append({"title":title,"theme":theme,"guide":guide})
    items.extend(remaining(db))
    for i in range(len(items),1000):
        serial=(n+i)*37
        place=SETTINGS[serial%len(SETTINGS)]
        conflict=CONFLICTS[(serial//len(SETTINGS))%len(CONFLICTS)]
        lens=LENSES[(serial//(len(SETTINGS)*len(CONFLICTS)))%len(LENSES)]
        theme=BEATS[(i+n)%len(BEATS)][0]
        items.append({"theme":theme,"title":place.capitalize()+" — "+conflict,"guide":"Возможная сцена: "+lens+"; "+conflict+". Не утверждай её заранее.","lens":lens})
    for i,p in enumerate(items):
        number=n+i+1
        pos=(number-14)%12
        p.update(number=number,volume=o.volume(number),pace=PACINGS[i%3],
                 phase_volume="завязка" if pos<3 else "развитие" if pos<9 else "кульминация и последствия",
                 proposal=True)
    raw=o.dump({"version":VERSION,"based_on":n,"items":items})
    db.execute("INSERT INTO infinite_forecast VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,checksum=excluded.checksum WHERE checksum!=excluded.checksum",(raw,o.digest(raw)))
    return json.loads(raw)

def refresh_forecast(db):
    row=db.execute("SELECT payload,checksum FROM infinite_forecast WHERE id=1").fetchone()
    if row and o.digest(row[0])==row[1]:
        try:
            value=json.loads(row[0])
            if value["version"]==VERSION and value["based_on"]==latest(db) and len(value["items"])==1000:return
        except (ValueError,TypeError,KeyError):pass
    forecast(db)

def source_visible(db,n):
    return n<=13 or ev.readable(db,n)

def public_rows(db):
    return [(n,did,p) for n,did,p in published(db) if source_visible(db,n)]

def source_key(db,n):
    row=db.execute("SELECT draft_id FROM omega_index WHERE number=?",(n,)).fetchone()
    if not row:return None
    return f"c:{row[0]}" if row[0] is not None else f"canon:{n}"

def history_text(db,page=1):
    rows=db.execute("SELECT number,title,draft_id FROM omega_index ORDER BY number").fetchall()
    lines=[]
    for n,title,did in rows:
        if not source_visible(db,n):continue
        m=o.metadata(db,did) if did else None
        events=m["data"]["events"] if m else []
        lines.append(f"Глава {n} · том {o.volume(n)}: {title}"+(" — "+"; ".join(x["summary"] for x in events) if events else ""))
    return "Хронология публикаций (не календарь мира):\n"+"\n".join(lines[(page-1)*25:page*25]) if lines[(page-1)*25:page*25] else "Нет доступных событий на этой странице."

def encyclopedia(db,page=1):
    # Reuse actual world portraits, and augment with visible character ledger only.
    names={}
    for n,did in db.execute("SELECT number,draft_id FROM omega_index WHERE draft_id IS NOT NULL ORDER BY number"):
        if not source_visible(db,n):continue
        m=o.metadata(db,did)
        if m:
            for e in m["data"]["events"]:
                for name in e["characters"]:names[o.normalized(name)]=(name,n)
        w=ge.world(db,did)
        if w:
            for p in w["characters"]:names[o.normalized(p["name"])]=(p["name"],n)
    for n,_,p in public_rows(db):
        for f in p["facts"]:
            if f["kind"] not in ("clue","reveal","prophecy","interpretation","law","consequence"):names[o.normalized(f["subject"])]=(f["subject"],n)
    names.setdefault(o.normalized("Хакурэя"),("Хакурэя",13))
    names.setdefault(o.normalized("Герой"),("Герой",13))
    values=sorted(names.values(),key=lambda p:o.normalized(p[0]))
    page_rows=values[(page-1)*25:page*25]
    lines=["Энциклопедия опубликованных персонажей:"]+[f"{name} — последнее доступное свидетельство: глава {n}" for name,n in page_rows]
    if page==1:
        lines.extend(["\nКанонические законы:"]+[f"Глава {n}: {label}" for _,n,label in ge.RULES])
        lines.append("Девять сил: "+", ".join(ge.POWERS))
        places=[x for x in ge.state(db)["places"] if source_visible(db,x["chapter"])]
        lines.extend(f"Место: {x['name']} — {x['description']} (глава {x['chapter']})" for x in places[-10:])
    return "\n".join(lines) if page_rows or page==1 else "Нет записей на этой странице."

def character_text(db,name):
    key=o.normalized(name);lines=[]
    if key in ("хакурэя","императрица","герой","герой легенды"):
        ids=("origin","nine","touch","warmth","choice","return") if key in ("хакурэя","императрица") else ("immunity","choice")
        lines.extend(f"Канон, глава {n}: {label}" for k,n,label in ge.RULES if k in ids)
    for actor in gu.CAST:
        if o.normalized(actor[1])==key:
            lines.append("Установленный профиль хранительницы (план саги, не опубликованное событие): "+actor[4]+"; голос: "+actor[7])
    for n,did in db.execute("SELECT number,draft_id FROM omega_index WHERE draft_id IS NOT NULL ORDER BY number"):
        if not source_visible(db,n):continue
        w=ge.world(db,did)
        if not w:continue
        for p in w["characters"]:
            if o.normalized(p["name"])==key:
                lines.append(f"Глава {n}: {p['portrait']}; мотив: {p['motive']}; происхождение: {p['lineage']}. «{p['evidence']}»")
    facts,_,_=ledger(public_rows(db))
    labels={"identity":"Личность","origin":"Происхождение","age":"Возраст","location":"Местоположение","voice":"Голос","knowledge":"Знание/незнание","relationship":"Отношения","trait":"Характер","goal":"Цель","biography":"Биография","power":"Сила","limit":"Предел","law":"Закон","letter":"Письмо","tradition":"Традиция"}
    visible=[x for x in facts.values() if o.normalized(x["subject"])==key and x["kind"] in labels]
    for f in sorted(visible,key=lambda x:x["chapter"]):
        lines.append(f"Глава {f['chapter']}: {labels[f['kind']]} — {f['value']} «{f['quote']}»")
    if not any(f["kind"]=="age" for f in visible):lines.append("Точный возраст: не установлен в доступных записях.")
    if not any(f["kind"]=="knowledge" for f in visible):lines.append("Знания: нет подтверждённой записи; это не означает незнания.")
    return "Персонаж: "+name+"\n\n"+"\n\n".join(lines[-24:])

def threads_text(db):
    _,threads,_=ledger(public_rows(db))
    lines=[f"{t['subject']} · {t['kind']}: {t['value']} (глава {t['chapter']}, "+("закрыто в главе "+str(t["closed"]) if t["closed"] else "открыто")+")" for t in threads.values()]
    for k,t in heart.threads(db).items():
        if source_visible(db,t["opened"]) and (t["closed"] is None or not source_visible(db,t["closed"])):
            lines.append(f"Любовная линия: {t['title']} (глава {t['opened']})")
    for f in ev.state(db,[(n,did,p) for n,did,p in ev.published(db) if source_visible(db,n)]).values():
        if f["kind"] in ("promise","conflict","thread") and f["state"]=="open":lines.append(f"{f['subject']}: {f['detail']} (глава {f['chapter']})")
    for k,t in o.mysteries(db).items():
        if source_visible(db,t["opened"]) and (t["closed"] is None or not source_visible(db,t["closed"])):lines.append(f"Загадка: {t['question']} (глава {t['opened']})")
    return "Реестр доступных сюжетных линий:\n"+"\n".join(lines[:40]) if lines else "Нет доступных открытых линий."

def quality_text(db):
    rows=public_rows(db)[-12:]
    return "Формальные литературные показатели (не оценка смысла):\n"+"\n".join(
       f"Глава {n}: эмоции {p['quality']['emotion_markers']}, решения {p['quality']['decision_markers']}, диалог {p['quality']['dialogue_lines']}, напряжение {p['quality']['tension']}/100"
       for n,_,p in rows) if rows else "Отчётов о доступных главах ещё нет."

def graph(db):
    # Reuse canonical protagonist, love and guardian hubs; keep new nodes bounded and spoiler-filtered.
    nodes=[];edges=[];seen=set();last_hero="character:hero"
    guardians={o.normalized(x[1]):"guardian:"+x[0] for x in gu.CAST}
    # Existing character nodes are reused whenever available.
    existing={}
    evolution_rows=[] if ev.audit(db) else list(ev.published(db))[-60:]
    for n,did,p in evolution_rows:
        if source_visible(db,n):
            for f in p["facts"]:
                key=o.normalized(f["subject"]);existing[key]="evolution:subject:"+o.digest(key)[:20]
    for n,did in db.execute("SELECT number,draft_id FROM omega_index ORDER BY number DESC LIMIT 24"):
        if did is None or not source_visible(db,n):continue
        m=o.metadata(db,did)
        if m:
            for event in m["data"]["events"]:
                for name in event["characters"]:
                    key=o.normalized(name);existing.setdefault(key,"actor:"+o.digest(key)[:20])
    def node(k,label,kind,area=None):
        if k not in seen:
            seen.add(k);item={"key":k,"group":4,"kind":kind,"content":label,"created":"","order":len(nodes)}
            if area:item["infinite_group"]=area
            nodes.append(item)
    def edge(a,b,kind):
        if a and b and a!=b:edges.append({"a":a,"b":b,"kind":kind})
    def hub(name):
        key=o.normalized(name)
        if key in ("герой","герой легенды"):return "character:hero"
        if key in ("хакурэя","императрица"):return "character:empress"
        if key in guardians:return guardians[key]
        k=existing.get(key) or "infinite:character:"+o.digest(key)[:20]
        if key not in existing:node(k,name,"infinite_character",k)
        edge("infinite:root",k,"infinite_character")
        return k
    node("infinite:root","Бесконечная судьба","infinite_root","infinite:root")
    edge("evolution:root","infinite:root","infinite_branch")
    edge("infinite:root","character:hero","infinite_hero")
    for n in (5,6,9,10,11,12,13):edge(f"canon:{n}","character:hero","infinite_hero")
    if audit(db):return nodes,edges
    visible_rows=public_rows(db)
    _,visible_threads,_=ledger(visible_rows)
    for n,did,p in visible_rows[-100:]:
        if p["step"]:
            k=f"infinite:stage:{p['step']}"
            node(k,stage(p["step"])["title"],"infinite_stage","infinite:root")
            edge("infinite:root",k,"infinite_branch");edge(f"c:{did}",k,"infinite_source")
            if stage(p["step"])["theme"]=="love":edge("heart:root",k,"infinite_love")
        for j,f in enumerate(p["facts"]):
            k=f"infinite:fact:{did}:{j}";subject=hub(f["subject"])
            kind="infinite_hero" if subject=="character:hero" else "infinite_love" if f["kind"] in ("letter","tradition","relationship") and subject=="character:empress" else "infinite_fact"
            node(k,f["value"],kind,"heart:root" if kind=="infinite_love" else subject)
            if f["kind"]=="clue" and visible_threads.get(fact_key(f),{}).get("closed") is None:nodes[-1]["mystery_open"]=True
            edge(subject,k,kind);edge(f"c:{did}",k,"infinite_source")
            if kind=="infinite_hero":
                edge(last_hero,k,"infinite_hero");last_hero=k
            if kind=="infinite_love":edge("heart:root",k,"infinite_love")
            if f["cause"] is not None and source_visible(db,f["cause"]):
                across=o.volume(f["cause"])!=o.volume(n)
                edge(source_key(db,f["cause"]),k,"infinite_cross_volume" if across else "infinite_cause")
                if across:edge("book:"+str(o.volume(f["cause"])),"book:"+str(o.volume(n)),"infinite_cross_volume")
    # Real older literary causes also connect volumes without duplicating the event node.
    for n,did in db.execute("SELECT number,draft_id FROM omega_index WHERE draft_id IS NOT NULL ORDER BY number DESC LIMIT 120"):
        if not source_visible(db,n):continue
        m=o.metadata(db,did)
        if not m:continue
        for e in m["data"]["events"]:
            cause=e["cause"]
            if cause is not None and source_visible(db,cause) and o.volume(cause)!=o.volume(n):
                edge(source_key(db,cause),f"c:{did}","infinite_cross_volume")
                edge("book:"+str(o.volume(cause)),"book:"+str(o.volume(n)),"infinite_cross_volume")
            # Named, published appearances also feed the same character constellations.
            for name in e["characters"]:
                actor=hub(name);edge(actor,f"c:{did}","infinite_hero" if actor=="character:hero" else "infinite_character")
    return nodes,edges
