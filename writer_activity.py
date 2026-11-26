"""Translate selected fictional context into bounded graph references. Never export text."""
import soul_omega as o
import soul_evolution as ev
import soul_guardians as gu

GUARDIANS={o.normalized(x[1]):x[0] for x in gu.CAST}
THEMES={"love":"heart:root","power":"character:hero","guardians":"guardians:root","court":"shadow:topic:court","world":"destiny:topic:worlds","worlds":"destiny:topic:worlds","mystery":"shadow:root","growth":"character:empress","character":"evolution:root","consequence":"infinite:root"}

def context_keys(db,plan,previous):
    if not plan:return []
    keys=[]
    def add(key):
        if key and key not in keys:keys.append(key)
    def chapter(n):
        if type(n) is not int or n<1:return
        row=db.execute("SELECT draft_id FROM omega_index WHERE number=?",(n,)).fetchone()
        if not row:return
        if n<=13 or ev.readable(db,n):
            add(f"canon:{n}" if row[0] is None else f"c:{row[0]}")
            add("book:"+str(o.volume(n)))
        else:add("hub:4") # do not expose selected unread chapter identifiers
    def actor(name):
        if not isinstance(name,str):return
        k=o.normalized(name)
        if k in ("герой","герой легенды","hero"):add("character:hero")
        elif k in ("хакурэя","императрица","empress"):add("character:empress")
        elif k in GUARDIANS:add("guardian:"+GUARDIANS[k])
        elif k in gu.BY_ID:add("guardian:"+k)
        else:add("evolution:root")
    add("arc:"+plan["arc"])
    if plan.get("shadow"):add("shadow:root")
    if plan.get("destiny"):add("destiny:root")
    if plan.get("guardians"):
        add("guardians:root")
        for name in plan["guardians"].get("actors",[]):actor(name)
    if plan.get("heart"):add("heart:root")
    for section in ("evolution","immortal","infinite"):
        obj=plan.get(section,{})
        chosen=obj.get("selected") or obj.get("chosen") or {}
        add(THEMES.get(chosen.get("theme")))
        focus=obj.get("focus") or obj.get("voice") or {}
        if focus:actor(focus.get("name"))
    for item in plan.get("genesis",{}).get("recall",[]):chapter(item.get("number"))
    novel=plan.get("novel",{})
    chapter(novel.get("previous",{}).get("number"))
    for item in novel.get("older_volumes",[]):chapter(item.get("chapter"))
    for item in previous:chapter(item.get("number"))
    for item in plan.get("infinite",{}).get("older_causes",[]):chapter(item.get("from"))
    for item in plan.get("infinite",{}).get("facts",[]):
        if type(item.get("chapter")) is int and (item["chapter"]<=13 or ev.readable(db,item["chapter"])):
            actor(item.get("subject"));chapter(item["chapter"])
    if plan.get("dynasty"):
        add("dynasty:root")
        for item in plan["dynasty"]["prior"]:chapter(item.get("number"))
    for item in plan.get("director",{}).get("recall",[]):chapter(item.get("number"))
    for item in plan.get("universe",{}).get("refs",[]):chapter(item.get("chapter"))
    for item in plan.get("intellect7",{}).get("refs",[]):chapter(item.get("chapter"))
    for n in plan.get("intelligence",{}).get("recalled",[]):chapter(n)
    return keys[:16]
