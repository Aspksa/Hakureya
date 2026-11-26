import test from "node:test";
import assert from "node:assert/strict";
import {stellarKind,stellarColor,publicationChanges,frameBudget,smoothStep} from "../web/stellar-effects.mjs";

test("semantic colors distinguish actual literary types",()=>{
 assert.equal(stellarKind({key:"root"}),"core");
 assert.equal(stellarKind({kind:"fictional_chapter"}),"chapter");
 assert.equal(stellarKind({kind:"lit_character"}),"character");
 assert.equal(stellarKind({kind:"heart_moment"}),"love");
 assert.equal(stellarKind({kind:"lit_power"}),"magic");
 assert.equal(stellarKind({kind:"lit_world"}),"world");
 assert.equal(stellarKind({kind:"lit_rel_conflict"}),"conflict");
 assert.equal(stellarColor({kind:"memory"},"#123456"),"#123456");
});
test("only real new related publication edges receive animation",()=>{
 const previous={records:[{key:"c:1"},{key:"old"}],edges:[{a:"c:1",b:"old",kind:"lit_fact"}]};
 const next={records:[...previous.records,{key:"c:2"},{key:"new"},{key:"other"},{key:"segment:future:2"}],edges:[...previous.edges,{a:"c:2",b:"new",kind:"lit_appearance"},{a:"c:2",b:"segment:future:2",kind:"story_arc"},{a:"old",b:"other",kind:"lit_fact"},{a:"c:2",b:"old",kind:"category"}]};
 const pub={key:"c:2",volume:2,segment:"segment:future:2"};
 const result=publicationChanges(previous,next,pub);
 assert.deepEqual(result.nodes,["c:2","new","segment:future:2"]);
 assert.equal(result.edges.length,2);
 const hidden=publicationChanges(previous,next,{...pub,details:false});
 assert.ok(!hidden.nodes.includes("new"));
 assert.equal(hidden.edges.length,1);
 assert.deepEqual(publicationChanges(previous,next,{key:"missing"}),{nodes:[],edges:[]});
});
test("animation interpolation and dense-scene budgets are bounded",()=>{
 assert.equal(smoothStep(-1),0);
 assert.equal(smoothStep(.5),.5);
 assert.equal(smoothStep(2),1);
 assert.equal(frameBudget(100,16),1);
 assert.equal(frameBudget(1000,16),.65);
 assert.equal(frameBudget(5000,16),.35);
 assert.equal(frameBudget(100,30),.35);
});
