import json
import sqlite3
import unittest
from datetime import datetime, timezone

import memory_graph
import soul_core
import soul_chronicle as c
import soul_saga as saga
import soul_novel as novel
import soul_universe as u
import soul_narrative as n
import soul_embeddings as vectors
import soul_proposals as proposals
import soul_evolution as ev
from test_omega import chapter

class NarrativeTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY,role TEXT,content TEXT,created TEXT)")
        memory_graph.init(self.db);soul_core.init(self.db);proposals.init(self.db)

    def publish(self,day,story,approve=True,arc="future"):
        plan=novel.enrich(self.db,saga.plan(self.db,arc))
        value=chapter("Новая часть "+str(day));value.pop("literary")
        value["story"]=story
        res=c.reserve(self.db,datetime(2099,3,day,tzinfo=timezone.utc),allow_story=True)
        c.finish(self.db,res,value,plan)
        did=c.latest_pending(self.db)["id"]
        if approve is not None:self.assertTrue(c.decide(self.db,did,approve))
        return did,plan

    def test_batch_survives_init_and_repairs_cache(self):
        self.assertEqual(n.refresh(self.db,limit=3),3)
        self.assertEqual(n.status(self.db)["indexed"],3)
        self.assertEqual(n.status(self.db)["pending"],10)
        n.init(self.db)
        self.assertEqual(n.refresh(self.db,limit=4),4)
        self.assertEqual(n.refresh(self.db),6)
        self.assertEqual(n.refresh(self.db),0)
        self.assertEqual(n.status(self.db)["pending"],0)
        self.assertIn("подтверждена",n.audit(self.db))
        for chapter_id,story in self.db.execute("SELECT number,story FROM omega_index"):
            for x in n.read(self.db,chapter_id)["extracts"]:
                self.assertEqual(x["quote"],story[x["start"]:x["end"]])
        self.db.execute("UPDATE narrative_sources SET payload='bad' WHERE chapter=3")
        with self.assertRaises(ValueError):n.read(self.db,3)
        self.assertIn("повреждена",n.audit(self.db))
        self.assertEqual(n.sweep(self.db),1)
        self.assertIn("подтверждена",n.audit(self.db))
        before=list(self.db.execute("SELECT number,story,checksum FROM omega_index ORDER BY number"))
        self.assertEqual(n.repair(self.db),13)
        self.assertEqual(before,list(self.db.execute("SELECT number,story,checksum FROM omega_index ORDER BY number")))

    def test_only_approved_publications_and_all_current_parts(self):
        story1="Хакурэя подошла к старому архиву. Она обещала вернуть найденную карту, когда наступит утро. Герой молча кивнул."
        story2="В другом зале зажглась серебряная лампа. Императрица разглядела неизвестный знак и решила сохранить его в памяти."
        _,_=self.publish(1,story1)
        self.assertEqual(n.read(self.db,14)["chapter"],14)
        _,_=self.publish(2,story2)
        _,_=self.publish(3,"Слуга заметил тайный проход под башней. Он не рассказал никому о странном движении за решёткой и поспешил скрыться за дверью.",False)
        plan=novel.enrich(self.db,saga.plan(self.db,"future"))
        packet=n.prepare(self.db,plan)
        self.assertEqual([x["chapter"] for x in packet["current"]],[14,15])
        self.assertNotIn(16,[x["chapter"] for x in packet["recall"]])
        self.assertLessEqual(len(json.dumps(packet,ensure_ascii=False,separators=(",",":")).encode()),n.CONTEXT_BYTES)
        n.record(self.db,"test",plan)
        self.assertEqual(n.last_run(self.db,False)["scope"],"future")
        self.assertIn("Общая литературная память",c.prompt((None,None,{}),{},saga_plan=plan)[1]["content"])

    def test_scoped_retrieval_and_summary(self):
        self.publish(1,"Хакурэя внимательно изучила древний архив. Рядом возник необыкновенный сапфировый компас, но его происхождение оставалось тайной.")
        plan={"arc":"past","guide":"сапфировый компас"}
        p=n.prepare(self.db,plan)
        for ref in p["recall"]:
            self.assertEqual(self.db.execute("SELECT arc FROM omega_index WHERE number=?",(ref["chapter"],)).fetchone()[0],"past")
        ev.mark_read(self.db,14)
        self.assertIn("Часть 14",n.summary(self.db,14))

    def test_embedding_cache_and_budget(self):
        n.refresh(self.db)
        items=vectors.missing(self.db)
        self.assertTrue(items);self.assertLessEqual(len(items),vectors.BATCH)
        self.assertIsNone(vectors.reserve(self.db,[x["body"] for x in items]))
        vectors.configure(self.db,{"rate":100,"cap":1000})
        cost=vectors.reserve(self.db,[x["body"] for x in items]);self.assertIsNotNone(cost)
        data=[{"index":i,"embedding":[1.0]+[0.0]*(vectors.DIM-1)} for i in range(len(items))]
        vectors.store(self.db,items,{"data":list(reversed(data))})
        self.assertEqual(vectors.status(self.db)["indexed"],len(items))
        self.assertTrue(set((x["chapter"],x["seq"]) for x in items).isdisjoint((x["chapter"],x["seq"]) for x in vectors.missing(self.db)))
        query=vectors.save_query(self.db,"тайна",{"data":[data[0]]})
        self.assertEqual(query,vectors.cached_query(self.db,"тайна"))
        hits=vectors.hybrid(self.db,"тайна",query,public=False)
        self.assertTrue(hits)
        for h in hits:
            source=self.db.execute("SELECT story FROM omega_index WHERE number=?",(h["chapter"],)).fetchone()[0]
            self.assertEqual(h["text"],source[h["start"]:h["end"]])
        with self.assertRaises(ValueError):vectors.parse({"data":[{"index":0,"embedding":[1]}]},1)
        vectors.settle(self.db,cost,{"usage":{"total_tokens":1000}})
        self.assertEqual(vectors.budget(self.db)["used"],1)

    def test_old_proposals_remain_and_require_author_evidence(self):
        ids=[]
        for i in range(5):
            ident=proposals.save(self.db,"plot","Идея "+str(i),json.dumps({"title":"Замысел "+str(i),"description":"Новая линия романа","impact":"Развитие","risks":"Не менять канон"}))
            item=proposals.pending(self.db)
            self.assertTrue(proposals.decide(self.db,ident,item["revision"],True));ids.append(ident)
        self.assertEqual(proposals.directions(self.db)[0]["id"],ids[0])
        story="Хакурэя подошла к старому архиву и увидела запечатанное послание. Она осторожно положила его на серебряный стол."
        self.publish(1,story)
        with self.assertRaises(ValueError):proposals.mark_executed(self.db,ids[0],14,"Цитата, которой в тексте нет.")
        proposals.mark_executed(self.db,ids[0],14,story[:55])
        self.assertEqual(proposals.execution(self.db,ids[0]),14)
        self.assertEqual(proposals.directions(self.db)[0]["id"],ids[1])

    def test_semantic_review_only_adds_author_approved_exact_facts(self):
        import soul_semantic as semantic
        import soul_intelligence as li
        import soul_intellect as intellect
        story="Хакурэя подошла к старому архиву. Хакурэя обещала вернуть найденную карту, когда наступит утро. Герой молча кивнул."
        self.publish(1,story)
        ev.mark_read(self.db,14)
        item=semantic.source(self.db,14,1)
        fact={"kind":"promise","subject":"Хакурэя","object":"","value":"вернуть найденную карту","quote":"Хакурэя обещала вернуть найденную карту, когда наступит утро.","cause":None}
        with self.assertRaises(ValueError):semantic.save(self.db,item,json.dumps({"facts":[{**fact,"quote":"Не существующая в тексте цитата."}]}))
        semantic.save(self.db,item,json.dumps({"facts":[fact]}))
        self.assertFalse(any(f["kind"]=="promise" for k,f in li.rows(self.db) if k==14))
        review=semantic.pending(self.db)
        self.assertFalse(semantic.decide(self.db,14,1,"stale",True))
        self.assertTrue(semantic.decide(self.db,14,1,review["revision"],True))
        self.assertTrue(any(f["kind"]=="promise" and f["value"]==fact["value"] for k,f in li.rows(self.db) if k==14))
        self.assertTrue(any(f["kind"]=="promise" and f["chapter"]==14 for f in intellect.rows(self.db,public=False)))
        self.assertEqual(self.db.execute("SELECT story FROM omega_index WHERE number=14").fetchone()[0],story)

    def test_archive_scale_1000_5000_10000(self):
        import soul_lore
        h=soul_lore.metadata()["sha256"]
        prior=0
        def word(i):
            return "архивмаркер"+"".join(chr(1072+(i//(26**j))%26) for j in range(4))
        for count in (1000,5000,10000):
            drafts=[];arcs=[];archive=[]
            for i in range(prior,count):
                num=i+14;did=i+100
                story="Хакурэя исследовала заброшенный архив. На столе лежала карта с надписью "+word(i)+". Она решила сохранить карту до утра."
                value={"title":"Архив "+str(i),"story":story,"tags":["познание"],"emotions":{"wonder":50,"calm":50,"joy":50},"traits":{"patience":0,"curiosity":0,"warmth":0}}
                raw=c.encode(value);digest=c.checksum(raw)
                drafts.append((did,-did,h,raw,digest,"approved"))
                arcs.append((did,"future",13,None,num))
                archive.append((num,"future",value["title"],story,digest,did))
            self.db.executemany("INSERT INTO chronicle_drafts(id,diary_id,canon_hash,payload,checksum,status) VALUES(?,?,?,?,?,?)",drafts)
            self.db.executemany("INSERT INTO saga_arcs VALUES(?,?,?,?,?)",arcs)
            self.db.executemany("INSERT INTO omega_index VALUES(?,?,?,?,?,?)",archive)
            n.refresh(self.db)
            self.assertEqual(n.status(self.db)["indexed"],count+13)
            self.assertEqual(n.status(self.db)["pending"],0)
            hits=u.search(self.db,word(count-1),3,False,"future")
            self.assertEqual(hits[0]["chapter"],count+13)
            prior=count
        self.assertEqual(n.refresh(self.db),0)
