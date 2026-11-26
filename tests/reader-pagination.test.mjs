import test from "node:test";
import assert from "node:assert/strict";
import {measuredPages,pageAt} from "../web/reader-pagination.mjs";
const text=("Хакурэя улыбнулась. Девять небес освещены луной. 🦊\n\n— Продолжим путь.\n\n").repeat(120);
test("measured pages preserve source and adapt to screen",()=>{
 const small=measuredPages(text,t=>Array.from(t).length<=270);
 const large=measuredPages(text,t=>Array.from(t).length<=650);
 assert.ok(small.length>large.length);
 for(const pages of [small,large]){
  assert.equal(pages.map(p=>p.text).join(""),text);
  assert.ok(pages.every(p=>p.end>p.start));
  assert.ok(pages.every(p=>p.end-p.start<=650));
 }
});
test("resize anchors the exact saved character including astral code points",()=>{
 const anchor=397;
 const p=measuredPages(text,(t,start)=>Array.from(t).length<=(start===0?190:540),anchor);
 assert.equal(p[pageAt(p,anchor)].start,anchor);
 assert.equal(p.map(x=>x.text).join(""),text);
 assert.equal(pageAt(p,Array.from(text).length),p.length-1);
});
