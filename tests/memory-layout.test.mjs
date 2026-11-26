import test from 'node:test';import assert from 'node:assert/strict';import {layout} from '../web/memory-layout.mjs';
test("empty memory is only root",()=>{let g=layout({records:[],edges:[]});assert.equal(g.nodes.length,1);assert.equal(g.edges.length,0)});
test("real stable keys and valid relationships",()=>{const records=[{key:"m:1",group:0,label:"a"},{key:"n:1",group:1,label:"b"},{key:"m:2",group:2,label:"c"}],edges=[{a:"m:1",b:"m:2",kind:"chronology"},{a:"missing",b:"m:2",kind:"keywords"}];let g=layout({records,edges});assert.deepEqual(g.nodes.filter(n=>n.key.includes(":")&&!n.key.startsWith("hub")).map(n=>n.key),records.map(n=>n.key));assert.ok(g.edges.every(e=>g.byKey.has(e.a)&&g.byKey.has(e.b)));assert.deepEqual(g.nodes,layout({records,edges}).nodes)});
test("5000 records produce finite positions",()=>{const records=Array.from({length:5000},(_,i)=>({key:"m:"+i,group:i%4,label:"test"}));const g=layout({records,edges:[]});assert.equal(g.nodes.length,5005);assert.ok(g.nodes.every(n=>Number.isFinite(n.x)&&Number.isFinite(n.y)))});

import {cell,categories} from '../web/memory-layout.mjs';
import {flowPaths,pointOn} from '../web/activity-flow.mjs';
test("biography is an independent fifth constellation and no Cloud node exists",()=>{
 const records=Array.from({length:150},(_,i)=>({key:"x:"+i,group:i%5,slot:Math.floor(i/5)}));
 const g=layout({records,edges:[]});
 assert.equal(categories[4],"Биография");
 assert.ok(g.byKey.has("hub:4"));
 assert.ok(!g.byKey.has("cloud"));
 for(let i=0;i<5;i++)for(let j=i+1;j<5;j++){
  const a=g.byKey.get("hub:"+i),b=g.byKey.get("hub:"+j);
  assert.ok(Math.hypot(a.x-b.x,a.y-b.y)>=g.radius[i]+g.radius[j]);
 }
});
test("5000 lattice slots unique and finite",()=>{
 const cells=new Set();
 for(let i=0;i<5000;i++){const p=cell(i);assert.ok(Number.isFinite(p.x)&&Number.isFinite(p.y));cells.add(p.x.toFixed(9)+":"+p.y.toFixed(9))}
 assert.equal(cells.size,5000);
});
test("stored star keeps relative position on insertion and eviction",()=>{
 const record={key:"old",group:4,slot:20};
 const a=layout({records:[record],edges:[]});
 const b=layout({records:[{key:"other",group:4,slot:200},record],edges:[]});
 for(const axis of ["x","y"])assert.ok(Math.abs((a.byKey.get("old")[axis]-a.byKey.get("hub:4")[axis])-(b.byKey.get("old")[axis]-b.byKey.get("hub:4")[axis]))<1e-9);
});
test("actual stages yield distinct transport paths, no synthetic activity",()=>{
 const graph=layout({records:[{key:"d:1",group:3,slot:0},{key:"draft:1",group:4,slot:1}],edges:[]});
 const req={kind:"chronicle",source:"d:1",target:"draft:1",stage:"waiting"};
 const outbound=flowPaths(req,graph)[0];assert.equal(outbound.points[0].key,"d:1");
 const done=flowPaths({...req,stage:"done"},graph)[0];assert.equal(done.points.at(-1).key,"draft:1");
 assert.deepEqual(pointOn(done.points,1),{x:done.points.at(-1).x,y:done.points.at(-1).y});
 assert.equal(flowPaths({...req,stage:"error"},graph)[0].color,"#ed657d");
 assert.deepEqual(flowPaths({...req,stage:"idle"},graph),[]);
});
