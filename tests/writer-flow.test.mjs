import test from "node:test";
import assert from "node:assert/strict";
import {layout} from "../web/memory-layout.mjs";
import {flowPaths,activityEvents,publicationLinks,sourceColor} from "../web/activity-flow.mjs";

const records=[
 {key:"arc:future",group:4,kind:"theme"},{key:"guardian:reika",group:4,guardian_actor:"reika",guardian_slot:-1},
 {key:"character:hero",group:4,kind:"character"},{key:"heart:root",group:4,heart_topic:"root",heart_slot:-1},
 {key:"canon:5",group:4,kind:"fictional_chapter",sector:"meeting",book:1,chapter_slot:4},
 {key:"book:1",group:4,kind:"book"},{key:"book:2",group:4,kind:"book"},
 {key:"c:42",group:4,kind:"fictional_chapter",sector:"future",book:2,chapter_slot:0},
 {key:"segment:future:2",group:4,kind:"book_segment",sector:"future",book:2,chapter_slot:-1},
 {key:"draft:43",group:4,kind:"draft"},
];
const graph=layout({records,edges:[{a:"canon:5",b:"c:42",kind:"infinite_cross_volume"},{a:"character:hero",b:"c:42",kind:"character"}],transport:true});
test("Cloud occupies its own reserved envelope and context sources fly independently",()=>{
 const cloud=graph.byKey.get("cloud:api"),root=graph.byKey.get("root");
 assert.ok(cloud&&cloud.x!==root.x||cloud.y!==root.y);
 assert.ok(Math.hypot(cloud.x-root.x,cloud.y-root.y)>=.22);
 const item={kind:"chronicle",source:"arc:future",sources:["guardian:reika","character:hero","heart:root","canon:5","not-present"],target:"draft:43",stage:"context"};
 const paths=flowPaths(item,graph);
 assert.equal(paths.length,5);
 assert.ok(paths.every(p=>p.points.at(-1).key==="root"));
 assert.ok(paths.some(p=>p.color===sourceColor("guardian:reika")));
 assert.ok(paths.some(p=>p.color===sourceColor("heart:root")));
 assert.deepEqual(flowPaths({...item,stage:"waiting"},graph)[0].points.map(p=>p.key),["root","cloud:api"]);
 assert.deepEqual(flowPaths({...item,stage:"received"},graph)[0].points.map(p=>p.key),["cloud:api","root"]);
 assert.equal(flowPaths({...item,stage:"saved"},graph)[0].points.at(-1).key,"draft:43");
});
test("stage history is filtered by sequence, never invented",()=>{
 const item={id:"one",kind:"chronicle",source:"root",target:"draft:43",stage:"saved",events:[
  {seq:1,stage:"context",target:"root"},{seq:2,stage:"waiting",target:"root"},{seq:3,stage:"received",target:"hub:4"},
  {seq:4,stage:"validating",target:"hub:4"},{seq:5,stage:"saving",target:"hub:4"},{seq:6,stage:"saved",target:"draft:43"}
 ]};
 assert.deepEqual(activityEvents(item,2).map(e=>e.stage),["received","validating","saving","saved"]);
 assert.deepEqual(activityEvents(item,6),[]);
});
test("only actual publication creates volume and character trails; unread hides details",()=>{
 const pub={key:"c:42",volume:2,segment:"segment:future:2",first:true,details:true};
 const links=publicationLinks(pub,graph);
 assert.ok(links.some(l=>l.a==="book:1"&&l.b==="book:2"));
 assert.ok(links.some(l=>l.a==="c:42"&&l.b==="character:hero"));
 assert.ok(links.some(l=>l.a==="canon:5"&&l.b==="c:42"));
 assert.ok(publicationLinks({...pub,details:false},graph).every(l=>l.b!=="character:hero"&&l.a!=="canon:5"));
 assert.deepEqual(publicationLinks({...pub,key:"missing"},graph),[]);
});
