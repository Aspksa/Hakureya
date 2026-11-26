"""Fiction-only evolution. Published source text is immutable."""
import json
import re
from collections import Counter
import soul_omega as o
import soul_guardians as gu
import soul_destiny as de
import soul_shadow as sh

VERSION=1
# Numbering preserves the approved design. These are proposals, not established events.
SCENES=(
(11,"love","Настоящий отпуск","Императрица распределяет обязанности и впервые отдыхает без чувства вины."),
(12,"love","Дом за пределами дворца","Пара выбирает тихое место, обустраивает его вместе; забота не отменяет обязанностей."),
(13,"love","Свидание по её замыслу","Хакурэя сама готовит необычное свидание."),
(14,"love","Удивить без магии","Неловкая человеческая задача, юмор и тёплый результат."),
(15,"love","Спор и примирение","Реальное разногласие, честный разговор, ответственность и взаимное решение."),
(16,"growth","Собственное увлечение","Хакурэя находит занятие, интересное ей самой."),
(17,"love","Дневник любви","Личная художественная запись о событии и его значении."),
(18,"world","Два вымышленных имени","Путешествие инкогнито, незнакомая культура и последствия."),
(19,"growth","Человеческий праздник","Новая традиция, открытие и участие хранительниц."),
(20,"love","История общего дома","Семейные традиции вымышленной пары, взаимный выбор."),
(21,"guardians","Девять личных дорог","Одна хранительница самостоятельно выбирает цель."),
(22,"guardians","До императорской службы","Её прошлое через воспоминание, не меняющее канон."),
(23,"guardians","Скрытая мечта","Её страх или мечта влияют на решение."),
(24,"guardians","Поручение в чужом мире","Самостоятельное задание и цена выбора."),
(25,"guardians","Состязание подруг","Дружеское соперничество меняет отношения."),
(26,"guardians","Совет о счастье госпожи","Разные мнения о поддержке императрицы без нарушения приватности."),
(27,"guardians","Неудачный сюрприз","Добрый юмор и помощь в романтических делах."),
(28,"guardians","Давний противник","Возвращается соперник одной хранительницы с собственной целью."),
(29,"guardians","Новый предел дара","Производная магия одной хранительницы и её предел."),
(30,"guardians","Девять взглядов","Одна глава глазами выбранной хранительницы."),
(31,"power","Новое свойство пространства","Новый ограниченный эффект уже пробуждённого дара."),
(32,"power","До рождения пространства","Древнее свидетельство, не окончательная истина."),
(33,"mystery","Неизвестный символ","Улика, связанная с героем; оставь проверяемый вопрос."),
(34,"power","Исток невосприимчивости","Развитие установленной загадки без переписывания рождения героя."),
(35,"power","Испытание вместе","Контроль дара, наблюдение и ограничение."),
(36,"world","Граница известных законов","Мир с отличными правилами; выбор и последствия."),
(37,"court","Исследователи неизвестного","Противники пытаются понять дар; разные мотивы."),
(38,"love","Две судьбы","Связь судьбы пары через свидетельства, без предопределённого принуждения."),
(39,"mystery","Хранитель запретных знаний","Новый независимый герой и ограниченное знание."),
(40,"power","Истоки и пределы","Раскрой часть происхождения дара на основании прежних улик."),
(41,"world","Империя чёрной луны","Независимая внешняя цивилизация, культура и дипломатия."),
(42,"court","Забытый трон","Исчезнувший правитель возвращается; последствия для подданных."),
(43,"world","Сад остановившегося времени","Утраченные воспоминания, не возможность менять прошлое."),
(44,"mystery","Дворец тысячи зеркал","Возможные судьбы, не обязательное будущее."),
(45,"power","Небесный турнир","Магическое состязание, ограничения и уважение соперников."),
(46,"court","Война пророчеств","Противоречащие предсказания, дипломатия и ответственность."),
(47,"world","Потерянное созвездие","Расследование исчезновения цивилизации."),
(48,"growth","Императрица без имени","Мир без императорского статуса; самостоятельный поступок."),
(49,"mystery","Последняя библиотека вечности","Свидетельства происхождения миров, не переписывание канона."),
(50,"love","Два сердца за пределами времени","Романтическое путешествие с самостоятельными решениями обоих.")
)
THEMES=("love","guardians","power","world","court","mystery","growth","character")
FIELDS=("goal","fear","belief","voice","promise","conflict","relationship","secret","knowledge","consequence","culture","law","artifact","tradition","thread")
FORMATS={"короткая":750,"обычная":2000,"большая":4000,"романтическая":3000}
STYLES={"баланс":"чередуй диалог, действие, атмосферу и внутренний мир","романтика":"больше нежности, подтекста и совместных решений","приключения":"больше открытий, движения и последствий","интриги":"больше дипломатии, неоднозначных мотивов и улик"}
def init(db):
    db.execute("CREATE TABLE IF NOT EXISTS evolution_settings(id INTEGER PRIMARY KEY CHECK(id=1), style TEXT NOT NULL, spoilers INTEGER NOT NULL CHECK(spoilers IN (0,1)))")
    db.execute("INSERT OR IGNORE INTO evolution_settings VALUES(1,'баланс',1)")
    db.execute("CREATE TABLE IF NOT EXISTS evolution_records(draft_id INTEGER PRIMARY KEY, payload TEXT NOT NULL, source_hash TEXT NOT NULL, checksum TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS evolution_read(number INTEGER PRIMARY KEY)")
    db.execute("CREATE TABLE IF NOT EXISTS evolution_preferences(theme TEXT PRIMARY KEY, weight INTEGER NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS evolution_budget(id INTEGER PRIMARY KEY CHECK(id=1), model TEXT NOT NULL, input_rate INTEGER NOT NULL, output_rate INTEGER NOT NULL, monthly_kopecks INTEGER NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS evolution_cost(day TEXT PRIMARY KEY, model TEXT NOT NULL, estimate_kopecks INTEGER NOT NULL, actual_kopecks INTEGER, input_rate INTEGER NOT NULL, output_rate INTEGER NOT NULL)")

def read(db,did):
    row=db.execute("SELECT payload,source_hash,checksum FROM evolution_records WHERE draft_id=?",(did,)).fetchone()
    if not row:return None
    raw,source,check=row
    d=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()
    if not d or d[0]!=source or o.digest(o.dump([raw,source]))!=check:raise ValueError("damaged evolution record")
    p=json.loads(raw)
    if p.get("version")!=VERSION:raise ValueError("evolution version")
    return p

def published(db):
    for n,did in db.execute("""SELECT a.number,r.draft_id FROM evolution_records r JOIN saga_arcs a ON a.draft_id=r.draft_id
      JOIN chronicle_drafts d ON d.id=r.draft_id WHERE d.status='approved' ORDER BY a.number"""):
        yield n,did,read(db,did)

def audit(db):
    try:
        for _ in published(db):pass
    except (ValueError,TypeError,KeyError):return ["Повреждены записи Eternal Evolution"]
    return []

def ready(db):
    return not (de.audit(db) or sh.audit(db) or gu.audit(db)) and de.ready(db) and len(de.published(db))==len(de.ORDER)

def settings(db):
    return db.execute("SELECT style,spoilers FROM evolution_settings WHERE id=1").fetchone()

def style(db,value):
    if value not in STYLES:raise ValueError("style")
    db.execute("UPDATE evolution_settings SET style=? WHERE id=1",(value,))

def preference(db,theme):
    if theme not in THEMES:raise ValueError("theme")
    db.execute("INSERT INTO evolution_preferences VALUES(?,1) ON CONFLICT(theme) DO UPDATE SET weight=MIN(5,weight+1)",(theme,))

def state(db,rows=None):
    rows=list(published(db)) if rows is None else rows
    result={}
    for n,_,p in rows:
        for f in p["facts"]:
            key=(o.normalized(f["subject"]),f["kind"],o.normalized(f["key"]))
            result[key]=dict(chapter=n,**f)
    return result

def candidates(db,rows):
    used={p["scene"] for _,_,p in rows if p.get("completed",False)}
    recent=Counter(p["theme"] for _,_,p in rows[-8:])
    prefs=dict(db.execute("SELECT theme,weight FROM evolution_preferences"))
    pool=[{"scene":n,"theme":t,"title":title,"guide":guide} for n,t,title,guide in SCENES if n not in used]
    if not pool:
        # Continuing scenarios remain proposals. Distinct historical context drives the next arc.
        pool=[{"scene":0,"theme":t,"title":"Новая линия: "+t,"guide":"Развивай новую причинно связанную историю в этой теме, не повторяя завершённые события."} for t in THEMES]
    return sorted(pool,key=lambda p:(-prefs.get(p["theme"],0)+recent[p["theme"]]*3,p["scene"],p["theme"]))

def enrich(db,plan):
    rows=list(published(db));fixed=any(k in plan for k in ("shadow","guardians","destiny")) or plan["arc"]!="future" or "cycle_id" in plan.get("romance",{})
    unlocked=not fixed and ready(db)
    proposals=candidates(db,rows)[:3] if unlocked else []
    chosen=proposals[0] if proposals else {"scene":0,"theme":"fixed" if fixed else "growth","title":"Текущий эпизод","guide":"Не изменяй выбранную сагу."}
    facts=sorted(state(db,rows).values(),key=lambda x:x["chapter"],reverse=True)
    obligations=[f for f in facts if f["kind"] in ("promise","conflict","thread") and f["state"]=="open"][:4]
    secrets=[f for f in facts if f["kind"]=="secret"][:4]
    cast=[{"name":p[1],"character":p[4],"voice":p[7],"goal":p[9]} for p in gu.CAST]
    focus=cast[sum(p["theme"]=="guardians" for _,_,p in rows)%9] if unlocked and chosen["theme"]=="guardians" else None
    latest=db.execute("SELECT COALESCE(MAX(number),13) FROM omega_index").fetchone()[0]
    n=latest+1
    plan["evolution"]={"chosen":chosen,"alternatives":proposals[1:],"style":STYLES[settings(db)[0]],
      "volume":o.volume(n),"phase":("завязка" if (n-14)%12<3 else "развитие" if (n-14)%12<9 else "кульминация и последствия"),
      "obligations":obligations,"secrets":secrets,"context":facts[:6],"focus":focus,"unlocked":unlocked}
    return plan

def instruction(plan):
    p=plan.get("evolution")
    if not p:return ""
    return (" Eternal Evolution: "+o.dump(p)+
      ". Текущий обязательный этап имеет приоритет. Альтернативы — будущие возможности, не события. "
      "Причина, цель, препятствие, выбор и последствие важнее красивого перечня. Учитывай обещания, конфликты, точку зрения, отдельные знания героев. "
      "Сохраняй русский литературный стиль, эмоциональный подтекст и разные голоса. Не раскрывай тайны раньше разрешённого этапа. "
      "Внутри одного ответа выполни саморедактуру, убери повторы, не выводи ход рассуждений. "
      "Необязательный evolution:{scene,evidence,facts:[{kind,subject,key,detail,evidence,cause,state,knows}]}, до двух фактов. "
      "scene — номер выбранной сцены только при её завершении, иначе 0; evidence — точная цитата из story при завершённой сцене, иначе пустая строка. "
      "kind из "+", ".join(FIELDS)+"; subject — имя или название из цитаты, key — стабильный короткий идентификатор, detail — краткий вывод, "
      "evidence — дословная цитата 12–240 символов, cause — номер опубликованной главы или null, state — open/closed для promise/conflict/thread, иначе known. "
      "knows — до четырёх имён персонажей из цитаты только для secret/knowledge, иначе []. "
      "Закрывай только ранее открытое обязательство. При нехватке места пропусти evolution, но сохрани основной текст и метаданные саги.")

def save(db,did,story,raw,plan):
    p=plan.get("evolution")
    if not p:
        if raw is not None:raise ValueError("unexpected evolution")
        return
    facts=[] if raw is None else raw.get("facts") if isinstance(raw,dict) and set(raw) in ({"facts"},{"scene","evidence","facts"}) else None
    scene=raw.get("scene",0) if isinstance(raw,dict) else 0
    evidence=raw.get("evidence","") if isinstance(raw,dict) else ""
    if type(scene) is not int or (scene!=0 and (not p["unlocked"] or scene!=p["chosen"]["scene"])):raise ValueError("wrong evolution scene")
    if scene:
        evidence=o.clean(evidence,12,240)
        if evidence not in story:raise ValueError("unverified scene")
    elif evidence!="":raise ValueError("unexpected scene evidence")
    if not isinstance(facts,list) or len(facts)>2:raise ValueError("invalid evolution facts")
    existing=state(db);out=[]
    for f in facts:
        if not isinstance(f,dict) or set(f)!={"kind","subject","key","detail","evidence","cause","state","knows"} or f["kind"] not in FIELDS:raise ValueError("invalid fact")
        kind=f["kind"];subject=o.clean(f["subject"],2,60);key=o.clean(f["key"],2,50)
        quote=o.clean(f["evidence"],12,240);detail=o.clean(f["detail"],8,180)
        if quote not in story or o.normalized(subject) not in o.normalized(quote):raise ValueError("unverified subject")
        cause=f["cause"];status=f["state"];knows=f["knows"]
        if cause is not None and (type(cause) is not int or not db.execute("SELECT 1 FROM omega_index WHERE number=?",(cause,)).fetchone()):raise ValueError("invalid cause")
        k=(o.normalized(subject),kind,o.normalized(key))
        if kind in ("promise","conflict","thread"):
            if status not in ("open","closed"):raise ValueError("invalid obligation")
            if status=="closed" and (k not in existing or existing[k]["state"]!="open" or cause!=existing[k]["chapter"]):raise ValueError("obligation not open")
        elif status!="known":raise ValueError("invalid state")
        if not isinstance(knows,list) or len(knows)>4 or (knows and kind not in ("secret","knowledge")):raise ValueError("invalid knowledge")
        knows=[o.clean(x,2,60) for x in knows]
        if any(o.normalized(x) not in o.normalized(quote) for x in knows):raise ValueError("unverified witness")
        if k in [(o.normalized(x["subject"]),x["kind"],o.normalized(x["key"])) for x in out]:raise ValueError("duplicate fact")
        out.append({"kind":kind,"subject":subject,"key":key,"detail":detail,"evidence":quote,"cause":cause,"state":status,"knows":knows})
    chosen=p["chosen"];raw=o.dump({"version":VERSION,"scene":scene,"completed":bool(scene),"evidence":evidence,"theme":chosen["theme"],"facts":out})
    source=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()[0]
    db.execute("INSERT INTO evolution_records VALUES(?,?,?,?)",(did,raw,source,o.digest(o.dump([raw,source]))))

def mark_read(db,n):
    db.execute("INSERT OR IGNORE INTO evolution_read VALUES(?)",(n,))

def readable(db,n):
    return not settings(db)[1] or db.execute("SELECT 1 FROM evolution_read WHERE number=?",(n,)).fetchone() is not None

def profile(db,name):
    if audit(db):return "Записи персонажей повреждены."
    facts=[f for f in state(db).values() if o.normalized(f["subject"])==o.normalized(name) and readable(db,f["chapter"])]
    return "\n\n".join(f"Глава {f['chapter']}: {f['kind']} — {f['detail']} «{f['evidence']}»" for f in facts[-20:]) or "Нет доступных прочитанных записей об этом персонаже."

def annotation(db,volume):
    rows=[(n,t,s) for n,t,s in db.execute("SELECT number,title,story FROM omega_index ORDER BY number") if o.volume(n)==volume and readable(db,n)]
    if not rows:return "Нет доступных прочитанных глав этого тома."
    lines=[f"Том {volume} — аннотация из прочитанных отрывков (не пересказ модели)."]
    for n,t,s in rows:
        excerpt=re.split(r"(?<=[.!?…])\s+",s.strip(),maxsplit=1)[0][:220]
        lines.append(f"{n}. {t}: {excerpt}")
    return "\n\n".join(lines)

def graph(db):
    nodes=[];edges=[];seen=set()
    def node(k,label,kind):
        if k not in seen:
            seen.add(k);nodes.append({"key":k,"group":4,"kind":kind,"content":label,"created":"","order":len(nodes)})
    node("evolution:root","Судьбы и последствия","evolution_root")
    edges.append({"a":"living:root","b":"evolution:root","kind":"evolution_branch"})
    if audit(db):return nodes,edges
    for n,did,p in list(published(db))[-60:]:
        for j,f in enumerate(p["facts"]):
            if not readable(db,n):continue
            hub="evolution:subject:"+o.digest(o.normalized(f["subject"]))[:20];key=f"evolution:fact:{did}:{j}"
            node(hub,f["subject"],"evolution_subject");node(key,f["detail"] if readable(db,n) else "Непрочитанное событие","evolution_fact")
            edges.extend([{"a":"evolution:root","b":hub,"kind":"evolution_subject"},{"a":hub,"b":key,"kind":"evolution_"+f["kind"]},{"a":f"c:{did}","b":key,"kind":"evolution_source"}])
            if f["cause"] is not None:
                r=db.execute("SELECT draft_id FROM omega_index WHERE number=?",(f["cause"],)).fetchone()
                edges.append({"a":f"c:{r[0]}" if r and r[0] is not None else f"canon:{f['cause']}","b":key,"kind":"evolution_cause"})
    return nodes,edges

def set_budget(db,model,inp,out,cap):
    # Rates in integer kopecks per million tokens; monthly cap in kopecks.
    if not model or any(type(x) is not int or not 0<x<=100_000_000 for x in (inp,out,cap)):raise ValueError("budget")
    db.execute("INSERT OR REPLACE INTO evolution_budget VALUES(1,?,?,?,?)",(model,inp,out,cap))

def estimate(messages,limit,inp,out):
    # Conservative local byte-based estimate, not provider tokenization.
    size=len(json.dumps(messages,ensure_ascii=False).encode("utf-8"))+1024
    return (size*inp+limit*out+999999)//1000000

def budget_check(db,model,messages,limit,day):
    row=db.execute("SELECT model,input_rate,output_rate,monthly_kopecks FROM evolution_budget WHERE id=1").fetchone()
    if not row:return True,None
    m,inp,out,cap=row
    if m!=model:return False,None
    predicted=estimate(messages,limit,inp,out)
    used=db.execute("SELECT COALESCE(SUM(COALESCE(actual_kopecks,estimate_kopecks)),0) FROM evolution_cost WHERE day LIKE ?",(day[:7]+"%",)).fetchone()[0]
    return used+predicted<=cap,(predicted,inp,out)

def reserve_cost(db,day,model,details):
    if details:
        estimate,inp,out=details
        db.execute("INSERT INTO evolution_cost VALUES(?,?,?,NULL,?,?)",(day,model,estimate,inp,out))

def settle_cost(db,day,result):
    row=db.execute("SELECT input_rate,output_rate FROM evolution_cost WHERE day=?",(day,)).fetchone()
    u=result.get("usage")
    if not row or not isinstance(u,dict):return
    a,b=u.get("prompt_tokens"),u.get("completion_tokens")
    if type(a) is int and type(b) is int and a>=0 and b>=0:
        db.execute("UPDATE evolution_cost SET actual_kopecks=? WHERE day=?",((a*row[0]+b*row[1]+999999)//1000000,day))

def budget_text(db,month):
    row=db.execute("SELECT model,input_rate,output_rate,monthly_kopecks FROM evolution_budget WHERE id=1").fetchone()
    if not row:return "Денежный лимит не задан. Суточный лимит генерации сохраняется."
    used=db.execute("SELECT COALESCE(SUM(COALESCE(actual_kopecks,estimate_kopecks)),0) FROM evolution_cost WHERE day LIKE ?",(month+"%",)).fetchone()[0]
    return f"Писатель: {row[0]}. Учтённая оценка: {used/100:.2f} из {row[3]/100:.2f} ₽ за месяц UTC. Не счёт Cloud.ru; только литературные запросы после настройки."

def model_report(db):
    """Compare available local generation records; no paid comparison calls."""
    rows=db.execute("""SELECT u.model,COUNT(*),SUM(CASE WHEN d.status='approved' THEN 1 ELSE 0 END),
        AVG(m.score),SUM(u.input_tokens),SUM(u.output_tokens)
        FROM cloud_writer_usage u JOIN chronicle_attempts a ON a.day=u.day
        LEFT JOIN chronicle_drafts d ON d.diary_id=a.diary_id
        LEFT JOIN omega_meta m ON m.draft_id=d.id GROUP BY u.model ORDER BY u.model""").fetchall()
    if not rows:return "Нет статистики моделей-писателей."
    return "Сравнение имеющихся запросов (разные сцены, не контролируемый тест):\n"+"\n".join(
        f"{m}: запросов {n}, утверждено {a}, средняя локальная оценка {round(score,1) if score is not None else '—'}, токены {i}/{out}"
        for m,n,a,score,i,out in rows)

def archive(db,offset=0):
    """Bounded local access to older published evolution records."""
    if audit(db):return "Записи повреждены."
    rows=db.execute("""SELECT a.number,r.draft_id FROM evolution_records r
      JOIN saga_arcs a ON a.draft_id=r.draft_id JOIN chronicle_drafts d ON d.id=r.draft_id
      WHERE d.status='approved' ORDER BY a.number DESC LIMIT 20 OFFSET ?""",(offset,)).fetchall()
    lines=[]
    for n,did in rows:
        if readable(db,n):
            p=read(db,did)
            lines.append(f"Глава {n}: "+("; ".join(f["subject"]+" — "+f["detail"] for f in p["facts"]) or "без дополнительных карточек"))
    return "\n".join(lines) or "На этой странице нет доступных записей."
