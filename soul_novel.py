"""Eternal Novel: a presentation and planning layer over immutable published scenes."""
import json
import re
from collections import Counter
import soul_omega as o
import soul_romance as romance
import soul_living as living
import soul_evolution as ev
import soul_immortal as im
import soul_saga as saga

TARGETS={"короткая":1500,"обычная":2500,"большая":4500}
VERSION=1
THEMES=(
 ("love","Тихая сторона вечности","Взаимная любовь и быт; решение, юмор, семейная традиция."),
 ("power","Цена нового дара","Исследуй пространственную магию и её пределы без переписывания канона."),
 ("guardians","Судьба хранительницы","Самостоятельная миссия, личная цель и последствия."),
 ("court","Девять небес","Параллельное событие в одном из девяти небес; правитель и мотивы."),
 ("mystery","След давнего решения","Возврати зрелую подсказку или незавершённое обещание."),
 ("world","Мир за горизонтом","Исследование мира, его жителей и последствий магии."),
 ("growth","Выбор императрицы","Покажи изменение через решение, а не декларацию."),
 ("character","Знакомое лицо","Возвращение персонажа с собственной жизнью и целью.")
)

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS novel_parts(
      draft_id INTEGER PRIMARY KEY, chapter_start INTEGER NOT NULL, part INTEGER NOT NULL,
      target INTEGER NOT NULL, source_hash TEXT NOT NULL, checksum TEXT NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS novel_group ON novel_parts(chapter_start,part)")
    db.execute("""CREATE TABLE IF NOT EXISTS novel_forecast(
      id INTEGER PRIMARY KEY CHECK(id=1),payload TEXT NOT NULL,checksum TEXT NOT NULL)""")

def checksum(did,start,part,target,source):
    return o.digest(o.dump([VERSION,did,start,part,target,source]))

def record(db,did):
    row=db.execute("SELECT chapter_start,part,target,source_hash,checksum FROM novel_parts WHERE draft_id=?",(did,)).fetchone()
    if not row:return None
    start,part,target,source,check=row
    base=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()
    if not base or base[0]!=source or check!=checksum(did,start,part,target,source) or not (start>=14 and 1<=part<=12 and 500<=target<=7500):
        raise ValueError("damaged novel part")
    return {"start":start,"part":part,"target":target}

def published_group(db,start):
    import soul_chronicle as c
    rows=db.execute("""SELECT a.number,a.arc,d.id,d.payload,d.checksum FROM novel_parts p
      JOIN saga_arcs a ON a.draft_id=p.draft_id JOIN chronicle_drafts d ON d.id=p.draft_id
      WHERE p.chapter_start=? AND d.status='approved' ORDER BY a.number""",(start,)).fetchall()
    result=[]
    for i,(n,arc,did,raw,h) in enumerate(rows):
        p=record(db,did)
        if n!=start+i or p["part"]!=i+1 or o.volume(n)!=o.volume(start) or (result and (arc!=result[0]["arc"] or p["target"]!=result[0]["target"])):
            raise ValueError("noncontiguous novel group")
        result.append({"number":n,"arc":arc,"id":did,**c.unpack(raw,h),**p})
    return result

def group_for(db,n):
    row=db.execute("SELECT draft_id FROM omega_index WHERE number=?",(n,)).fetchone()
    if not row or row[0] is None:return []
    p=record(db,row[0])
    return published_group(db,p["start"]) if p else []

def next_group(db,arc,cycle=None):
    last=db.execute("SELECT number,arc,draft_id FROM omega_index ORDER BY number DESC LIMIT 1").fetchone()
    n=last[0]+1
    import soul_universe
    pages=soul_universe.chapter_pages(db)
    # Approximation: 250 words per 1800-character manuscript page.
    # The existing 12-part / volume safety boundary still applies.
    target=cycle["target"] if cycle else pages*250 if pages else TARGETS[im.preferences(db)[0]]
    if last[2] is not None and last[1]==arc:
        p=record(db,last[2])
        if p:
            rows=published_group(db,p["start"])
            count=sum(len(re.findall(r"\b\w+\b",x["story"])) for x in rows)
            if count<p["target"] and p["part"]<12 and o.volume(n)==o.volume(p["start"]):
                return {"start":p["start"],"part":p["part"]+1,"target":p["target"],"written":count,
                        "title":rows[0]["title"],"ending":rows[-1]["story"][-2200:],"previous_number":last[0]}
    return {"start":n,"part":1,"target":target,"written":0,"title":"","ending":"","previous_number":last[0]}

def enrich(db,plan):
    if plan.get("alternative"):return plan
    p=next_group(db,plan["arc"],romance.current_cycle(db))
    # The actual source and its ending, not a generated summary, anchor continuation.
    last=db.execute("SELECT number,title,story FROM omega_index WHERE arc=? ORDER BY number DESC LIMIT 1",(plan["arc"],)).fetchone()
    if last:
        p["previous"]={"number":last[0],"title":last[1],"ending":last[2][-2200:]}
    # Bounded cross-volume memory; cite real earlier events and their chapter numbers.
    earlier=[]
    last_volume=o.volume(p["previous_number"])
    for v in range(max(1,last_volume-4),last_volume):
        low,high=(1,13) if v==1 else (14+(v-2)*12,25+(v-2)*12)
        row=db.execute("SELECT number,title,story,draft_id FROM omega_index WHERE number BETWEEN ? AND ? ORDER BY number DESC LIMIT 1",(low,high)).fetchone()
        if row:
            n,title,story,did=row;m=o.metadata(db,did) if did else None
            earlier.append({"volume":v,"chapter":n,"title":title,"ending":story[-500:],"events":m["data"]["events"][:2] if m else []})
    p["older_volumes"]=earlier
    # Existing narrative directors have priority, no new canon facts from the forecast.
    p["open_threads"]=plan.get("evolution",{}).get("obligations",[])[:3]
    p["mysteries"]=plan.get("living",{}).get("open",[])[:3]
    p["guardian_focus"]=1+(p["previous_number"]%9)
    p["heaven_focus"]=1+((p["previous_number"]//2)%9)
    plan["novel"]=p
    if not plan.get("dynasty_lane") and plan["arc"]=="future" and not any(k in plan for k in ("shadow","guardians","destiny")) and "cycle_id" not in plan.get("romance",{}) and not plan.get("evolution",{}).get("chosen",{}).get("scene") and not plan.get("immortal",{}).get("chosen") and im.ready(db):
        head=forecast(db)["items"][0]
        p["next_line"]={"title":head["title"],"guide":head["guide"],"theme":head["theme"]}
    return plan

def instruction(plan):
    p=plan.get("novel")
    if not p:return ""
    return (" Eternal Novel: "+o.dump(p)+
      ". Это следующая полноценная часть художественной главы, не краткий пересказ. "
      "Пиши максимально содержательную сцену в пределах текущего лимита, закончи полным предложением. "
      "При part>1 начинай непосредственно после последней реплики или действия, не повторяй ending, заголовок, аннотацию или вступление. "
      "Объём target относится ко всей группе частей, не к одному ответу. Не сжимай весь замысел в один абзац. "
      "Следуй обязательным этапам старых саг; развивай конфликт через причины и последствия, естественные диалоги и действия. Если есть next_line, используй этот замысел как новую линию после завершения обязательных этапов. "
      "Сохраняй достоинство и самостоятельность обоих влюблённых, юмор, разные голоса хранительниц, врождённую защиту героя и границы магии. "
      "При уместности покажи параллельное событие в одном из девяти небес и собственную цель одной хранительницы; не добавляй десятое небо. "
      "Возвращай ранее посеянные улики и обещания, не раскрывай незрелые тайны. Не придумывай события прошлых томов. "
      "Сохрани стиль и канон. Не пересказывай последние абзацы и не печатай служебные заголовки в story.")

def save(db,did,base,plan):
    p=plan.get("novel")
    if not p:return
    # Existing romance/omega checks handle long repeated passages and contradictory metadata.
    ending=p.get("ending") or p.get("previous",{}).get("ending","")
    # Reject verbatim overlap of 12+ words across the boundary.
    old=romance.words(ending);new=romance.words(base["story"])
    for size in range(min(60,len(old),len(new)),11,-1):
        if old[-size:]==new[:size]:raise ValueError("novel boundary repeated")
    source=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()[0]
    db.execute("INSERT INTO novel_parts VALUES(?,?,?,?,?,?)",(did,p["start"],p["part"],p["target"],source,checksum(did,p["start"],p["part"],p["target"],source)))

def validate_approval(db,did):
    p=record(db,did)
    if not p:return
    arc=db.execute("SELECT arc FROM saga_arcs WHERE draft_id=?",(did,)).fetchone()[0]
    expected=next_group(db,arc,romance.current_cycle(db))
    if any(p[k]!=expected[k] for k in ("start","part","target")):
        # Target is frozen at draft creation; changing preference cannot invalidate a first part.
        if p["part"]!=1 or p["start"]!=expected["start"] or expected["part"]!=1:raise ValueError("novel sequence changed")

def audit(db):
    try:
        for start, in db.execute("SELECT DISTINCT p.chapter_start FROM novel_parts p JOIN chronicle_drafts d ON d.id=p.draft_id WHERE d.status='approved'"):
            published_group(db,start)
    except (ValueError,TypeError,KeyError):return ["Повреждены части романа"]
    return []

def forecast(db):
    # Reuse the old queue's prerequisite simulation, then include actual remaining evolution and Immortal stages.
    base=living.queue(db,limit=118)
    latest=base["based_on"]
    items=[dict(x) for x in base["items"] if x["theme"]=="fixed"]
    for p in ev.candidates(db,list(ev.published(db))):
        if p["scene"]:items.append({"title":p["title"],"theme":p["theme"],"guide":p["guide"]})
    done=sum(p["step"] is not None for _,_,p in im.published(db))
    for i,phase in im.ORDER[done:]:
        if i<10:
            _,title,theme,guide=im.SAGAS[i];title+=" — "+im.PHASES[phase]
        else:title,guide=im.DAILY[i-10];theme="love"
        items.append({"title":title,"theme":theme,"guide":guide})
    import soul_infinite
    items.extend(soul_infinite.remaining(db))
    recent=Counter(p["theme"] for _,_,p in living.published(db))
    rank=sorted(THEMES,key=lambda x:(recent[x[0]],x[0]))
    while len(items)<100:
        i=len(items);theme,title,guide=rank[(i+latest)%len(rank)]
        # A proposal, not an established story event.
        items.append({"title":title+" — новая линия","theme":theme,"guide":guide})
    for i,p in enumerate(items[:100]):
        p.update(number=latest+i+1,volume=o.volume(latest+i+1),epoch=1+(o.volume(latest+i+1)-1)//8)
    payload={"based_on":latest,"items":items[:100],"version":VERSION}
    raw=o.dump(payload)
    db.execute("INSERT INTO novel_forecast VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,checksum=excluded.checksum WHERE checksum!=excluded.checksum",(raw,o.digest(raw)))
    return payload

def status(db):
    n=db.execute("SELECT MAX(number) FROM omega_index").fetchone()[0]
    rows=group_for(db,n) if n else []
    if not rows:return "Новая длинная глава ещё не начата."
    written=sum(len(re.findall(r"\b\w+\b",p["story"])) for p in rows)
    return f"Глава {rows[0]['number']}: {len(rows)} частей, {written}/{rows[0]['target']} слов. Части сохранены в SQLite. Том {o.volume(n)}; эпоха {1+(o.volume(n)-1)//8}."


def graph(db):
    # A small, spoiler-neutral layer of assembled chapters and chronological eras.
    nodes=[];edges=[];seen=set()
    def node(key,label,kind):
        if key not in seen:
            seen.add(key);nodes.append({"key":key,"group":4,"content":label,"kind":kind,"created":"","order":len(nodes)})
    groups=db.execute("""SELECT DISTINCT p.chapter_start FROM novel_parts p
      JOIN chronicle_drafts d ON d.id=p.draft_id WHERE d.status='approved' ORDER BY p.chapter_start DESC LIMIT 36""").fetchall()
    for start, in reversed(groups):
        try:parts=published_group(db,start)
        except (ValueError,TypeError,KeyError):continue
        if not parts:continue
        volume=o.volume(start);epoch=1+(volume-1)//8
        e=f"novel:epoch:{epoch}";g=f"novel:chapter:{start}"
        node(e,f"Литературная эпоха {epoch}","novel_epoch")
        node(g,f"Большая глава {start} · {len(parts)} ч.","novel_chapter")
        edges.extend([{"a":"immortal:root","b":e,"kind":"immortal_branch"},{"a":e,"b":g,"kind":"immortal_branch"},{"a":f"book:{volume}","b":g,"kind":"book_chapter"}])
        for p in parts:edges.append({"a":g,"b":f"c:{p['id']}","kind":"immortal_source"})
    return nodes,edges
