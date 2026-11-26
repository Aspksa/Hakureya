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

import {detailLevel} from '../web/memory-layout.mjs';
test("nested epoch and book geometry produces distinct stable cells",()=>{
 const records=[];
 for(const sector of ["past","meeting","love","future"]){
  records.push({key:"era:"+sector,group:4,sector,book:0,chapter_slot:0,kind:"epoch"});
  for(let book=1;book<=8;book++){
   records.push({key:"segment:"+sector+":"+book,group:4,sector,book,chapter_slot:-1,kind:"book_segment"});
   for(let i=0;i<12;i++)records.push({key:sector+":"+book+":"+i,group:4,sector,book,chapter_slot:i,kind:"fictional_chapter"});
  }
 }
 const g=layout({records,edges:[]});
 const pos=g.nodes.map(n=>n.x.toFixed(8)+":"+n.y.toFixed(8));
 assert.equal(new Set(pos).size,pos.length);
 const a=g.byKey.get("love:2:0"),b=g.byKey.get("segment:love:2");
 assert.ok(Math.abs(Math.hypot(a.x-b.x,a.y-b.y)-.026)<1e-8);
 assert.equal(detailLevel(1000,1),0);assert.equal(detailLevel(1000,1.5),1);assert.equal(detailLevel(1000,3),2);
});

test("Heart topics and growing moments have separate finite lattice positions",()=>{
 const records=[{key:"heart:root",group:4,heart_topic:"root",heart_slot:-1,kind:"heart_root"},{key:"canon:5",group:4,sector:"meeting",book:1,chapter_slot:4}];
 for(const topic of ["meeting","tenderness","trust","memory","letters","adventure"]){
  records.push({key:"heart:topic:"+topic,group:4,heart_topic:topic,heart_slot:-1,kind:"heart_topic"});
  for(let i=0;i<48;i++)records.push({key:"heart:"+topic+":"+i,group:4,heart_topic:topic,heart_slot:i,kind:"heart_moment"});
 }
 const g=layout({records,edges:[]});
 assert.ok(g.nodes.every(n=>Number.isFinite(n.x)&&Number.isFinite(n.y)));
 const cells=g.nodes.map(n=>n.x.toFixed(8)+":"+n.y.toFixed(8));
 assert.equal(new Set(cells).size,cells.length);
 const a=g.byKey.get("heart:trust:0"),b=g.byKey.get("heart:topic:trust");
 assert.ok(Math.abs(Math.hypot(a.x-b.x,a.y-b.y)-.026)<1e-8);
 assert.deepEqual(g.nodes,layout({records,edges:[]}).nodes);
});

test("Shadow and Heart areas remain separate with all epoch sectors",()=>{
 const records=[{key:"heart:root",group:4,heart_topic:"root",heart_slot:-1},{key:"shadow:root",group:4,shadow_topic:"root",shadow_slot:-1}];
 for(const topic of ["court","visits","suitors","threat","mask","power"]){
  records.push({key:"shadow:topic:"+topic,group:4,shadow_topic:topic,shadow_slot:-1});
  for(let i=0;i<18;i++)records.push({key:"shadow:"+topic+":"+i,group:4,shadow_topic:topic,shadow_slot:i});
 }
 for(const topic of ["meeting","tenderness","trust","memory","letters","adventure"]){
  records.push({key:"heart:topic:"+topic,group:4,heart_topic:topic,heart_slot:-1});
  for(let i=0;i<30;i++)records.push({key:"heart:"+topic+":"+i,group:4,heart_topic:topic,heart_slot:i});
 }
 for(const sector of ["past","meeting","love","future"])records.push({key:"era:"+sector,group:4,sector,book:0,chapter_slot:0});
 const g=layout({records,edges:[]});
 assert.ok(g.nodes.every(n=>Number.isFinite(n.x)&&Number.isFinite(n.y)));
 assert.equal(new Set(g.nodes.map(n=>n.x.toFixed(8)+":"+n.y.toFixed(8))).size,g.nodes.length);
});

test("nine guardians and their memories have unique stable positions",()=>{
 const actors=["reika","seirana","mikage","tokihana","akatsuki","shiori","yumeka","meirin","amatsuka"];
 const records=[{key:"guardians:root",group:4,guardian_actor:"root",guardian_slot:-1},{key:"heart:root",group:4,heart_topic:"root",heart_slot:-1},{key:"shadow:root",group:4,shadow_topic:"root",shadow_slot:-1}];
 for(const a of actors){
  records.push({key:"guardian:"+a,group:4,guardian_actor:a,guardian_slot:-1});
  for(let i=0;i<90;i++)records.push({key:"memory:"+a+":"+i,group:4,guardian_actor:a,guardian_slot:i});
 }
 const g=layout({records,edges:[]});
 assert.ok(g.nodes.every(n=>Number.isFinite(n.x)&&Number.isFinite(n.y)));
 assert.equal(new Set(g.nodes.map(n=>n.x.toFixed(8)+":"+n.y.toFixed(8))).size,g.nodes.length);
 const a=g.byKey.get("guardian:reika"),b=g.byKey.get("memory:reika:0");
 assert.ok(Math.abs(Math.hypot(a.x-b.x,a.y-b.y)-.026)<1e-8);
 assert.deepEqual(g.nodes,layout({records,edges:[]}).nodes);
});

test("Destiny topic and personal clusters do not overlap",()=>{
 const topics=["love","power","guardians","court","worlds","cast","growth","actor:iori","actor:lian"];
 const records=[{key:"destiny:root",group:4,destiny_topic:"root",destiny_slot:-1}];
 for(const topic of topics){
  records.push({key:"hub:"+topic,group:4,destiny_topic:topic,destiny_slot:-1});
  for(let i=0;i<40;i++)records.push({key:topic+":"+i,group:4,destiny_topic:topic,destiny_slot:i});
 }
 const g=layout({records,edges:[]});
 assert.ok(g.nodes.every(n=>Number.isFinite(n.x)&&Number.isFinite(n.y)));
 assert.equal(new Set(g.nodes.map(n=>n.x.toFixed(8)+":"+n.y.toFixed(8))).size,g.nodes.length);
 assert.deepEqual(g.nodes,layout({records,edges:[]}).nodes);
});

test("Immortal Chronicle uses separated stable cells",()=>{
 const records=[{key:"immortal:root",group:4,immortal_slot:-1},{key:"destiny:root",group:4,destiny_topic:"root",destiny_slot:-1},{key:"heart:root",group:4,heart_topic:"root",heart_slot:-1}];
 for(let i=0;i<500;i++)records.push({key:"immortal:"+i,group:4,immortal_slot:i});
 const g=layout({records,edges:[]});
 assert.ok(g.nodes.every(n=>Number.isFinite(n.x)&&Number.isFinite(n.y)));
 assert.equal(new Set(g.nodes.map(n=>n.x.toFixed(8)+":"+n.y.toFixed(8))).size,g.nodes.length);
 assert.deepEqual(g.nodes,layout({records,edges:[]}).nodes);
});

import {packCircles,cameraFrame} from '../web/memory-layout.mjs';
test("compact envelopes do not overlap or expand into a radial staircase",()=>{
 const disks=[.24,.3,.16,.4,.55,.68,.16,.32,.14].map((r,i)=>({key:i,r}));
 const p=[{key:"core",x:0,y:0,r:.1},...packCircles(disks,.1,.035).values()];
 for(let i=0;i<p.length;i++)for(let j=0;j<i;j++)assert.ok(Math.hypot(p[i].x-p[j].x,p[i].y-p[j].y)>=p[i].r+p[j].r+.035-1e-7);
 const packedRadius=Math.max(...p.map(x=>Math.hypot(x.x,x.y)+x.r));
 const staircase=.1+disks.reduce((a,x)=>a+2*x.r+.1,0);
 assert.ok(packedRadius<staircase*.65);
 assert.deepEqual([...packCircles(disks,.1,.035)],[...packCircles(disks,.1,.035)]);
});
test("overview fits all star centers in desktop and narrow chat viewports",()=>{
 const records=Array.from({length:1000},(_,i)=>({key:"m:"+i,group:i%5,slot:Math.floor(i/5)}));
 records.push({key:"immortal:root",group:4,immortal_slot:-1},{key:"heart:root",group:4,heart_topic:"root",heart_slot:-1});
 for(let i=0;i<120;i++)records.push({key:"immortal:"+i,group:4,immortal_slot:i});
 const g=layout({records,edges:[]});
 assert.equal(g.byKey.get("root").r,9);
 for(const [w,h] of [[1920,1080],[1366,768],[1280,720],[760,768],[450,720],[390,844]]){
  const c=cameraFrame(g.bounds,w,h);
  assert.ok(c.scale>0);
  for(const n of g.nodes){
   const x=w/2+(n.x-c.cx)*c.scale,y=h/2+(n.y-c.cy)*c.scale;
   assert.ok(x>=c.pad-1e-6&&x<=w-c.pad+1e-6);
   assert.ok(y>=c.pad-1e-6&&y<=h-c.pad+1e-6);
  }
 }
});
