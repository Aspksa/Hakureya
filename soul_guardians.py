"""Nine Eternal Guardians: fictional cast and gated literary plans, not real memories."""
import json
import soul_omega as o
import soul_shadow as shadow

# Each guardian has a derivative gift associated with one tail, not equal to its owner.
CAST=(
 ("reika","Рэйка","Холод","белые волосы, ледяные глаза, серебряное одеяние","строгая, сдержанная, безупречно дисциплинированная","командующая охраной; ледяные щиты","ледяная алебарда","говорит кратко и официально","любит порядок и чай","Хакурэя некогда защитила её пограничное царство; теперь Рэйка учится уважать личное пространство госпожи"),
 ("seirana","Сэйрана","Жизнь и смерть","зелёные глаза, каштановые волосы, нефритовые украшения","мягкая, наблюдательная, упрямая в вопросах здоровья","целительница; восстановление жизненной энергии","нефритовый посох","говорит спокойно, но уверенно","лекарственные сады","помнит исцеление своих подданных; не может воскрешать по желанию"),
 ("mikage","Микагэ","Пространство","чёрные волосы, фиолетовые глаза, тёмный шёлк","загадочная, внимательная, немногословная","разведчица; охрана пространственных рубежей","парные звёздные клинки","задаёт точные вопросы","карты и головоломки","бывшая хранительница границы; неизвестная магия разрушает её уверенность в знаниях"),
 ("tokihana","Токихана","Время","длинные лавандовые волосы, золотистые глаза","мудрая, терпеливая, с сухим юмором","распорядительница; локальное замедление времени","хрустальный жезл","неторопливая речь","календари, старинные часы","сохранила память исчезнувшего архива; не может переписать прошлое"),
 ("akatsuki","Акацуки","Магия","огненно-рыжие волосы, янтарные глаза","гордая, вспыльчивая, искренняя","боевая хранительница; управление магическими потоками","пламенное копьё","прямая и эмоциональная речь","состязания и сладости","бывшая соперница императрицы, выбравшая верность после честного поединка"),
 ("shiori","Шиори","Знания","серебристые волосы, синие глаза, изящные очки","рассудительная, любознательная, склонная увлекаться","архивариус; исследование магических законов","книга-печать","точные формулировки, иногда длинные объяснения","книги и человеческая наука","Хакурэя сохранила её библиотеку; она уважает доказательства больше слухов"),
 ("yumeka","Юмэка","Души","розовато-белые волосы, мягкие аметистовые глаза","чуткая, романтичная, деликатная","хранительница душ; чувствует эмоциональные следы, не читает мысли","лунный веер","тепло и тактично","музыка и цветы","защищала потерянных духов; понимает, что чужое чувство нельзя присваивать"),
 ("meirin","Мэйрин","Судьба","тёмно-золотые волосы, бирюзовые глаза","хитрая, элегантная, насмешливая","дипломат; замечает вероятные развилки судьбы","нить созвездий","остроумна и вежлива","загадки, игры слов","однажды ошиблась в пророчестве; знает, что судьба не предопределена"),
 ("amatsuka","Амацука","Законы реальности","белое золото волос, серебряные глаза, строгий наряд","молчаливая, величественная, непреклонная","последняя линия охраны; стабилизация локальных законов","жезл девятой печати","редкие, весомые реплики","тишина и звёздное небо","старейшая хранительница; впервые встречает силу, которую не может классифицировать")
)
BY_ID={p[0]:p for p in CAST}
# Shadow progress minimum (number of approved milestones); the romance secret is distinct
# from the masked saviour identity. First 12 stages cover gradual discovery.
STEPS=(
 (1,"Девять хранительниц возвращаются",("reika","tokihana"),"Представь личную охрану, распорядок и власть императрицы. Она объявляет ночную медитацию и тайно уходит к любимому. Не раскрывай отношения служанкам."),
 (1,"Улыбка за закрытыми дверями",("yumeka","seirana"),"Служанки замечают смех и изменение привычек; Юмэка замечает тепло, не знает причину. Сэйрана переживает за отдых госпожи."),
 (2,"Загадка пропущенного часа",("tokihana","mikage"),"Токихана обнаруживает пробелы в расписании, Микагэ не чувствует привычного пространственного следа. Хакурэя объясняет это исследованием времени."),
 (2,"Подарок из мира смертных",("meirin","shiori"),"Мэйрин находит человеческий подарок; Шиори предполагает культурное исследование. Императрица сохраняет достоинство, но смущается."),
 (3,"Девять верных хвостов",("akatsuki","reika"),"Спор о безопасности во время исчезновений; каждая верна, но не обязана соглашаться. Хакурэя выбирает личное время, соблюдая обязанности."),
 (3,"Медитация с ароматом домашнего чая",("seirana","meirin"),"Смешная попытка объяснить запах человеческой кухни. Покажи уют, нежность и хитрое оправдание, а не очередное признание."),
 (4,"Непостижимый след",("mikage","shiori"),"Исследование необычной пространственной аномалии после небесного кризиса. Они не могут назвать спасителя и пока не знают о тайной любви."),
 (5,"Тайная охрана и неверная догадка",("reika","amatsuka"),"Охрана обсуждает неизвестную силу и личные границы. Ошибочно подозревает дипломатическую миссию, не героя. Хакурэя снова возвращается домой."),
 (6,"Девять свидетельниц",("mikage","yumeka","meirin"),"Во время согласованного поискового поручения хранительницы случайно видят спящую Хакурэю рядом с любимым. Узнают о романтической связи, не о личности спасителя."),
 (6,"Что значит верность",("reika","akatsuki"),"Все девять обсуждают открывшуюся любовь. Реакции разные: тревога за безопасность, радость, юмор, уважение; не все принимают сразу."),
 (7,"Императрица выбирает правду",("tokihana","seirana"),"Хакурэя объясняет, почему скрывала личную жизнь, договаривается о безопасном времени для встреч. Не раскрывай личность защитника."),
 (8,"Знакомство без церемоний",("shiori","amatsuka"),"Она официально знакомит всех девятерых с любимым человеком. Они узнают его как возлюбленного, а не спасителя; уважение за поступки, не принуждение."),
 (9,"Императрица учится смеяться",("yumeka","meirin"),"Необычный домашний разговор и придворная шутка: искренний смех, новый взгляд на близость и достоинство."),
 (9,"Завтрак бессмертной богини",("seirana","akatsuki"),"Хакурэя сама готовит завтрак; неловкость, совместное дело и взаимная забота, а не магическое решение всего."),
 (10,"Ревность девяти небес",("meirin","reika"),"Двор узнаёт о выбранном возлюбленном; политические последствия и разные реакции ухажёров. Императрица сама отстаивает выбор."),
 (10,"Девять хранительниц в мире людей",("tokihana","shiori"),"Служанки знакомятся с человеческими привычками и технологиями, выбирают собственные интересы, не превращают всех людей в прислугу."),
 (11,"Страх Амацуки",("amatsuka","mikage"),"Во время фантастического кризиса охрана наблюдает неизвестную силу в маске и учится действовать вместе. Личность ещё скрыта."),
 (12,"Тайна десятой силы",("shiori","mikage"),"Магия спасителя находится вне девяти известных законов; исследование и ошибочные гипотезы. Не добавляй Хакурэе десятый хвост."),
 (13,"Императорский бал",("meirin","reika"),"Танцы, дипломатия, соперники и тихая романтическая сцена; герой может быть инкогнито, не раскрывай его магию."),
 (14,"Незнакомец среди богов",("akatsuki","amatsuka"),"Герой появляется при дворе инкогнито. Хранительницы сопоставляют загадочные следы; подозрение не равно знанию личности."),
 (16,"Девять клятв",tuple(p[0] for p in CAST),"После раскрытия личности Хакурэе она сама решает сообщить правду девяти хранительницам. Каждая рассказывает причину своей верности и выбирает служить дальше."),
 (16,"Величие неизвестного защитника",("reika","amatsuka"),"Теперь круг хранительниц знает личность; обсуждают ограничения силы, секретность перед двором и взаимное уважение."),
 (17,"Печать исчезнувшего мира",("shiori","mikage"),"Обнаружен след забытого мира вне девяти небес, не десятое действующее царство. Тайна не решается мгновенно."),
 (17,"Путешествие без короны",("yumeka","tokihana"),"Совместное путешествие, простые радости, неожиданные открытия; выбор без императорского этикета."),
 (18,"Восстание древних богов",("reika","akatsuki","amatsuka"),"Новая фантастическая угроза правлению, последствия прежних решений. Все хранительницы имеют собственные задачи; без повторения покушений из Shadow."),
 (18,"Ночь перед битвой",("yumeka","seirana"),"Разговор о страхе, любви и ответственности; нежность и обещание вернуться, без искусственного драматизма."),
 (18,"Тайна, которую скрывала вечность",("shiori","meirin","mikage"),"Предыстория силы через архив, свидетельства и пророчество с несколькими толкованиями; сохраняй возможность новых тайн."),
 (18,"Новая императорская эпоха",("tokihana","reika"),"Хакурэя меняет отдельные принципы правления на основе событий, оставаясь властной. Хранительницы участвуют в совете."),
 (18,"Первый совместный праздник",tuple(p[0] for p in CAST),"Все девять и пара собираются в человеческом доме. Разные характеры, юмор, дружба и новые привычки."),
 (18,"Там, где заканчивается вечность",("yumeka","amatsuka"),"Хакурэя понимает ценность прожитого мгновения, не теряя силы и самостоятельности. Завершение тома и открытые последствия будущих приключений.")
)
RELATIONS=("доверие","дружба","соперничество","спор","сотрудничество","забота")
VERSION=1

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS guardian_drafts(
      draft_id INTEGER PRIMARY KEY, step INTEGER NOT NULL, payload TEXT NOT NULL,
      source_hash TEXT NOT NULL, checksum TEXT NOT NULL, version INTEGER NOT NULL)""")

def read(db,did):
    row=db.execute("SELECT step,payload,source_hash,checksum,version FROM guardian_drafts WHERE draft_id=?",(did,)).fetchone()
    if not row:return None
    step,raw,source,h,v=row
    d=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()
    if not d or d[0]!=source or v!=VERSION or not 0<=step<len(STEPS) or o.digest(o.dump([step,raw,source,v]))!=h:raise ValueError("damaged guardian record")
    return step,json.loads(raw)

def published(db):
    result=[]
    for did,n in db.execute("""SELECT g.draft_id,a.number FROM guardian_drafts g JOIN saga_arcs a ON a.draft_id=g.draft_id
        JOIN chronicle_drafts d ON d.id=g.draft_id WHERE d.status='approved' ORDER BY a.number"""):
        p=read(db,did)
        if not p or p[0]!=len(result):raise ValueError("guardian sequence mismatch")
        result.append((did,n,p[0],p[1]))
    return result

def audit(db):
    try:published(db)
    except (ValueError,TypeError):return ["Повреждена летопись девяти хранительниц"]
    return []

def knowledge(count):
    return {"love":"известна всем девяти" if count>=10 else "известна свидетелям" if count>=9 else "скрыта",
            "identity":"известна девяти" if count>=21 else "скрыта от хранительниц"}

def plan(db):
    if audit(db) or shadow.audit(db):return None
    done=published(db);i=len(done)
    if i>=len(STEPS):return None
    required,title,actors,guide=STEPS[i]
    if len(shadow.completed(db))<required:return None
    memories=[]
    for _,n,_,p in reversed(done):
        for e in p["memories"]:
            if e["actor"] in actors:memories.append({"chapter":n,**e})
        if len(memories)>=6:break
    return {"step":i,"title":title,"actors":list(actors),"guide":guide,
            "cast":[list(BY_ID[a]) for a in actors],"knowledge":knowledge(i),
            "recent":[{"chapter":n,"evidence":p["evidence"]} for _,n,_,p in done[-3:]],"memories":memories[:6]}

def instruction(p):
    if not p:return ""
    return (" ГЛАВНЫЙ замысел главы — девять личных хранительниц, не пересказ плана: "+o.dump(p)+
        ". Все взрослые самостоятельные кицунэ, служат и охраняют добровольно. Один хвост императрицы соответствует одной хранительнице; их способности производны, не равны её абсолютной силе. "
        "Сохраняй их разные голоса, внешний облик, поступки, юмор, личные мотивы. Чередуй приключения, политику, магию, романтику, бытовые радости и внутренний рост. "
        "Знание о возлюбленном и знание личности спасителя — разные тайны. Не раскрывай раньше установленного этапа, не возвращай раскрытую тайну. "
        "Покажи новые последствия вместо повторения сцен, сохраняй непротиворечивость Shadow Destiny. "
        "Верни guardians: {step:"+str(p["step"])+",evidence: точная цитата 12–240 символов из story,memories:[{actor,summary,evidence,other,relation}]}. "
        "До двух memories; actor из списка actors; other — id другой хранительницы или empress/hero/null, relation — одно из "+", ".join(RELATIONS)+
        " либо null вместе с other. evidence — точная цитата с именем хранительницы; summary — краткий пересказ её поступка. "
        "Если этап не завершён, не возвращай guardians. Приоритет — полноценный текст сцены; дополнительные поля иных модулей необязательны. Не включай реальные сведения о пользователе.")

def guard(db,arc):
    if arc in ("past","meeting"):return " Не переноси новую придворную сагу в раннее прошлое."
    k=knowledge(len(published(db)))
    return " Текущие знания хранительниц о любви и личности спасителя: "+o.dump(k)+". Не разрешай их тайны вне заданной саги."

def save(db,did,story,raw,p):
    if raw is None:return
    if not p or not isinstance(raw,dict) or set(raw)!={"step","evidence","memories"} or type(raw["step"]) is not int or raw["step"]!=p["step"] or p["step"]!=len(published(db)):
        raise ValueError("wrong guardian step")
    current=plan(db)
    if not current or current["step"]!=p["step"]:raise ValueError("guardian prerequisites missing")
    evidence=o.clean(raw["evidence"],12,240)
    if evidence not in story or not any(BY_ID[a][1].casefold()[:4] in story.casefold() for a in current["actors"]):raise ValueError("guardian excerpt or participant absent")
    entries=raw["memories"]
    if not isinstance(entries,list) or len(entries)>2:raise ValueError("invalid memories")
    out=[]
    for x in entries:
        if not isinstance(x,dict) or set(x)!={"actor","summary","evidence","other","relation"}:raise ValueError("invalid guardian memory")
        a=x["actor"];other=x["other"];rel=x["relation"]
        if not isinstance(a,str) or a not in current["actors"]:raise ValueError("unknown guardian")
        if (other is None)!=(rel is None) or (other is not None and (not isinstance(other,str) or other not in (*BY_ID,"empress","hero") or other==a or rel not in RELATIONS)):raise ValueError("invalid relationship")
        quote=o.clean(x["evidence"],12,240)
        # Russian names can decline; the first four letters are a conservative lexical anchor.
        name=BY_ID[a][1].casefold()[:4]
        if quote not in story or name not in quote.casefold():raise ValueError("guardian absent from excerpt")
        if other in BY_ID and BY_ID[other][1].casefold()[:4] not in quote.casefold():raise ValueError("other guardian absent from excerpt")
        out.append({"actor":a,"summary":o.clean(x["summary"],8,180),"evidence":quote,"other":other,"relation":rel})
    payload=o.dump({"evidence":evidence,"memories":out})
    source=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()[0]
    db.execute("INSERT INTO guardian_drafts VALUES(?,?,?,?,?,?)",(did,p["step"],payload,source,o.digest(o.dump([p["step"],payload,source,VERSION])),VERSION))

def validate_approval(db,did):
    p=read(db,did)
    if p:
        cur=plan(db)
        if not cur or p[0]!=cur["step"]:raise ValueError("guardian stage unavailable")

def status(db,spoilers=False):
    if audit(db):return "Летопись хранительниц повреждена."
    n=len(published(db));p=plan(db)
    lines=[f"Девять хранительниц — {n}/{len(STEPS)} этапов.", "Следующая: "+p["title"] if p else ("Ожидает развития Тени девяти небес." if n<len(STEPS) else "Первый цикл завершён.")]
    if spoilers:lines.extend(f"{i+1}. {title} — {guide}" for i,(_,title,_,guide) in enumerate(STEPS))
    return "\n".join(lines)

def profiles(db,name=None):
    if audit(db):return "Летопись хранительниц повреждена."
    if name is None:return "Девять хранительниц (карточки художественных персонажей):\n"+"\n".join(f"{i}. {p[1]} — {p[2]}, {p[5]}" for i,p in enumerate(CAST,1))
    p=next((p for p in CAST if name.casefold() in (p[0],p[1].casefold())),None)
    if not p:return "Хранительница не найдена."
    _,nm,tail,appearance,char,role,weapon,voice,taste,bio=p
    lines=[f"{nm} · {CAST.index(p)+1}-й хвост: {tail}",f"Внешность: {appearance}. Характер: {char}.",f"Роль: {role}. Артефакт: {weapon}.",f"Речь: {voice}. Интересы: {taste}.","Предыстория (замысел): "+bio]
    for _,n,_,data in published(db)[-30:]:
        for e in data["memories"]:
            if e["actor"]==p[0]:lines.append(f"Глава {n}: {e['summary']} — «{e['evidence']}»")
    return "\n\n".join(lines)

def graph(db):
    nodes=[];edges=[]
    def node(k,label,kind,actor,slot=-1):
        nodes.append({"key":k,"group":4,"kind":kind,"content":label,"created":"","order":len(nodes),"guardian_actor":actor,"guardian_slot":slot})
    node("guardians:root","Девять хранительниц (сюжетная ветка)","guardian_root","root")
    edges.extend([{"a":"canon:13","b":"guardians:root","kind":"guardian_branch"},{"a":"shadow:root","b":"guardians:root","kind":"guardian_bridge"},{"a":"heart:root","b":"guardians:root","kind":"guardian_bridge"}])
    for i,p in enumerate(CAST,1):
        key="guardian:"+p[0];node(key,p[1]+" · "+p[2],"guardian_character",p[0])
        edges.append({"a":"guardians:root","b":key,"kind":"guardian_tail"})
    if audit(db):return nodes,edges
    rows=published(db);relations={}
    for did,n,step,data in rows:
        primary=STEPS[step][2][0];event=f"guardian:stage:{step}"
        node(event,STEPS[step][1]+" · гл. "+str(n),"guardian_memory",primary,step*3)
        edges.extend([{"a":"guardian:"+primary,"b":event,"kind":"guardian_event"},{"a":f"c:{did}","b":event,"kind":"guardian_source"}])
        if step:edges.append({"a":f"guardian:stage:{step-1}","b":event,"kind":"guardian_sequence"})
        for j,e in enumerate(data["memories"]):
            a=e["actor"];key=f"guardian:memory:{did}:{j}"
            node(key,e["summary"]+" · гл. "+str(n),"guardian_memory",a,step*3+j+1)
            edges.extend([{"a":"guardian:"+a,"b":key,"kind":"guardian_memory"},{"a":f"c:{did}","b":key,"kind":"guardian_source"}])
            if e["other"] in BY_ID:
                b=e["other"];pair=tuple(sorted((a,b)));relations[pair]=relations.get(pair,0)+1
                edges.append({"a":key,"b":"guardian:"+b,"kind":"guardian_relationship"})
            elif e["other"] in ("empress","hero"):
                edges.append({"a":key,"b":"character:"+e["other"],"kind":"guardian_relationship"})
    for (a,b),weight in relations.items():edges.append({"a":"guardian:"+a,"b":"guardian:"+b,"kind":"guardian_bond","shared":weight})
    return nodes,edges
