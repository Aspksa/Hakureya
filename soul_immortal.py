"""Immortal Chronicle: fictional source-linked narrative continuity, no network calls."""
import json
import re
from collections import Counter
import soul_omega as o
import soul_evolution as ev

VERSION=1
SAGAS=(
("bride","Невеста девяти небес","love","Хакурэя обдумывает добровольный брак; не считай свадьбу состоявшейся без согласия обоих. Двор и хранительницы имеют разные ожидания."),
("rebellion","Восстание бессмертных","court","Боги оспаривают последствия реформы; у каждого мотив, переговоры и цена решений."),
("white","Тайна белого созвездия","mystery","Связь истоков героя и Хакурэи исследуется через улики, не переписывай канон."),
("sisters","Девять сестёр вечности","guardians","Предыстория знакомства девяти хранительниц; разные голоса, не меняй их установленные истории."),
("human","Императрица человеческого мира","growth","Жизнь среди людей, человеческие привычки и ответственность за двор."),
("letters","Письма сквозь тысячелетия","mystery","Давняя переписка, проверка подлинности и последствия; не меняй прошлое."),
("void","Последний бог пустоты","power","Существо не подчиняется известной магии; у дара героя есть предел и цена."),
("garden","Сад двух сердец","love","Совместное создание волшебного сада, традиции, добровольные решения."),
("moon","Загадка исчезнувшей луны","world","Неизвестная вселенная с собственными законами, исследование и судьба жителей."),
("eternity","Вечность начинается сегодня","love","Новый этап совместной жизни и открытый выбор будущего, не окончательный финал.")
)
DAILY=(
("Дневник и доверие","Хранительницы случайно находят дневник, но уважают приватность."),
("Кулинарный секрет","Хакурэя учится готовить новое блюдо для любимого, с добрым юмором."),
("Подарок без титула","Императрица выбирает подарок в обычном магазине."),
("Девять идей свидания","Хранительницы предлагают разные идеи и спорят, не решая за пару."),
("Драгоценное время","Хакурэя меняет необязательное расписание ради совместного вечера."),
("Берег волшебного океана","Отдых и открытие, взаимная забота."),
("Человеческие технологии","Забавное недоразумение и обучение без унижения."),
("Письмо в дорогу","Романтическая переписка во время разлуки."),
("Общая традиция","Новая семейная традиция как результат совместного выбора."),
("Два лица императрицы","Контраст совета и дома без потери достоинства и самостоятельности.")
)
PHASES=("завязка и личная цель","улика и осложнение","пересечение с другой линией, выбор","кульминация и последствия")
# Interleave groups of two sagas, add one daily scene after each group's midpoint and finale.
ORDER=tuple(x for i in range(0,10,2) for x in
 ((i,0),(i+1,0),(i,1),(i+1,1),(10+i,0),(i,2),(i+1,2),(i,3),(i+1,3),(11+i,0)))
KINDS=("clue","reveal","law","consequence","love","journey","opponent","knowledge")
def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS immortal_records(
      draft_id INTEGER PRIMARY KEY, payload TEXT NOT NULL, source_hash TEXT NOT NULL, checksum TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS immortal_preferences(id INTEGER PRIMARY KEY CHECK(id=1), length TEXT NOT NULL, idle INTEGER NOT NULL)""")
    db.execute("INSERT OR IGNORE INTO immortal_preferences VALUES(1,'обычная',1200)")

def read(db,did):
    row=db.execute("SELECT payload,source_hash,checksum FROM immortal_records WHERE draft_id=?",(did,)).fetchone()
    if not row:return None
    raw,source,h=row
    d=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()
    if not d or d[0]!=source or o.digest(o.dump([raw,source]))!=h:raise ValueError("damaged immortal record")
    p=json.loads(raw)
    if p.get("version")!=VERSION:raise ValueError("immortal version")
    return p

def published(db):
    for n,did in db.execute("""SELECT a.number,r.draft_id FROM immortal_records r JOIN saga_arcs a ON a.draft_id=r.draft_id
      JOIN chronicle_drafts d ON d.id=r.draft_id WHERE d.status='approved' ORDER BY a.number"""):
        yield n,did,read(db,did)

def audit(db):
    try:
        completed=[tuple(p["step"]) for _,_,p in published(db) if p["step"] is not None]
        if completed!=list(ORDER[:len(completed)]):raise ValueError("sequence")
    except (ValueError,TypeError,KeyError):return ["Повреждены записи Immortal Chronicle"]
    return []

def ready(db):
    return ev.ready(db) and not ev.audit(db) and {p["scene"] for _,_,p in ev.published(db) if p.get("completed")} >= {n for n,_,_,_ in ev.SCENES}

def state(rows):
    clues={};laws={}
    for n,_,p in rows:
        for f in p["facts"]:
            k=f["key"]
            if f["kind"]=="clue":clues[k]={**f,"chapter":n,"closed":None}
            if f["kind"]=="reveal":clues[k]["closed"]=n
            if f["kind"]=="law":laws[k]={**f,"chapter":n}
    return clues,laws

def preferences(db):
    return db.execute("SELECT length,idle FROM immortal_preferences WHERE id=1").fetchone()

def enrich(db,plan):
    rows=list(published(db))
    done=sum(p["step"] is not None for _,_,p in rows)
    fixed=any(k in plan for k in ("shadow","guardians","destiny")) or plan["arc"]!="future" or "cycle_id" in plan.get("romance",{})
    step=ORDER[done] if not fixed and ready(db) and done<len(ORDER) else None
    chosen=None
    if step:
        i,phase=step
        if i<10:
            key,title,theme,guide=SAGAS[i]
            chosen={"key":key,"title":title,"theme":theme,"phase":PHASES[phase],"guide":guide}
        else:
            title,guide=DAILY[i-10]
            chosen={"key":"daily","title":title,"theme":"love","phase":"самостоятельная сцена","guide":guide}
    clues,laws=state(rows)
    latest=db.execute("SELECT COALESCE(MAX(number),13) FROM omega_index").fetchone()[0]
    open_clues=[v for v in clues.values() if v["closed"] is None]
    mature=[v for v in open_clues if latest+1-v["chapter"]>=v["delay"]]
    # Keep context bounded. No new actual facts until approved.
    recent=rows[-5:]
    theme_counts=Counter(p["theme"] for _,_,p in recent)
    pacing="последствия и передышка" if recent and sum(p["quality"]["tension"] for _,_,p in recent)/len(recent)>65 else "новое препятствие с логичной причиной"
    if chosen:
        # Evolution has finished, so this director replaces only its generic fallback.
        if "evolution" in plan:
            plan["evolution"]["chosen"]={"scene":0,"theme":chosen["theme"],"title":chosen["title"],"guide":chosen["guide"]}
            plan["evolution"]["alternatives"]=[]
    plan["immortal"]={"step":list(step) if step else None,"chosen":chosen,"pacing":pacing,
      "theme_counts":dict(theme_counts),"open_clues":open_clues[-3:],"mature_clues":mature[-3:],
      "laws":list(laws.values())[-4:],"length":preferences(db)[0],
      "recent":[{"chapter":n,"step":p["step"],"facts":p["facts"][:1]} for n,_,p in recent]}
    return plan

def instruction(plan):
    p=plan.get("immortal")
    if not p:return ""
    return (" Immortal Chronicle — литературный замысел: "+o.dump(p)+
      ". Приоритет у обязательных этапов предыдущих саг; новая линия применяется лишь если chosen не null. "
      "Чередуй любовную повседневность, юмор, политику и приключения. Противники — самостоятельные герои с убедительной целью. "
      "Сажай подсказки заранее; не раскрывай незрелые тайны. Пересечение линий имеет причину, а не случайное совпадение. "
      "Редактор внутри этого же ответа проверяет русскую прозу, индивидуальные голоса, подтекст, мотивы, логику магии и повторения. "
      "Длина сцены: короткая — стремись к 180–250 словам, обычная — 300–450, большая — 450–600, но не превышай общий лимит JSON. "
      "Не обрывай предложение. Опционально immortal:{step,evidence,facts:[{kind,key,detail,evidence,cause,delay}]}. "
      "step — точный массив выбранного этапа при завершении, иначе null; evidence — дословная цитата 12–240 символов, иначе пустая строка. "
      "До двух facts, kind из "+", ".join(KINDS)+"; key — стабильный латинский идентификатор 2–40 символов; detail — вывод; evidence — точная цитата; "
      "cause — номер опубликованной главы или null; delay — 3..40 глав для clue, иначе 0. Для reveal укажи key открытой зрелой подсказки и cause её главы. "
      "Для law не меняй значение установленного закона. При нехватке места пропусти метаданные, но не художественную сцену и обязательную отметку старой саги.")

def quality(story):
    words=re.findall(r"\w+",story.casefold())
    counts=Counter(words)
    sentences=[s.strip() for s in re.split(r"[.!?…]+",story) if s.strip()]
    repeated=sum(n-1 for s,n in Counter(sentences).items() if len(s)>35 and n>1)
    tension=sum(any(w.startswith(k) for k in ("опасн","страх","враг","удар","угроз","разлом","сраж","тревог")) for w in words)
    dialogue=sum(line.lstrip().startswith("—") for line in story.splitlines())
    warnings=[]
    if repeated:warnings.append("повтор предложений")
    if len(words)<180:warnings.append("короткая сцена")
    if not dialogue and "—" not in story:warnings.append("нет явного диалога")
    if any(len(s.split())>65 for s in sentences):warnings.append("очень длинное предложение")
    return {"words":len(words),"tension":min(100,round(1200*tension/max(1,len(words)))),"dialogue_lines":dialogue,
      "lexical_diversity":round(len(counts)/max(1,len(words)),3),"warnings":warnings}

def save(db,did,story,raw,plan):
    p=plan.get("immortal")
    if not p:
        if raw is not None:raise ValueError("unexpected immortal fields")
        return
    if raw is None:raw={"step":None,"evidence":"","facts":[]}
    if not isinstance(raw,dict) or set(raw)!={"step","evidence","facts"}:raise ValueError("invalid immortal fields")
    step=raw["step"];evidence=raw["evidence"]
    if step is not None:
        if not isinstance(step,list) or len(step)!=2 or any(type(x) is not int for x in step) or step!=p["step"]:raise ValueError("wrong immortal step")
        evidence=o.clean(evidence,12,240)
        if evidence not in story:raise ValueError("immortal excerpt absent")
    elif evidence!="":raise ValueError("unexpected evidence")
    rows=list(published(db));clues,laws=state(rows)
    latest=db.execute("SELECT COALESCE(MAX(number),13) FROM omega_index").fetchone()[0]+1
    facts=raw["facts"];out=[];seen=set()
    if not isinstance(facts,list) or len(facts)>2:raise ValueError("invalid facts")
    for f in facts:
        if not isinstance(f,dict) or set(f)!={"kind","key","detail","evidence","cause","delay"} or f["kind"] not in KINDS:raise ValueError("invalid fact")
        kind,key,cause,delay=f["kind"],f["key"],f["cause"],f["delay"]
        if not isinstance(key,str) or not re.fullmatch(r"[a-z0-9-]{2,40}",key) or key in seen:raise ValueError("invalid key")
        seen.add(key)
        detail=o.clean(f["detail"],8,180);quote=o.clean(f["evidence"],12,240)
        if quote not in story:raise ValueError("fact not quoted")
        if cause is not None and (type(cause) is not int or not db.execute("SELECT 1 FROM omega_index WHERE number=?",(cause,)).fetchone()):raise ValueError("unknown cause")
        if type(delay) is not int or (not 3<=delay<=40 if kind=="clue" else delay!=0):raise ValueError("invalid delay")
        if kind=="clue" and key in clues:raise ValueError("duplicate clue")
        if kind=="reveal" and (key not in clues or clues[key]["closed"] is not None or cause!=clues[key]["chapter"] or latest-cause<clues[key]["delay"]):raise ValueError("premature revelation")
        if kind=="law" and key in laws and o.normalized(detail)!=o.normalized(laws[key]["detail"]):raise ValueError("magic law contradiction")
        out.append({"kind":kind,"key":key,"detail":detail,"evidence":quote,"cause":cause,"delay":delay})
    theme=(p["chosen"] or {}).get("theme") or plan.get("evolution",{}).get("chosen",{}).get("theme","fixed")
    payload=o.dump({"version":VERSION,"step":step,"evidence":evidence,"theme":theme,"facts":out,"quality":quality(story)})
    source=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()[0]
    db.execute("INSERT INTO immortal_records VALUES(?,?,?,?)",(did,payload,source,o.digest(o.dump([payload,source]))))

def validate_approval(db,did):
    p=read(db,did)
    if not p or p["step"] is None:return
    if audit(db) or not ready(db):raise ValueError("immortal prerequisites")
    done=sum(x["step"] is not None for _,_,x in published(db))
    if done>=len(ORDER) or p["step"]!=list(ORDER[done]):raise ValueError("immortal sequence")

def status(db):
    if audit(db):return "Сага повреждена."
    done=sum(p["step"] is not None for _,_,p in published(db))
    return f"Immortal Chronicle: {done}/{len(ORDER)} этапов. "+("Новые линии открыты." if ready(db) else "Продолжает предыдущие саги.")

def quality_text(db,volume=None):
    rows=[(n,p["quality"]) for n,_,p in published(db) if volume is None or o.volume(n)==volume]
    if not rows:return "Нет литературных отчётов."
    if volume is not None:
        avg=sum(q["tension"] for _,q in rows)/len(rows)
        return f"Том {volume}: {len(rows)} сцен, {sum(q['words'] for _,q in rows)} слов; средний индекс напряжения {avg:.0f}/100 (лексическая эвристика)."
    return "Локальные литературные показатели (не смысловой редактор):\n"+"\n".join(f"{n}: {q['words']} слов; напряжение {q['tension']}/100; "+(", ".join(q["warnings"]) or "явных формальных замечаний нет") for n,q in rows[-10:])

def graph(db):
    nodes=[];edges=[];seen=set()
    def node(k,label,kind,slot):
        if k not in seen:
            seen.add(k);nodes.append({"key":k,"group":4,"content":label,"kind":kind,"created":"","order":len(nodes),"immortal_slot":slot})
    node("immortal:root","Immortal Chronicle","immortal_root",-1)
    edges.append({"a":"evolution:root","b":"immortal:root","kind":"immortal_branch"})
    if audit(db):return nodes,edges
    rows=list(published(db))[-100:];previous={}
    for n,did,p in rows:
        if not ev.readable(db,n):continue
        if p["step"] is not None:
            i,phase=p["step"];title=SAGAS[i][1] if i<10 else DAILY[i-10][0]
            hub=f"immortal:saga:{i}";node(hub,title,"immortal_saga",i*8)
            k=f"immortal:stage:{i}:{phase}";node(k,title+" · "+str(phase+1),"immortal_stage",i*8+phase+1)
            edges.extend([{"a":"immortal:root","b":hub,"kind":"immortal_branch"},{"a":hub,"b":k,"kind":"immortal_stage"},{"a":f"c:{did}","b":k,"kind":"immortal_source"}])
            if i in previous:edges.append({"a":previous[i],"b":k,"kind":"immortal_consequence"})
            previous[i]=k
        for j,f in enumerate(p["facts"]):
            key=f"immortal:fact:{did}:{j}";node(key,f["detail"],"immortal_fact",160+(did-1)*2+j)
            edges.extend([{"a":"immortal:root","b":key,"kind":"immortal_branch"},{"a":f"c:{did}","b":key,"kind":"immortal_"+f["kind"]}])
            if f["cause"] is not None and ev.readable(db,f["cause"]):
                r=db.execute("SELECT draft_id FROM omega_index WHERE number=?",(f["cause"],)).fetchone()
                edges.append({"a":f"c:{r[0]}" if r and r[0] is not None else f"canon:{f['cause']}","b":key,"kind":"immortal_consequence"})
    return nodes,edges
