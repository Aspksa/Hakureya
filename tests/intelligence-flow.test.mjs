import test from "node:test";
import assert from "node:assert/strict";
import {layout} from "../web/memory-layout.mjs";
import {flowPaths,activityEvents,brainLabels} from "../web/activity-flow.mjs";
test("all ten recorded brains have independent routes into one coordinator",()=>{
 const records=[{key:"lit:db",group:4,kind:"lit_database",infinite_group:"lit:db"},...Object.keys(brainLabels).map(k=>({key:"brain:"+k,group:4,kind:"lit_brain",infinite_group:"lit:db"}))];
 const graph=layout({records,edges:[],transport:true});
 assert.equal(new Set(graph.nodes.map(n=>n.x.toFixed(8)+":"+n.y.toFixed(8))).size,graph.nodes.length);
 const events=Object.keys(brainLabels).map((k,i)=>({seq:i+1,stage:"brain:"+k,target:"brain:"+k}));
 assert.equal(activityEvents({events},0).length,10);
 for(const e of events){
  const paths=flowPaths({kind:"chronicle",source:"root",...e},graph);
  assert.equal(paths.length,1);
  assert.equal(paths[0].points.at(-1).key,e.stage==="brain:coordinator"?"root":"brain:coordinator");
 }
});
