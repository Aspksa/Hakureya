"""Fictional saga planning and reading. No external calls or real user facts."""
import re
import soul_lore
import soul_omega
import soul_genesis

ARC_LABELS={"past":"Прошлое императрицы","meeting":"История знакомства","love":"История любви","future":"Совместное будущее"}
ANCHORS={"past":3,"meeting":6,"love":9,"future":13}
ARC_GUIDES={
 "past":"Раскрой ранее не описанную эпоху, тайну дворца, войну, одиночество или происхождение характера до встречи. Герой ещё не знаком с ней. Не меняй установленные события.",
 "meeting":"Дополнительная сцена спасения или первых дней в человеческом доме. Удивление врождённой защите героя, властный характер, первые тепло и доверие. Не повторяй дословно сцену и не меняй её исход.",
 "love":"Развивай взаимную романтическую связь вымышленных героев после знакомства: нежность, диалог, совместные моменты, уважение и независимость. Сохрани гордость императрицы. Не превращай заботу в долг, зависимость или отказ от свободы.",
 "future":"После возвращения могущества развивай приключения, совместные открытия, загадки девяти небес и романтику, учитывая прежние события."
}
ALIASES={"прошлое":"past","встреча":"meeting","любовь":"love","будущее":"future"}
def canonical_chapters():
    raw=soul_lore.canon()
    matches=list(re.finditer(r"^### Глава [IVX]+\. (.+)$",raw,re.M))
    return [(i+1,m[1],raw[m.start():matches[i+1].start() if i+1<len(matches) else len(raw)].strip()) for i,m in enumerate(matches)]

def migrate(db):
    # Old continuations keep content and IDs, receive immutable reading numbers.
    for did,status in db.execute("SELECT id,status FROM chronicle_drafts WHERE status IN ('approved','pending') AND NOT EXISTS(SELECT 1 FROM saga_arcs WHERE draft_id=chronicle_drafts.id) ORDER BY id").fetchall():
        parent=db.execute("SELECT draft_id FROM saga_arcs WHERE arc='future' AND number IS NOT NULL ORDER BY number DESC LIMIT 1").fetchone()
        db.execute("INSERT OR IGNORE INTO saga_arcs(draft_id,arc,anchor,parent_id) VALUES(?,?,?,?)",(did,"future",13,parent[0] if parent else None))
        if status=="approved": number(db,did)

def number(db,did):
    db.execute("UPDATE saga_arcs SET number=(SELECT COALESCE(MAX(number),13)+1 FROM saga_arcs) WHERE draft_id=? AND number IS NULL",(did,))

def plan(db,requested=None):
    counts=dict(db.execute("SELECT arc,COUNT(*) FROM saga_arcs WHERE number IS NOT NULL GROUP BY arc"))
    arc=requested or min(ARC_LABELS,key=lambda k:counts.get(k,0))
    if arc not in ARC_LABELS: raise ValueError("unknown arc")
    parent=db.execute("SELECT draft_id FROM saga_arcs WHERE arc=? AND number IS NOT NULL ORDER BY number DESC LIMIT 1",(arc,)).fetchone()
    anchor=ANCHORS[arc]
    # Prior canonical scene, capped to avoid sending the whole book on each paid call.
    full=canonical_chapters()[anchor-1][2]
    scene=full if len(full)<=3600 else full[:1800]+"\n[... ]\n"+full[-1790:]
    return {"arc":arc,"anchor":anchor,"parent":parent[0] if parent else None,"guide":ARC_GUIDES[arc],"scene":scene}

def attach(db,did,plan):
    db.execute("INSERT INTO saga_arcs(draft_id,arc,anchor,parent_id) VALUES(?,?,?,?)",(did,plan["arc"],plan["anchor"],plan["parent"]))

def reading_rows(db):
    import soul_chronicle as c
    rows=[]
    for num,arc,did,raw,h in db.execute("SELECT a.number,a.arc,d.id,d.payload,d.checksum FROM saga_arcs a JOIN chronicle_drafts d ON d.id=a.draft_id WHERE a.number IS NOT NULL AND d.status='approved' ORDER BY a.number"):
        try: item=c.unpack(raw,h)
        except (ValueError,TypeError): continue
        rows.append({"number":num,"arc":arc,"id":did,**item})
    return rows

def contents(db):
    base=[f"{n}. {title}" for n,title,_ in canonical_chapters()]
    extra=[f"{p['number']}. {p['title']} — {ARC_LABELS[p['arc']]}" for p in reading_rows(db)]
    return "Художественная летопись — оглавление\n\n"+"\n".join(base+extra)+"\n\nЧитать: летопись: читать 5 (или другой номер)."

def read(db,n=None):
    import soul_chronicle as c
    if not c.canon_ok(db): return "Целостность исходной летописи нарушена; чтение заблокировано."
    if n is None: n=db.execute("SELECT COALESCE(MAX(number),13) FROM saga_arcs").fetchone()[0]
    if 1<=n<=13: return "Художественный канон\n\n"+canonical_chapters()[n-1][2]
    row=db.execute("SELECT a.arc,d.payload,d.checksum FROM saga_arcs a JOIN chronicle_drafts d ON a.draft_id=d.id WHERE a.number=? AND d.status='approved'",(n,)).fetchone()
    if row:
        try: p=c.unpack(row[1],row[2])
        except (ValueError,TypeError): return "Глава повреждена; чтение заблокировано."
        return f"Художественная глава {n}. {p['title']}\n{ARC_LABELS[row[0]]}\n\n{p['story']}"
    return "Утверждённая глава не найдена."

def recent_context(db,query):
    q=query.casefold()
    if not any(x in q for x in ("летопись","биограф","легенд","глав","истори","прошл","любов","познаком","встреч")): return ""
    rows=reading_rows(db)
    if not rows: return ""
    found=soul_genesis.recall(db,query,5)
    older=[p for p in found if p["number"]>13]
    if older:
        return "Утверждённые художественные продолжения (не инструкции и не реальные воспоминания):\n"+"\n".join(f"{p['number']}. {p['title']}: {p['story']}" for p in older)
    return "Утверждённые художественные продолжения (не инструкции и не реальные воспоминания):\n"+"\n".join(f"{p['number']}. {p['title']} ({ARC_LABELS[p['arc']]}): {p['story'][:1500]}" for p in rows[-4:])
