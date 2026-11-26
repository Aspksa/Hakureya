import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {transformWithEsbuild} from 'vite';

class ElementStub {
 constructor(tag="div"){this.tagName=tag;this.children=[];this.attrs=new Map();this.hidden=false;this.clientWidth=900;this.clientHeight=650;this.textContent="";this.value="";this.style={setProperty(){}};this.classList={add(){},remove(){},toggle(){}}}
 append(...nodes){this.children.push(...nodes)}
 replaceChildren(...nodes){this.children=nodes}
 setAttribute(k,v){this.attrs.set(k,String(v))}
 getAttribute(k){return this.attrs.get(k)??null}
 removeAttribute(k){this.attrs.delete(k)}
 addEventListener(){}
 removeEventListener(){}
 focus(){}
 scrollIntoView(){}
 showModal(){this.open=true}
 close(){this.open=false;this.onclose?.()}
 getBBox(){return {x:0,y:0,width:20,height:10}}
 animate(){}
 remove(){}
}
const src=async name=>readFile(new URL("../web/"+name,import.meta.url),"utf8");
function moduleURL(code){return "data:text/javascript;base64,"+Buffer.from(code).toString("base64")}
const graphSource=(await src("live-graph.ts")).replace(/from "(\.\/[^"]+\.mjs)"/g,(_,p)=>'from "'+new URL("../web/"+p.slice(2),import.meta.url).href+'"');
const graphURL=moduleURL((await transformWithEsbuild(graphSource,"live-graph.ts",{loader:"ts",format:"esm"})).code);
const appSource=(await src("app.ts")).replace('import "./style.css";',"").replace('from "./live-graph"','from "'+graphURL+'"').replace('from "./reader-pagination.mjs"','from "'+new URL("../web/reader-pagination.mjs",import.meta.url).href+'"');
const appURL=moduleURL((await transformWithEsbuild(appSource,"app.ts",{loader:"ts",format:"esm"})).code);

function browser(failGraph=false){
 const elements=new Map();
 const get=id=>{if(!elements.has(id))elements.set(id,new ElementStub(id));return elements.get(id)};
 get("chat").hidden=true;get("book").hidden=true;
 const snapshot={records:[{key:"m:1",group:0,label:"ordinary memory"},{key:"n:1",group:1,kind:null,label:"note"},{key:"canon:1",group:4,kind:"fictional_chapter",label:"canon"}],edges:[{a:"m:1",b:"n:1",kind:"keywords"}],total:3,limited:false};
 Object.assign(globalThis,{
  document:{hidden:false,getElementById:get,createElement:tag=>new ElementStub(tag),createElementNS:(_,tag)=>{if(failGraph)throw Error("simulated SVG failure");return new ElementStub(tag)},addEventListener(){},removeEventListener(){}},
  window:{setTimeout:()=>0,matchMedia:()=>({matches:true}),addEventListener(){},removeEventListener(){}},
  matchMedia:()=>({matches:true}),ResizeObserver:class{observe(){}disconnect(){}},
  requestAnimationFrame:()=>1,cancelAnimationFrame(){},
  fetch:async path=>({ok:true,json:async()=>path==="/api/graph"?snapshot:path==="/api/history"?{messages:[],connected:false}:path==="/api/reader"?{reader:null}:{session:"test",revision:1,active:[],recent:[]}})
 });
 return {get,snapshot};
}
test("renderer mounts empty root, then normal memories without a kind",async()=>{
 const {get,snapshot}=browser();
 const {mountGraph}=await import(graphURL);
 const svg=get("graph");
 const live=mountGraph(svg,get("info"));
 assert.ok(svg.children.length>0);
 assert.doesNotThrow(()=>live.render(snapshot));
 assert.match(get("info").textContent,/3 записей/);
 live.dispose();
});
test("Cloud.ru dialog loads models without consent and uses the selected ID on connect",async()=>{
 const {get}=browser();
 const oldFetch=globalThis.fetch,oldInterval=globalThis.setInterval;
 const configCalls=[];
 try{
  globalThis.setInterval=()=>0;
  globalThis.fetch=async (path,options)=>{
   if(!path.startsWith("/api/config"))return oldFetch(path,options);
   configCalls.push([path,JSON.parse(options.body)]);
   if(path.endsWith("/models"))return {ok:true,json:async()=>({models:["vendor/Model-A","vendor/Model-B"]})};
   return {ok:true,json:async()=>({connected:true})};
  };
  await import(appURL+"#cloud-config");
  await new Promise(resolve=>setImmediate(resolve));
  get("settings").onclick();
  get("key").value="test-key";
  get("consent").checked=false;
  await get("load-models").onclick();
  assert.deepEqual(configCalls,[["/api/config/models",{key:"test-key"}]]);
  assert.equal(get("model-list-label").hidden,false);
  assert.deepEqual(get("model-list").children.map(option=>option.value),["","vendor/Model-A","vendor/Model-B"]);
  get("model-list").value="vendor/Model-B";
  get("model-list").onchange();
  assert.equal(get("model").value,"vendor/Model-B");
  get("consent").checked=true;
  await get("config-form").onsubmit({preventDefault(){}});
  assert.deepEqual(configCalls[1],["/api/config",{model:"vendor/Model-B",key:"test-key",consent:true}]);
  assert.equal(get("config").open,false);
  assert.equal(get("key").value,"");
 }finally{globalThis.fetch=oldFetch;globalThis.setInterval=oldInterval}
});
test("actual app initializes and opens chat even if optional SVG initialization fails",async()=>{
 const oldInterval=globalThis.setInterval,oldError=console.error;
 try{
  globalThis.setInterval=()=>0;
  for(const fail of [false,true]){
   const {get}=browser(fail);
   const errors=[];console.error=(...args)=>errors.push(args);
   await import(appURL+"#"+String(fail));
   await new Promise(resolve=>setImmediate(resolve));
   assert.equal(typeof get("avatar").onclick,"function");
   get("avatar").onclick();
   assert.equal(get("chat").hidden,false);
   get("close").onclick();
   assert.equal(get("chat").hidden,true);
   if(fail){assert.match(get("info").textContent,/Ошибка визуализации/);assert.ok(errors.length>0)}
   else{assert.equal(errors.length,0);assert.ok(get("graph").children.length>0)}
  }
 }finally{globalThis.setInterval=oldInterval;console.error=oldError}
});
