"""Hierarchical literary atlas: bounded snapshots with real publication counts."""
import soul_omega as o
MAX_NODES=96
MAX_VOLUME=1_000_000

def volume_bounds(first,last):
    return (1 if first==1 else 14+(first-2)*12,13 if last==1 else 25+(last-2)*12)

def snapshot(db,first=None,last=None):
    import soul_chronicle as ch
    if not ch.canon_ok(db):raise ValueError("canon integrity")
    max_number=db.execute("SELECT COALESCE(MAX(number),13) FROM omega_index").fetchone()[0]
    max_volume=o.volume(max_number)
    root=first is None and last is None
    if root:first,last=1,max_volume
    if type(first) is not int or type(last) is not int or not 1<=first<=last<=max_volume or last>MAX_VOLUME:
        raise ValueError("invalid atlas range")
    width=1
    while (last-first+width)//width>MAX_NODES:width*=16
    records=[];edges=[]
    for a in range(first,last+1,width):
        b=min(last,a+width-1)
        low,high=volume_bounds(a,b)
        count=db.execute("SELECT COUNT(*) FROM omega_index WHERE number BETWEEN ? AND ?",(low,high)).fetchone()[0]
        if not count:continue
        key=f"book:{a}" if a==b else f"atlas:{a}:{b}"
        title=f"Том {a}" if a==b else f"Тома {a}–{b}"
        records.append(dict(key=key,label=title+f" · {count} частей",group=4,kind="book" if a==b else "atlas_region",slot=len(records),chapter_count=count,volume_complete=count==high-low+1))
        if len(records)>1:edges.append(dict(a=records[-2]["key"],b=key,kind="publication_order"))
    low,high=volume_bounds(first,last)
    count=db.execute("SELECT COUNT(*) FROM omega_index WHERE number BETWEEN ? AND ?",(low,high)).fetchone()[0]
    return dict(records=records,edges=edges,total=count,limited=False,atlas=f"{first}:{last}",atlas_root=root,atlas_max=max_volume,atlas_width=width,detail_count=len(records))
