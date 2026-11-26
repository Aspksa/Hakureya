"""Eternal Destiny: approved fictional events, never real user memories."""
import json
import soul_omega as o
import soul_shadow as sh
import soul_guardians as gu

VERSION=1
TOPICS=("love","power","guardians","court","worlds","cast","growth")
LABELS=("Любовь","Сила героя","Хранительницы","Правление и интриги","Путешествия и миры","Новые герои","Развитие Хакурэи")
# Stable numbers match the approved 80-item design. 71–80 are graph capabilities.
BEATS=(
("Украденные ночи","Новый приватный вечер после раскрытия любви: укромное свидание с согласованной охраной, шутливое оправдание для двора, не обман доверенных хранительниц."),
("Императорский выходной","Отмени необязательную церемонию, сохрани важные обязанности; покажи радость отдыха и последствия решения."),
("Незнакомая ревность","Хакурэя замечает ревность, признаёт чувство и обсуждает его с любимым, не ограничивает его свободу."),
("Ночь без магии","Добровольно проведи вечер без магии; неловкое бытовое дело и взаимная помощь."),
("Свидание среди смертных","Скрытые уши и хвосты, прогулка в городе, неожиданная встреча и выбор."),
("Тайный подарок","Самодельный подарок с историей, не очередное признание."),
("Первый публичный танец","Новый бал после прежних придворных событий; танец показывает сделанный выбор, не повторяет первый бал."),
("Сокровенные мечты","Разговор о мечте императрицы, которую она раньше не позволяла себе осуществить."),
("Тысяча причин любить","Раскрой любовь к поступкам и личности героя, не к его силе."),
("Утро без короны","Хранительницы пытаются разбудить императрицу в объятиях любимого; добрый юмор и обязанности."),
("Непроизвольный отклик дара","После раскрытия личности обнаруживается новое проявление силы, а не повторное пробуждение."),
("Артефакт без ответа","Древний артефакт не классифицирует дар; исследование имеет последствия."),
("Отклик девяти хвостов","Хвосты реагируют на неизвестную магию; связь не лишает героиню воли."),
("Законы за гранью пространства","Новый эффект дара, конкретное ограничение и ответственность."),
("Признание Амацуки","Амацука уточняет предел собственного знания после предыдущего столкновения."),
("Запись до рождения пространства","Шиори находит свидетельство, допускающее разные толкования, не объявляет гипотезу фактом."),
("Врата неизвестного мира","Непредвиденное открытие прохода; герой отвечает за последствия."),
("Совет древнейших богов","Боги изучают происхождение дара; разные мотивы и позиции."),
("Урок невозможной магии","Хакурэя помогает герою контролировать неизвестный дар посредством опыта и наблюдения."),
("Два истока","Намёк на связь происхождения героя и Хакурэи через проверенные свидетельства; не переписывай канон рождения."),
("Расписание свиданий","Рэйка совмещает охрану, обязанности и приватность пары, учится гибкости."),
("Кулинарный урок","Сэйрана учит Хакурэю новому человеческому блюду; отличие от первого завтрака."),
("Карта невозможного","Микагэ исследует пространственный след, признаёт ошибочную гипотезу."),
("Архив счастливых дней","Токихана сохраняет конкретные события, уважая приватность."),
("Дружеское состязание","Акацуки предлагает безопасное фантастическое испытание, уважает границы соперника."),
("Противоречие в архиве","Шиори находит несовпадение древних записей, проверяет источник."),
("Доверенное лицо","Юмэка выслушивает императрицу, не читает мысли и не решает за неё."),
("Дипломатия свиданий","Мэйрин придумывает изящное публичное объяснение приватного вечера без обмана охраны."),
("Молчание Амацуки","Амацука раскрывает причину многовекового молчания; её личный выбор."),
("Вечер девяти подруг","Все девять совместно готовят праздник; каждому характеру отдельный вклад."),
("Разделённый совет","Разные позиции царств по выбору императрицы, дипломатические последствия."),
("Неожиданный союзник","Бывший ухажёр помогает герою по собственным причинам, уважая отказ."),
("Возвращение соперницы","Древняя соперница Хакурэи возвращается с независимой целью."),
("Аудиенция неизвестного правителя","Правитель требует встречи с защитником; не раскрывай его личность всему двору автоматически."),
("Исчезнувшие страницы","Архивный пробел связывает прошлые решения с настоящей загадкой."),
("Мятежное царство","Одно царство оспаривает власть; императрица ищет решение и учитывает подданных."),
("Невозможный политический брак","Совет предлагает союз; Хакурэя сохраняет право выбора, последствия реалистичны для мира."),
("Пророк при дворе","Пророчество неоднозначно, возможны ошибка и манипуляция."),
("Утраченный артефакт","Хранительницы расследуют исчезновение фантастического артефакта; разные версии."),
("Давнее решение","Поступок императрицы из прошлого отзывается в нынешней политике; не меняй установленные главы."),
("Царство вечной ночи","Путешествие в новый мир с собственными обычаями и ограничениями."),
("Город между секундами","Необычный город; время ограничивает выбор, Токихана не переписывает прошлое."),
("Океан воспоминаний","Океан хранит следы исчезнувшей культуры; память не равна достоверной истории."),
("Храм без магии","Решение задачи через наблюдение, сотрудничество и обычные навыки."),
("Мир без титула","Хакурэю никто не узнаёт; она самостоятельно выбирает, как поступить."),
("Создатель царства","Встреча с древним основателем; его свидетельство не обязательно истинно."),
("Окно в прошлое","Наблюдение прошлого без изменения событий или канона."),
("Библиотека ненаписанных судеб","Возможные будущие, не обязательные предсказания."),
("Спасение целого мира","Все девять хранительниц и пара действуют сообща, каждый имеет собственную роль."),
("За девятью небесами","Открытие внешней вселенной; не объявляй её десятым хвостом или уже существующим царством."),
("Наставница из вечности","Представь Иори — хранительницу древних знаний, некогда наставлявшую Хакурэю после её рождения, не её создательницу."),
("Соседняя императрица","Представь Лианьсюэ — независимую правительницу внешнего мира, дипломатический интерес и собственная воля."),
("Хранитель расстояний","Представь Каэна — загадочного исследователя границ пространства, не всезнающего учителя."),
("Жрица забытых богов","Представь Мэйсю — жрицу, защищающую память исчезнувшего народа."),
("Человеческий мудрец","Представь старого учителя Дзюна; мудрость без магического превосходства."),
("Небесный принц","Представь Рэнхо — безответно влюблённого князя, отличимого от прежних ухажёров."),
("Соперница Рэйки","Представь воительницу Сэцуну; прошлое соперничество, нынешняя самостоятельная цель."),
("Странница с частью ответа","Представь Нари — путешественницу, знающую один фрагмент истории героя, не все тайны."),
("Библиотекарь будущих событий","Представь Кагари — хранительницу возможных судеб, не гарантированных фактов."),
("Свидетель рождения","Представь древнее существо Орум, которое помнит рождение Хакурэи, не меняет канон."),
("Смех над собой","Новая ситуация, где императрица искренне смеётся над собственной ошибкой."),
("Лицо без маски","Она выражает эмоцию в подходящей обстановке, не теряет выдержку на совете."),
("Простые радости","Человеческое занятие становится самостоятельным интересом, а не только способом быть рядом с героем."),
("Дружба вместо церемоний","Она слышит мнение хранительницы как подруги, а не только подданной."),
("Признанная ошибка","Конкретная ошибка правления, исправление и ответственность перед людьми."),
("Страх за любимого","Разговор о риске и свободном выборе без повторного похищения или спасения."),
("Совместное созидание","Герои создают новое полезное дело; каждый вносит собственный вклад."),
("Девять голосов","Изменение отношений с охраной: доверие, право на несогласие, ответственность."),
("Новый принцип правления","Реформа вытекает из прежнего решения и проверяется последствиями."),
("Счастье вечной владычицы","Заверши большой том новой привычкой или выбором, сохрани её достоинство и открытые приключения.")
)
CAST=(
("iori","Иори","Наставница после рождения Хакурэи; спокойная, требовательная, хранит древние знания."),
("lian","Лианьсюэ","Императрица внешнего мира; гордая дипломатка, защищает собственных подданных."),
("kaen","Каэн","Хранитель пространства; любознательный и осторожный исследователь, не знает всего."),
("meixiu","Мэйсю","Жрица забытых богов; верная памяти своего народа, умеет спорить."),
("jun","Дзюн","Пожилой человеческий мудрец; внимательный и ироничный, без сверхсил."),
("renho","Рэнхо","Небесный принц; любит Хакурэю без взаимности, учится принимать её выбор."),
("setsuna","Сэцуна","Воительница, соперница Рэйки; прямолинейна, уважает заслуженную победу."),
("nari","Нари","Странница; знает фрагмент прошлого героя, скрытна, но не всеведуща."),
("kagari","Кагари","Хранительница библиотеки возможных будущих; аккуратна в предсказаниях."),
("orum","Орум","Древний свидетель рождения Хакурэи; помнит события, но может ошибаться в толковании.")
)
# Interleave by round. Introduce the external empire after the gateway to it.
ORDER=tuple(n for row in zip(*(range(i,i+10) for i in (1,11,21,31,41,51,61))) for n in row)
# Explicit late introductions: external ruler follows discovery of external universe.
ORDER=tuple(n for n in ORDER if n not in (52,70))+(52,70,)
ACTORS={k:(name,desc) for k,name,desc in CAST}
ACTORS.update({p[0]:(p[1],p[4]) for p in gu.CAST})
ACTORS.update({"empress":("Хакурэя","Императрица девяти небес"),"hero":("герой","Возлюбленный императрицы")})
KINDS=("character","realm","travel","prophecy","power","alliance","growth","consequence")
GRAPH_ITEMS=(
"71. Созвездия новых персонажей","72. Связи девяти царств","73. Карта путешествий",
"74. Пророчества и их исполнение","75. История силы","76. Союзы и конфликты",
"77. Древо развития характера","78. Причины и последствия","79. Переплетение историй","80. Расширение пространства"
)

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS destiny_drafts(
        draft_id INTEGER PRIMARY KEY, beat INTEGER NOT NULL, payload TEXT NOT NULL,
        source_hash TEXT NOT NULL, checksum TEXT NOT NULL, version INTEGER NOT NULL)""")

def read(db,did):
    row=db.execute("SELECT beat,payload,source_hash,checksum,version FROM destiny_drafts WHERE draft_id=?",(did,)).fetchone()
    if not row:return None
    beat,raw,source,check,v=row
    d=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()
    if not d or d[0]!=source or v!=VERSION or beat not in ORDER or o.digest(o.dump([beat,raw,source,v]))!=check:raise ValueError("damaged destiny record")
    return beat,json.loads(raw)

def published(db):
    result=[]
    for did,n in db.execute("""SELECT t.draft_id,a.number FROM destiny_drafts t JOIN saga_arcs a ON a.draft_id=t.draft_id
      JOIN chronicle_drafts d ON d.id=t.draft_id WHERE d.status='approved' ORDER BY a.number"""):
        p=read(db,did)
        if not p or len(result)>=len(ORDER) or p[0]!=ORDER[len(result)]:raise ValueError("destiny sequence mismatch")
        result.append((did,n,p[0],p[1]))
    return result

def audit(db):
    try:published(db)
    except (ValueError,TypeError,KeyError):return ["Повреждены связи Eternal Destiny"]
    return []

def ready(db):
    return not (sh.audit(db) or gu.audit(db)) and len(sh.completed(db))==len(sh.STEPS) and len(gu.published(db))==len(gu.STEPS)

def topic(beat):
    return TOPICS[(beat-1)//10]

def plan(db):
    if audit(db) or not ready(db):return None
    done=published(db)
    if len(done)>=len(ORDER):return None
    beat=ORDER[len(done)];title,guide=BEATS[beat-1]
    cast=[]
    if 51<=beat<=60:cast.append(list(CAST[beat-51]))
    if 21<=beat<=29:cast.append(list(gu.CAST[beat-21]))
    if beat==30:cast.extend([list(p[:3]) for p in gu.CAST])
    recent=[{"chapter":n,"beat":b,"excerpt":p["evidence"]} for _,n,b,p in done[-4:]]
    related=[{"chapter":n,"beat":b,"excerpt":p["evidence"]} for _,n,b,p in done if topic(b)==topic(beat)][-3:]
    known_cast=[list(CAST[b-51]) for _,_,b,_ in done if 51<=b<=60]
    # Track unresolved prophecies by explicit source references.
    resolved={f["cause"] for _,_,_,p in done for f in p["facts"] if f["kind"]=="prophecy" and f["cause"] is not None}
    open_prop=[{"chapter":n,"detail":f["detail"]} for _,n,_,p in done for f in p["facts"] if f["kind"]=="prophecy" and f["cause"] is None and n not in resolved]
    return {"beat":beat,"topic":topic(beat),"title":title,"guide":guide,"cast":cast,"recent":recent,"related":related,"known_cast":known_cast,"open_prophecies":open_prop[-3:]}

def instruction(p):
    if not p:return ""
    return (" ГЛАВНЫЙ замысел продолжения после завершения Тени и девяти хранительниц: "+o.dump(p)+
       ". Это новые события; не возвращай раскрытую тайну любви или личности защитника, не пересказывай старые покушения. "
       "Хакурэя — самостоятельная императрица, любовь взаимна, девять хранительниц имеют собственные характеры. "
       "Сохрани канон, ограничения силы и последствия. Пиши полноценную сцену, с диалогом, выбором и результатом. "
       "Для завершённого этапа верни destiny:{beat:"+str(p["beat"])+",evidence:точная цитата 12–240 символов из story,facts:[{kind,subject,detail,evidence,cause,realm}]}. "
       "До двух facts; kind из "+", ".join(KINDS)+
       "; subject — id персонажа из известных карточек, либо null; detail — краткий вывод; evidence — точная цитата 12–240 символов; "
       "cause — номер уже опубликованной главы либо null; realm — 1..9 только при установленной связи с царством, иначе null. "
       "Для character укажи id и имя в цитате. Для travel/realm оставь realm=null для внешнего или человеческого мира. "
       "Для alliance можно добавить other — id второго названного персонажа; для travel можно добавить origin — номер исходного царства 1..9, отличный от realm. Для prophecy с cause укажи главу прежнего открытого пророчества. Не выдавай гипотезу за факт. "
       "Если этап не завершён, не добавляй destiny; приоритет — текст сцены. Остальные метаданные необязательны.")

def save(db,did,story,raw,p):
    if raw is None:return
    current=plan(db)
    if not p or not current or p["beat"]!=current["beat"] or not isinstance(raw,dict) or set(raw)!={"beat","evidence","facts"} or type(raw["beat"]) is not int or raw["beat"]!=p["beat"]:
        raise ValueError("destiny beat unavailable")
    evidence=o.clean(raw["evidence"],12,240)
    if evidence not in story:raise ValueError("destiny excerpt missing")
    facts=raw["facts"]
    if not isinstance(facts,list) or len(facts)>2:raise ValueError("invalid destiny facts")
    previous=published(db)
    introduced={CAST[b-51][0] for _,_,b,_ in previous if 51<=b<=60}
    if 51<=p["beat"]<=60:
        a=CAST[p["beat"]-51]
        if a[1].casefold()[:3] not in story.casefold():raise ValueError("new character absent")
        introduced.add(a[0])
    prop={n for _,n,_,data in previous for f in data["facts"] if f["kind"]=="prophecy" and f["cause"] is None}
    closed={f["cause"] for _,_,_,data in previous for f in data["facts"] if f["kind"]=="prophecy" and f["cause"] is not None}
    out=[]
    for f in facts:
        if not isinstance(f,dict) or not {"kind","subject","detail","evidence","cause","realm"}<=set(f) or set(f)-{"kind","subject","detail","evidence","cause","realm","other","origin"} or f["kind"] not in KINDS:raise ValueError("invalid destiny fact")
        kind,subject,cause,realm=f["kind"],f["subject"],f["cause"],f["realm"]
        quote=o.clean(f["evidence"],12,240)
        if quote not in story:raise ValueError("destiny fact not quoted")
        if subject is not None:
            if not isinstance(subject,str) or subject not in ACTORS or (subject in {a[0] for a in CAST} and subject not in introduced):raise ValueError("unknown character")
            if ACTORS[subject][0].casefold()[:3] not in quote.casefold():raise ValueError("character not in excerpt")
        if kind=="character" and subject is None:raise ValueError("character required")
        if cause is not None and (type(cause) is not int or not db.execute("SELECT 1 FROM omega_index WHERE number=?",(cause,)).fetchone()):raise ValueError("invalid cause")
        if kind=="prophecy" and cause is not None:
            if cause not in prop or cause in closed:raise ValueError("prophecy not open")
            closed.add(cause)
        if realm is not None and (type(realm) is not int or not 1<=realm<=9):raise ValueError("invalid realm")
        other,origin=f.get("other"),f.get("origin")
        if other is not None:
            if kind!="alliance" or not isinstance(other,str) or other not in ACTORS or other==subject or subject is None or (other in {a[0] for a in CAST} and other not in introduced):raise ValueError("invalid alliance partner")
            if ACTORS[other][0].casefold()[:3] not in quote.casefold():raise ValueError("alliance partner not in excerpt")
        if origin is not None and (kind!="travel" or type(origin) is not int or not 1<=origin<=9 or origin==realm):raise ValueError("invalid travel origin")
        out.append({"kind":kind,"subject":subject,"detail":o.clean(f["detail"],8,180),"evidence":quote,"cause":cause,"realm":realm,"other":other,"origin":origin})
    payload=o.dump({"evidence":evidence,"facts":out})
    source=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()[0]
    db.execute("INSERT INTO destiny_drafts VALUES(?,?,?,?,?,?)",(did,p["beat"],payload,source,o.digest(o.dump([p["beat"],payload,source,VERSION])),VERSION))

def validate_approval(db,did):
    p=read(db,did)
    if p:
        current=plan(db)
        if not current or current["beat"]!=p[0]:raise ValueError("destiny approval unavailable")

def status(db,spoilers=False):
    if audit(db):return "Летопись Eternal Destiny повреждена."
    done=published(db);p=plan(db)
    lines=[f"За пределами девяти небес — {len(done)}/70 этапов.",
           "Следующая: "+p["title"] if p else "Ожидает завершения предыдущих саг." if len(done)<70 else "Том завершён."]
    if spoilers:
        lines.extend(f"{i}. {BEATS[i-1][0]} — {BEATS[i-1][1]}" for i in ORDER)
        lines.extend(GRAPH_ITEMS)
    return "\n".join(lines)

def characters(db):
    if audit(db):return "Летопись повреждена."
    known={b for _,_,b,_ in published(db)}
    return "Новые персонажи (замысел до публикации):\n"+"\n".join(f"{name} — {desc} "+("(введён)" if i in known else "(запланирован)") for i,(_,name,desc) in enumerate(CAST,51))

def timeline(db,kind):
    if audit(db):return "Летопись повреждена."
    lines=[f"Глава {n}: {f['detail']} — «{f['evidence']}»" for _,n,_,p in published(db) for f in p["facts"] if f["kind"]==kind]
    return "\n\n".join(lines[-30:]) or "Пока нет опубликованных записей по этой теме."

def graph(db):
    nodes=[];edges=[];seen=set()
    def node(key,label,kind,area,slot=-1):
        if key in seen:return
        seen.add(key);nodes.append({"key":key,"group":4,"kind":kind,"content":label,"created":"","order":len(nodes),"destiny_topic":area,"destiny_slot":slot})
    def edge(a,b,k,shared=None):
        e={"a":a,"b":b,"kind":"destiny_"+k}
        if shared is not None:e["shared"]=shared
        edges.append(e)
    node("destiny:root","За пределами девяти небес","destiny_root","root")
    edge("canon:13","destiny:root","anchor")
    for t,label in zip(TOPICS,LABELS):
        key="destiny:topic:"+t;node(key,label,"destiny_topic",t);edge("destiny:root",key,"branch")
    for a,b in (("heart:root","love"),("shadow:topic:power","power"),("guardians:root","guardians"),("shadow:topic:court","court"),("character:empress","growth")):edge(a,"destiny:topic:"+b,"bridge")
    for i in range(1,10):edge("realm:"+str(i),"destiny:topic:worlds","realm")
    if audit(db):return nodes,edges
    rows=published(db);previous=None;first_char={};last_travel=None;last_growth=None;last_power=None;chapter_event={n:f"destiny:event:{b}" for _,n,b,_ in rows}
    for did,n,b,data in rows:
        t=topic(b);k=f"destiny:event:{b}";node(k,BEATS[b-1][0]+" · гл. "+str(n),"destiny_event",t,(b-1)*4)
        edge("destiny:topic:"+t,k,"event");edge(f"c:{did}",k,"source")
        if previous:edge(previous,k,"sequence")
        previous=k
        if 51<=b<=60:
            a,name,_=CAST[b-51];key="destiny:actor:"+a;node(key,name,"destiny_character","actor:"+a,-1);edge(k,key,"introduced");first_char[a]=key
        for j,f in enumerate(data["facts"]):
            kind=f["kind"];key=f"destiny:fact:{did}:{j}";area="actor:"+f["subject"] if f["subject"] in first_char else "realm:"+str(f["realm"]) if f["realm"] is not None and kind in ("travel","realm") else t
            node(key,f["detail"],"destiny_fact",area,(b-1)*4+j+1);edge(k,key,kind)
            if kind=="travel":
                if last_travel:edge(last_travel,key,"travel_sequence")
                last_travel=key
            if kind=="growth":
                if last_growth:edge(last_growth,key,"growth_sequence")
                last_growth=key
            if kind=="power":
                if last_power:edge(last_power,key,"power_sequence")
                last_power=key
            if f["subject"] is not None:
                a=f["subject"];target=first_char.get(a) or ("guardian:"+a if a in gu.BY_ID else "character:"+a)
                edge(target,key,"actor")
            if f["realm"] is not None:edge("realm:"+str(f["realm"]),key,"realm")
            if f.get("origin") is not None:edge("realm:"+str(f["origin"]),key,"departure")
            if f.get("other") is not None:
                a=f["other"];target=first_char.get(a) or ("guardian:"+a if a in gu.BY_ID else "character:"+a)
                edge(target,key,"alliance_partner")
            if f["cause"] is not None:
                cause=f["cause"];source=chapter_event.get(cause)
                if source is None:
                    r=db.execute("SELECT draft_id FROM omega_index WHERE number=?",(cause,)).fetchone()
                    source=f"c:{r[0]}" if r and r[0] is not None else f"canon:{cause}"
                edge(source,key,"cause")
    return nodes,edges
