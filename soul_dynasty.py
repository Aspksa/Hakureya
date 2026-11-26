"""Eternal Dynasty: author-approved fictional intentions, separate from published canon.
One selected beat per literary group; exact story excerpts are required to mark a beat.
Existing Cloud.ru request, quota, review, and publication transaction remain authoritative.
"""
import json
import soul_omega as o
import soul_evolution as ev
import soul_novel as novel
import soul_romance as romance
import soul_intelligence as li

VERSION=1
SISTER="Цукиноха"
MAID="Маюри"
# Titles and directions are plans, never prepublished facts.
BEATS=(
(1,"sister","character","Младшая сестра императрицы","Представь взрослую бессмертную кицунэ Цукиноху, младшую сестру Хакурэи. Не меняй исходные 13 глав."),
(2,"sister","power","Собственный первородный дар","Покажи уникальный дар Цукинохи, его цену и границы, не копируй девять сил Хакурэи."),
(3,"sister","love","Невероятная новость","Цукиноха узнаёт о любви сестры к человеку из конкретного свидетельства; не узнаёт автоматически его тайную силу."),
(4,"sister","world","Тайный визит","Цукиноха отправляется в человеческий мир по собственной причине, соблюдая тайны двора."),
(5,"sister","character","Чем он её пленил","Цукиноха наблюдает характер и поступки героя, хочет понять выбор Хакурэи."),
(6,"sister","love","Чувство, которого не ждала","Цукиноха постепенно осознаёт любовь к герою после уже показанных совместных событий."),
(7,"sister","mystery","Невысказанная тайна","Цукиноха скрывает свои чувства от Хакурэи; разделяй знания персонажей."),
(8,"sister","love","Соперничество сестёр","Напряжение и ревность без унижения, принуждения или разрушения родства."),
(9,"sister","love","Взгляд старшей сестры","Хакурэя замечает перемену по поступкам, но подозрение ещё не знание."),
(10,"sister","character","Прошлое Цукинохи","Раскрой её биографию, достоинство, слабости и отдельную цель; не переписывай канон."),
(11,"maid","court","Приговорённая к казни","Взрослая небесная кицунэ Маюри несправедливо приговорена к казни. Она боится императрицы, не знает о её любви и человеческом мире. Не раскрывай виновника."),
(12,"maid","court","Тайное спасение","Хакурэя лично спасает Маюри от казни и скрывает это от преследователей. Маюри не понимает причины милости и всё ещё боится её."),
(13,"maid","world","Незнакомый человеческий мир","Хакурэя переносит Маюри в дом героя и прячет её от преследователей. Маюри впервые видит человека и боится его, не понимает его статуса или отношений с императрицей; ничего не знает о человеческом быте."),
(14,"maid","power","Защита без цепей","Хакурэя дарует Маюри защиту от преследователей. Это не ошейник, не магическое подчинение и не отмена её воли."),
(15,"maid","character","Подарок императрицы","Хакурэя преподносит герою подарок: личную горничную Маюри, предлагает ей безопасный дом и службу. Маюри в страхе не понимает, почему императрица дарит её человеку и кто он для Хакурэи; служба — добровольная, человек не собственность. Не раскрывай всё сразу."),
(16,"maid","love","Тепло вместо страха","Лишь после нескольких опубликованных сцен безопасности и быта Маюри замечает собственные чувства к герою; не благодарность за спасение как долг любви."),
(17,"maid","power","Скрытый дар","Наблюдаемое проявление особой способности Маюри; её ограничения, не мгновенная абсолютная сила."),
(18,"maid","mystery","Имя из неизвестного прошлого","Покажи след загадочного происхождения Маюри; даже Хакурэя не знает всей правды."),
(19,"maid","mystery","Почему её осудили","Исследуй обвинение, противоречивые показания и реальные причины приговора, не решай всё одной репликой."),
(20,"maid","growth","Избранная собственная судьба","Маюри постепенно становится самостоятельной сильной героиней, способной выбирать служение и собственный путь."),
(21,"heroines","mystery","Богиня судьбы","Новая взрослая богиня не может увидеть будущее героя; проверь, нет ли уже похожего персонажа, различи её роль от Мэйрин."),
(22,"heroines","world","Императрица драконов","Взрослая древняя правительница драконов с собственной культурой, целью и ценой власти."),
(23,"heroines","court","Королева демонов","Взрослая правительница ищет союз по самостоятельной причине; не делай её автоматически врагом или возлюбленной."),
(24,"heroines","power","Богиня смерти","Взрослая богиня удивлена невосприимчивостью героя; уважай установленные пределы силы."),
(25,"heroines","world","Принцесса исчезнувшей цивилизации","Взрослая наследница, культура и свидетельства утраченного мира; отличимое имя."),
(26,"heroines","power","Хранительница пространства","Взрослая героиня с иной ролью, не дубль Микагэ; независимые задачи и ограничения."),
(27,"heroines","mystery","Небесная целительница","Взрослая целительница хранит опасное знание; этические последствия в мире романа."),
(28,"heroines","court","Древняя соперница","Новая или уже подтверждённая взрослая соперница Хакурэи; покажи мотивы и историю отношений."),
(29,"heroines","character","Изгнанная женщина-рыцарь","Взрослая рыцарь, изгнание, цель, честь и возможность новой судьбы."),
(30,"heroines","power","Создательница артефактов","Взрослая мастерица, ремесло, собственные правила, цена создания и ошибки."),
(31,"home","love","Обычаи людей","Хакурэя и Цукиноха учатся человеческим обычаям; покажи разные реакции без повторения прошлых сцен."),
(32,"home","character","Первое утро Маюри","Маюри не знает кухни, электричества, техники и бытовых правил. Герой спокойно объясняет; страх ослабевает постепенно, не исчезает сразу."),
(33,"home","guardians","Тайные визиты","Девять хранительниц посещают дом согласно уже раскрытым им сведениям; не раскрывай тайну раньше их этапов."),
(34,"home","growth","Магия и бытовые ошибки","Юмор через различие привычек, не унижение героинь; конкретное последствие магии."),
(35,"home","world","Совместный отдых","Путешествие и отдых в человеческом мире, новая деталь культуры, самостоятельные желания."),
(36,"home","love","Подарок с историей","Неожиданный подарок герою с личным смыслом, не покупка привязанности."),
(37,"home","world","Дворец в отдельном измерении","Добровольное совместное строительство, правила пространства и безопасность; не новый десятый небесный мир."),
(38,"home","character","Библиотека героя","Создание личной библиотеки; каждый участник предлагает собственный вклад и источники знаний."),
(39,"home","love","Семейный праздник","Ужин или праздник, разные голоса, новые традиции, уважение границ."),
(40,"home","mystery","Секрет среди людей","Последствия сохранения тайны сверхъестественного происхождения; не заставляй людей знать то, чего не видели."),
(41,"romance","love","Своя история любви","Для взрослых героинь показывай разные добровольные траектории чувств; не объявляй всех влюблёнными без событий."),
(42,"romance","love","Ревность Хакурэи","Хакурэя замечает собственную ревность к Цукинохе, обсуждает чувства, сохраняя достоинство."),
(43,"romance","love","Внимание героя","Соперничество за внимание без принуждения и унижения; герой также выбирает."),
(44,"romance","love","Тайное письмо","Новое личное письмо, адресат и конкретное опубликованное событие."),
(45,"romance","love","Признание","Признание лишь для героини, чьи чувства уже развивались; согласие и естественная реакция."),
(46,"romance","world","Свидание между мирами","Романтическое путешествие с новой культурой, препятствием и последствием."),
(47,"romance","character","Дружба героинь","Самостоятельная дружба и совместное дело, не только общий интерес к герою."),
(48,"romance","growth","Спор и примирение","Семейное разногласие с разными мотивами и взаимным уважением."),
(49,"romance","love","Добровольное обещание","Обещания и клятвы без магического принуждения; открой линию для последствий."),
(50,"romance","love","Время меняет сердца","Покажи изменения отношений через подтверждённое течение времени, не выдумывай прошедшие века."),
(51,"mysteries","power","Врождённая невосприимчивость","Возврати установленную загадку защиты героя; новая улика, без утверждения причины без доказательств."),
(52,"mysteries","mystery","Пустая запись судьбы","Исследуй отсутствие записи о герое в небесном архиве; свидетельства и альтернативные объяснения."),
(53,"mysteries","court","След заказчика казни","Свяжи дело Маюри с ранее опубликованной уликой; не называй виновника без причинной цепочки."),
(54,"mysteries","power","Скрытая сила Цукинохи","Почему сестра скрывала часть дарования; покажи подтверждённые причины, не новый абсолют."),
(55,"mysteries","mystery","Утраченная династия","Архив и свидетели исчезнувшей династии кицунэ, не меняй происхождение Хакурэи."),
(56,"mysteries","mystery","Человек без судьбы","Пророчество с несколькими толкованиями; не путай отсутствие записи с предопределённым исходом."),
(57,"mysteries","power","За границей закона","Ограниченный эксперимент с необычной силой, цена и опровержимая гипотеза."),
(58,"mysteries","court","Тайный совет","Тайное общество небесных правителей, собственные интересы, не всеобщий заговор без улик."),
(59,"mysteries","mystery","Первая вечная снежинка","Исследуй символ и происхождение в границах неизменного канона; гипотеза не факт."),
(60,"mysteries","growth","Пересечение судеб","Соедини реально опубликованные причинные линии Маюри, Цукинохи и героя, без искусственного совпадения."),
(61,"lives","character","Биографии героинь","Выбери уже введённую героиню, её подтверждённая биография и новый эпизод; не создавай дубль."),
(62,"lives","character","Разные голоса","Развивай индивидуальные привычки, речь, юмор и поступки существующих персонажей."),
(63,"lives","love","Личное воспоминание","Воспоминание о герое только из опубликованной сцены, новая точка зрения."),
(64,"lives","love","Изменение чувств","Покажи изменение чувств после конкретного ранее описанного совместного события."),
(65,"lives","character","Собственная цель","Самостоятельная цель взрослой героини, не связанная исключительно с любовью."),
(66,"lives","character","Дневник героини","Личный дневник по известным ей событиям; не всеведущий пересказ."),
(67,"lives","world","В отсутствие героя","Событие, самостоятельный выбор героини, последствия без участия героя."),
(68,"lives","mystery","Разные знания","Различай подтверждённые знания и скрытые тайны персонажей, не раскрывай незрелые улики."),
(69,"lives","power","Рост способности","Тренировка, ошибки и подтверждённый рост одной героини, с ограничениями."),
(70,"lives","growth","Собственный том","Начни самостоятельную линию одной героини с целью и последствиями; не объявляй целый том написанным."),
)
BY_ID={x[0]:x for x in BEATS}
# First the maid's rescue, then sister and home; later payoffs interleave.
ORDER=(11,12,13,14,15,32,1,2,3,4,5,31,34,10,35,17,18,6,7,9,8,16,19,20,33,36,39,40,37,38,
       21,51,22,23,24,52,25,26,27,28,29,30,41,42,43,44,45,46,47,48,49,50,
       53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70)
assert len(ORDER)==70 and set(ORDER)==set(BY_ID)
GROUPS={"maid":"Спасённая горничная","sister":"Сестра императрицы","heroines":"Новые героини","home":"Человеческий дом","romance":"Истории отношений","mysteries":"Великие тайны","lives":"Самостоятельные судьбы"}
# Narrow lexical checks support the key opening scenes; not full semantic proof.
MARKERS={
 11:("маюри","казн"),12:("маюри","спас"),13:("маюри","человек"),14:("маюри","защит"),15:("маюри","горничн"),
 32:("маюри",),1:("цукинох","сестр"),6:("цукинох","люб"),16:("маюри","люб"),
}

def stage(step):
    i,group,theme,title,guide=BY_ID[step]
    return {"id":i,"group":group,"theme":theme,"title":title,"guide":guide}

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS dynasty_records(
        draft_id INTEGER PRIMARY KEY,payload TEXT NOT NULL,source_hash TEXT NOT NULL,checksum TEXT NOT NULL)""")

def read(db,did):
    row=db.execute("SELECT payload,source_hash,checksum FROM dynasty_records WHERE draft_id=?",(did,)).fetchone()
    if not row:return None
    raw,source,check=row
    base=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()
    if not base or base[0]!=source or o.digest(o.dump([raw,source]))!=check:raise ValueError("damaged dynasty record")
    p=json.loads(raw)
    if p.get("version")!=VERSION or type(p.get("step")) is not int or p["step"] not in (0,*ORDER):raise ValueError("dynasty schema")
    return p

def published(db):
    rows=db.execute("""SELECT a.number,d.id FROM dynasty_records r JOIN saga_arcs a ON a.draft_id=r.draft_id
        JOIN chronicle_drafts d ON d.id=r.draft_id WHERE d.status='approved' AND a.number IS NOT NULL ORDER BY a.number""").fetchall()
    return [(n,did,read(db,did)) for n,did in rows]

def completed(db):
    steps=[p["step"] for _,_,p in published(db) if p["step"]]
    if steps!=list(ORDER[:len(steps)]):raise ValueError("dynasty sequence")
    return steps

def audit(db):
    try:completed(db)
    except (ValueError,TypeError,KeyError):return ["Повреждены записи Eternal Dynasty"]
    return []

def next_step(db):
    done=completed(db)
    return stage(ORDER[len(done)]) if len(done)<len(ORDER) else None

def choose_lane(db,explicit=False):
    """Only switch at a new literary group; keep ongoing Dynasty groups intact."""
    if romance.current_cycle(db) or audit(db):return False
    last=db.execute("SELECT number,arc,draft_id FROM omega_index ORDER BY number DESC LIMIT 1").fetchone()
    if not last:return False
    n,arc,did=last
    group=novel.next_group(db,arc,None)
    if group["part"]>1:return bool(arc=="future" and did is not None and read(db,did))
    if next_step(db) is None:return False
    if explicit:return True
    previous=db.execute("""SELECT MAX(a.number) FROM dynasty_records r JOIN saga_arcs a ON a.draft_id=r.draft_id
       JOIN chronicle_drafts d ON d.id=r.draft_id WHERE d.status='approved'""").fetchone()[0]
    return previous is None or n-previous>=3

def context(db,plan):
    if not plan.get("dynasty_lane"):return plan
    group=plan["novel"];start=group["start"]
    previous=published(db)
    # A completed beat does not allow a second beat in the same multi-part group.
    already=next((p for _,_,p in reversed(previous) if p["group_start"]==start and p["step"]),None)
    selected=None if already else next_step(db)
    done=completed(db)
    prior=[]
    # Send bounded evidence from relevant previous stages, even if older than recent chapters.
    target_group=selected["group"] if selected else (stage(already["step"])["group"] if already else "")
    related=[(n,p) for n,_,p in previous if p["step"] and stage(p["step"])["group"]==target_group]
    for n,p in related[-3:]:prior.append({"number":n,"step":p["step"],"quote":p["evidence"][:160]})
    current=selected or (stage(already["step"]) if already else None)
    if not current:raise ValueError("no dynasty group")
    p={"selected":selected,"current":current,"group_start":start,"done":done,"prior":prior,"continuation":group["part"]>1}
    plan["dynasty"]=p
    direction={k:current[k] for k in ("theme","title","guide")}
    plan["living"]["theme"]=current["theme"];plan["living"]["head"]={**plan["living"]["head"],**direction}
    plan["evolution"]["chosen"]={"scene":0,**direction};plan["evolution"]["alternatives"]=[]
    if not p["continuation"]:plan["novel"]["next_line"]=direction
    return plan

def instruction(plan):
    p=plan.get("dynasty")
    if not p:return ""
    current=p["current"];done=set(p["done"]);selected=p["selected"]
    guard=""
    if current["group"] in ("maid","home","mysteries","romance","lives") and 11 in done|{current["id"]}:
        guard+=" Маюри — взрослая спасённая кицунэ. До первых встреч не знает людей, их быта и связи Хакурэи с героем. Не знает того, чего ей ещё не показали. До постепенного развития доверия не превращай страх и благодарность в любовь. "
        if 16 not in done and current["id"]!=16:guard+=" Не признавай её влюблённой до соответствующего этапа. "
    if current["group"] in ("sister","romance","home","mysteries","lives") and 1 in done|{current["id"]} and 6 not in done and current["id"]!=6:
        guard+=" Цукиноха не признаётся в любви до постепенного развития её чувств. "
    marker=(" При реальном завершении выбранного эпизода верни dynasty:{step:"+str(selected["id"])+",evidence: точная цитата из story 12–240 символов, подтверждающая событие}. Если эпизод ещё не завершён, не добавляй dynasty. " if selected else " Не отмечай новый этап в этой части. ")
    return " Eternal Dynasty — текущая отдельная линия, а не уже произошедшие факты: "+o.dump(current)+". Подтверждённые этапы (номера): "+o.dump(p["done"])+". Выдержки предыдущих сцен этой линии: "+o.dump(p["prior"])+". "+guard+" Продолжай предыдущую часть без повтора, не перескакивай к будущим этапам. Не раскрывай секрет личности героя всему двору и не меняй прежние обязательные этапы. "+marker+" Все романтические герои взрослые; служение добровольное, чувства не являются платой за спасение."

def check(story,step,evidence):
    if type(step) is not int or step not in ORDER:raise ValueError("dynasty step")
    quote=o.clean(evidence,12,240)
    if quote not in story:raise ValueError("dynasty evidence absent")
    if any(x not in o.normalized(quote) for x in MARKERS.get(step,())):raise ValueError("dynasty evidence does not contain required anchors")
    return quote

def save(db,did,story,raw,plan):
    p=plan.get("dynasty")
    if not p:
        if raw is not None:raise ValueError("unexpected dynasty")
        return
    selected=p["selected"];step=0;quote=""
    if raw is not None:
        if not isinstance(raw,dict) or set(raw)!={"step","evidence"} or not selected or raw["step"]!=selected["id"]:raise ValueError("unexpected dynasty milestone")
        step=raw["step"];quote=check(story,step,raw["evidence"])
    payload=o.dump({"version":VERSION,"step":step,"evidence":quote,"group_start":p["group_start"],"target":selected["id"] if selected else 0,"current":p["current"]["id"]})
    source=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()[0]
    db.execute("INSERT INTO dynasty_records VALUES(?,?,?,?)",(did,payload,source,o.digest(o.dump([payload,source]))))

def validate_approval(db,did):
    p=read(db,did)
    if not p:return
    if audit(db):raise ValueError("dynasty integrity")
    if p["step"]:
        expected=next_step(db)
        if not expected or p["step"]!=expected["id"]:raise ValueError("dynasty sequence changed")
        import soul_chronicle as c
        raw,h=db.execute("SELECT payload,checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()
        check(c.unpack(raw,h)["story"],p["step"],p["evidence"])

def status(db):
    rows=published(db);done=completed(db);visible=[n for n,_,p in rows if p["step"] and (n<=13 or ev.readable(db,n))]
    return f"Династия вечности: {len(done)} из 70 сюжетных этапов отмечено в опубликованных частях. Доступных прочитанных этапов: {len(visible)}. Ещё 10 пунктов относятся к визуализации. План — отдельная линия, оригинальные 13 глав неизменны."

def plan_text(db):
    done=set(completed(db))
    return "Будущие замыслы (спойлеры, не канон):\n"+"\n".join(("✓ " if i in done else "· ")+str(i)+". "+stage(i)["title"] for i in ORDER)

def graph(db):
    try:rows=[(n,did,p) for n,did,p in published(db) if p["step"] and (n<=13 or ev.readable(db,n))]
    except (ValueError,TypeError,KeyError):return [],[]
    if not rows:return [],[]
    nodes=[];edges=[];seen=set();groups=set();done={p["step"] for _,_,p in rows}
    def node(k,label,kind,area=None,**extra):
        if k not in seen:
            seen.add(k);nodes.append(dict(key=k,content=label,group=4,kind=kind,created="",order=len(nodes),infinite_group=area or k,**extra))
    def edge(a,b,k):
        if a!=b:edges.append(dict(a=a,b=b,kind=k))
    root="dynasty:root";node(root,"Династия вечности","dynasty_root")
    sister=li.actor_key(SISTER);maid=li.actor_key(MAID)
    if 1 in done:
        node(sister,SISTER,"lit_character");edge(root,sister,"dynasty_character");edge(sister,"character:empress","dynasty_family")
    if 11 in done:
        node(maid,MAID,"lit_character");edge(root,maid,"dynasty_character")
    if 6 in done and 1 in done:edge(sister,"character:hero","dynasty_love")
    if 16 in done and 11 in done:edge(maid,"character:hero","dynasty_love")
    if 8 in done and 1 in done:edge(sister,"character:empress","dynasty_rival")
    if 15 in done and 11 in done:edge(maid,"character:hero","dynasty_service")
    previous=None
    for n,did,p in rows:
        s=stage(p["step"]);g="dynasty:group:"+s["group"];groups.add(s["group"])
        node(g,GROUPS[s["group"]],"dynasty_saga");edge(root,g,"dynasty_branch")
        k="dynasty:stage:"+str(s["id"]);source="c:"+str(did)
        # Keep spoiler-protected titles neutral even when reading out of order.
        label=("Этап "+str(s["id"]) if ev.settings(db)[1] else s["title"])
        node(k,label,"dynasty_mystery" if s["theme"]=="mystery" else "dynasty_event",g)
        edge(g,k,"dynasty_stage");edge(source,k,"dynasty_source")
        if s["group"]=="sister" and 1 in done:edge(sister,k,"dynasty_history")
        if s["group"]=="maid" and 11 in done:edge(maid,k,"dynasty_history")
        if previous:edge(previous,k,"dynasty_time")
        previous=k
        if s["id"]==60 and 1 in done and 11 in done:
            edge(sister,k,"dynasty_cross");edge(maid,k,"dynasty_cross");edge("character:hero",k,"dynasty_cross")
    return nodes,edges
