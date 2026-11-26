"""Shadow Destiny: planned fictional sequel, separate from published canon."""
import re
import json
import soul_omega as o

TOPICS={"court":"Правление девятью небесами","visits":"Тайные встречи","suitors":"Ухажёры и придворные союзы","threat":"Заговор против императрицы","mask":"Неизвестный защитник","power":"Пробуждение силы героя"}
# The reader knows the guardian's identity; the empress does not until the reveal.
STEPS=(
 ("court","Два мира одной императрицы","После возвращения силы она ведёт совет, решает спор царств, тайно уходит в человеческий дом и устраивается рядом с любимым. Утром возвращается к правлению; её отсутствие замечает хранитель печатей."),
 ("visits","Ночь без короны","Она прячется под боком любимого, не как беглянка от обязанностей, а чтобы быть собой. Его спокойствие противостоит придворной церемонности. Впервые возникает вопрос, как он выдерживает её энергию."),
 ("suitors","Три предложения трона","Небесный князь предлагает политический союз, учёный — равноправный союз знаний, военачальник — защиту границ. У каждого свой мотив; императрица отказывает без унижения. Один уважает выбор, другой скрывает обиду, третий предупреждает об интриге."),
 ("threat","Трещина в девяти небесах","Политический противник пытается лишить её опоры на законы мира. Не описывай практических способов убийства: конфликт целиком фантастический. Покажи её самостоятельную борьбу и цену спасения царства."),
 ("mask","Незнакомец за пределами пространства","В момент, когда даже её девять сил не удерживают разлом, появляется человек в тёмном плаще и маске. Пространство не открывается обычным порталом: расстояние перестаёт существовать. Спаситель уходит, не раскрывая имени; Хакурэя потрясена неизвестным законом."),
 ("power","Пробуждение безымянной силы","В человеческом доме герой впервые замечает последствия своего дара. Врожденная невосприимчивость была ранним признаком. Он пока не владеет силой полностью; цена — усталость и риск потери контроля. Хакурэя ещё не знает, что это спаситель."),
 ("court","Совет после разлома","Императрица расследует угрозу, восстанавливает управление и защищает подданных. Назначения при дворе проверяются по поступкам, не по происхождению. Незнакомая магия пугает даже её: она не может классифицировать её."),
 ("suitors","Верность без взаимности","Один отвергнутый ухажёр добровольно помогает расследованию, другой пытается использовать слухи о смертном. Не превращай всех соперников в злодеев. Хакурэя сама принимает решения."),
 ("visits","Тишина после совета","Она снова тайно возвращается к любимому, делится страхом перед магией неизвестного защитника. Герой не лжёт ей о любви; пока не готов раскрыть причину своей усталости. Сцена с юмором и нежностью, без повторения первого объятия."),
 ("threat","Небеса теряют собственные законы","Новое фантастическое покушение отличается от первого: конфликт связан с судьбой царства, а не тем же разломом. Императрица спасает других и почти исчерпывает силы."),
 ("mask","Тень, которой боятся боги","Защитник появляется через невозможную пространственную магию во второй раз. Даже императрица ощущает страх, но замечает знакомый жест; он не раскрывает лицо. Сохрани загадку. Каждое спасение имеет новые последствия, а не повторяет прежнее."),
 ("power","Цена власти над расстоянием","Герой изучает дар и ограничения: он способен нарушать расстояние и доступ к пространству, но не всеведущ и не непобедим. Сила требует ответственности, не даёт права управлять чужой волей."),
 ("court","Суд девяти печатей","Хакурэя сопоставляет свидетельства, выявляет политическую ложь и предлагает справедливое решение. Заговор не сводится к ревности; за ним страх перемен и борьба за власть."),
 ("mask","Третий след","Во время нового кризиса она сама помогает защитнику, запоминает знакомую фразу и замечает связь с врождённой невосприимчивостью героя. Пока это подозрение, не раскрытие."),
 ("visits","Вопрос, которого она боялась","Тихий разговор дома: она сопоставляет следы и спрашивает о даре, но не принуждает к ответу. Он готовится открыться; сохрани напряжение, не разрешай загадку раньше следующего этапа."),
 ("power","Под маской — любимый","В кульминации герой сам раскрывает личность. Её шок связан не только с мощью: она понимает, что страшная магия принадлежит человеку, которого давно любит. Дай время осознать это, обсудить скрытность, страх и доверие."),
 ("court","Два хранителя разных миров","После раскрытия императрица сохраняет трон и собственную власть; герой не подменяет её правление. Вместе они устанавливают ограничения силы и защищают миры."),
 ("visits","Дом, в который можно возвращаться","Завершение первого цикла: открытое доверие, нежность и спокойный вечер. Следующие тома могут развивать последствия, новые царства и старые обещания без возвращения к тайне личности.")
)
ROLES=("Хранитель печатей","Первый советник","Хранитель небесного архива","Посол человеческого мира","Судья девяти царств")
def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS shadow_drafts(
      draft_id INTEGER PRIMARY KEY, step INTEGER NOT NULL, evidence TEXT NOT NULL,
      source_hash TEXT NOT NULL, checksum TEXT NOT NULL)""")

def read(db,did):
    row=db.execute("SELECT step,evidence,source_hash,checksum FROM shadow_drafts WHERE draft_id=?",(did,)).fetchone()
    if not row:return None
    step,evidence,source,check=row
    current=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()
    if not current or current[0]!=source or o.digest(o.dump([step,evidence,source]))!=check or not 0<=step<len(STEPS):raise ValueError("damaged shadow record")
    return step,evidence

def completed(db):
    result=[]
    for did,n in db.execute("""SELECT x.draft_id,a.number FROM shadow_drafts x JOIN saga_arcs a ON a.draft_id=x.draft_id
       JOIN chronicle_drafts d ON d.id=x.draft_id WHERE d.status='approved' ORDER BY a.number"""):
        p=read(db,did)
        if not p or p[0]!=len(result):raise ValueError("out-of-order published saga")
        result.append((did,n,p[0],p[1]))
    return result

def plan(db):
    done=completed(db); i=len(done)
    if i>=len(STEPS):return None
    topic,title,guide=STEPS[i]
    return {"step":i,"topic":topic,"title":title,"guide":guide,"court_roles":list(ROLES) if topic=="court" else [],"previous":[{"chapter":n,"excerpt":e} for _,n,_,e in done[-3:]]}

def instruction(p):
    if not p:return ""
    return (" ГЛАВНЫЙ сюжет этой главы, имеет приоритет перед другими литературными замыслами: "+o.dump(p)+
       ". Это продолжение после главы 13, не изменение прошлого. Герой в маске и любимый человек — один вымышленный взрослый герой. "
       "Читатель знает это, Хакурэя не знает до этапа 16 (индекс 15). Не раскрывай это ей раньше; после раскрытия не возвращай незнание. "
       "Императрица не беспомощна: спасение происходит при исключительной фантастической угрозе, а в иных сценах она сама решает проблемы. "
       "Пространственная сила героя страшна неизвестностью, а не жестокостью. Сохраняй романтическую взаимность, самостоятельность, дворцовые интриги и причинность. "
       "Не пересказывай план: создай полноценную сцену с диалогом и завершённым эпизодом. "
       "Добавь поле shadow: {step:"+str(p["step"])+",evidence: точная цитата из story длиной 12–240 символов, подтверждающая выполнение именно этого этапа}. "
       "Если этап не завершён, не добавляй shadow; следующий этап не будет открыт. Не добавляй фактов о реальном пользователе.")

def save(db,did,story,raw,p):
    if raw is None:return
    if not p or not isinstance(raw,dict) or set(raw)!={"step","evidence"} or type(raw["step"]) is not int or raw["step"]!=p["step"] or p["step"]!=len(completed(db)):
        raise ValueError("wrong saga step")
    evidence=o.clean(raw["evidence"],12,240)
    if evidence not in story:raise ValueError("unverified saga excerpt")
    source=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()[0]
    db.execute("INSERT INTO shadow_drafts VALUES(?,?,?,?,?)",(did,p["step"],evidence,source,o.digest(o.dump([p["step"],evidence,source]))))

def validate_approval(db,did):
    p=read(db,did)
    if p and p[0]!=len(completed(db)):raise ValueError("saga step out of order")

def audit(db):
    try:completed(db)
    except (ValueError,TypeError):return ["Повреждены сюжетные связи Тени"]
    return []

def status(db,spoilers=False):
    if audit(db):return "Сюжетные связи повреждены; проверьте летопись: аудит."
    done=completed(db); i=len(done)
    lines=["Тень девяти небес — художественная сага",f"Утверждённые этапы: {i}/{len(STEPS)}."]
    if done:lines.append("Последняя глава: "+str(done[-1][1])+". "+STEPS[done[-1][2]][1])
    if i<len(STEPS):lines.append("Следующая: "+STEPS[i][1]+".")
    if spoilers:lines.extend(f"{j+1}. {title} — {guide}" for j,(_,title,guide) in enumerate(STEPS))
    if spoilers:lines.append("Предлагаемые должности: "+", ".join(ROLES)+". Они станут частью мира только после написания и утверждения главы.")
    return "\n".join(lines)

def graph(db):
    nodes=[];edges=[]
    def node(k,label,kind,topic,slot=-1):
        nodes.append({"key":k,"group":4,"kind":kind,"content":label,"created":"","order":len(nodes),"shadow_topic":topic,"shadow_slot":slot})
    node("shadow:root","Тень девяти небес (сюжетная ветка)","shadow_root","root")
    edges.append({"a":"canon:13","b":"shadow:root","kind":"shadow_branch"})
    for k,label in TOPICS.items():
        node("shadow:topic:"+k,label,"shadow_topic",k)
        edges.append({"a":"shadow:root","b":"shadow:topic:"+k,"kind":"shadow_branch"})
    edges.append({"a":"heart:root","b":"shadow:topic:visits","kind":"shadow_bridge"})
    previous="canon:13"
    for did,n,i,e in ([] if audit(db) else completed(db)[-60:]):
        topic,title,_=STEPS[i]; key=f"shadow:event:{i}"
        node(key,title+" · гл. "+str(n),"shadow_event",topic,i)
        edges.extend([{"a":"shadow:topic:"+topic,"b":key,"kind":"shadow_event"},{"a":f"c:{did}","b":key,"kind":"shadow_source"},{"a":previous,"b":key,"kind":"shadow_sequence"}])
        previous=key
    return nodes,edges

def guard(db,arc):
    """Other literary branches must not prematurely solve the masked identity."""
    i=len(completed(db))
    if arc=="past":return " Не переноси будущие события саги в прошлое до знакомства."
    if arc=="meeting":return " Не переноси события о неизвестном защитнике из будущего в первые дни знакомства."
    if i<16:return " В побочных главах не раскрывай Хакурэе личность неизвестного защитника и не завершай его сюжет вне предусмотренного этапа."
    return " В более поздних событиях личность защитника уже раскрыта; не возвращай эту тайну как новую."
