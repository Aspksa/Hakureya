import {layout,palette,detailLevel,cameraFrame} from "./memory-layout.mjs";
import {flowPaths,pointOn,activityEvents,stageLabels,publicationLinks} from "./activity-flow.mjs";
import {rng,clamp} from "./geometry.mjs";
type Publication={number:number,key:string,volume:number,segment:string,first:boolean,complete:boolean,epoch:number,details?:boolean};
type Snapshot={records:any[],edges:any[],total:number,limited:boolean,volume?:number,publication?:Publication|null};
type Work={id:string,kind:string,source:string,target:string,stage:string,sources?:string[],events?:{seq:number,stage:string,target:string}[],seq?:number};
type Activity={session:string,revision:number,active:Work[],recent:Work[]};
export function mountGraph(svg:SVGSVGElement,info:HTMLElement,onVolume?:(volume:number)=>void){
 const ns="http://www.w3.org/2000/svg";
 function el<K extends keyof SVGElementTagNameMap>(tag:K,attrs:Record<string,string|number>={},parent:SVGElement=svg){const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,String(v));parent.append(e);return e}
 const defs=el("defs"),colors=["#fffdf4",...palette];
 colors.forEach((c,i)=>{const g=el("radialGradient",{id:"glow"+i},defs);for(const [offset,opacity] of [[0,.92],[.11,.65],[.25,.26],[.5,.08],[1,0]])el("stop",{offset,"stop-color":c,"stop-opacity":opacity},g)});
 const cloudGlow=el("radialGradient",{id:"cloud-glow"},defs);for(const [offset,opacity] of [[0,.8],[.2,.35],[1,0]])el("stop",{offset,"stop-color":"#91cbff","stop-opacity":opacity},cloudGlow);
 const stars=el("g",{"pointer-events":"none"}),world=el("g"),links=el("g",{"pointer-events":"none"},world),orbits=el("g",{"pointer-events":"none"},world),dots=el("g",{},world),flows=el("g",{"pointer-events":"none"},world),overlay=el("g",{"pointer-events":"none"},world);
 const random=rng(920),starData=Array.from({length:2200},()=>({x:random(),y:random(),r:.12+random()**7*.72,o:.035+random()**2*.34}));
 const starEls=starData.map((p,i)=>el("circle",{r:p.r,fill:i%13===0?"#d8b9a1":"#e1dcd8",opacity:p.o},stars));
 let snapshot:Snapshot={records:[],edges:[],total:0,limited:false},graph=layout({...snapshot,transport:true}),w=1,h=1,s=1,zoom=1,panX=0,panY=0,fit=1,desired=1,active="",drag:null|{x:number,y:number,moved:boolean}=null,items=new Map<string,SVGGElement>(),edgeEls:SVGLineElement[]=[],drawnEdges:any[]=[],replayAt=0,shown=0,last=performance.now(),raf=0,disposed=false;
 let session="",works=new Map<string,{item:Work,started:number,terminal:boolean}>(),seen=new Set<string>();
 let receivedSnapshot=false,maxChapter=0,level=-1,lastPublication=0,manualUntil=0,readerOpen=false,paused=false;
 const birthTrails=new Map<string,{a:string,b:string,color:string,at:number}>();
 const waves=new Map<string,{at:number,color:string,rings:SVGCircleElement[]}>();
 const stages=new Map<string,{seq:number,queue:Work[],started:number,current:Work,terminal:boolean}>();
 const highlighted=new Map<string,SVGCircleElement>();
 const orbitEls=new Map<string,{circle:SVGCircleElement,node:any,r:number}>();
 let lastLabelFrame=0;
 let recentChapterKeys=new Set<string>();
 const births=new Map<string,number>();
 const glyphs=new Map<string,SVGGElement>(),labels=new Map<string,SVGTextElement>(),labelWidths=new Map<string,number>();
 let camera=cameraFrame(graph.bounds,w,h),glyphScale=NaN,selectionGlyph:SVGGElement|null=null;
 let focusMotion:null|{start:number,fromZoom:number,toZoom:number,fromX:number,fromY:number,toX:number,toY:number}=null;
 const motion=matchMedia("(prefers-reduced-motion: reduce)");
 const particles=new Map<string,{group:SVGGElement,line:SVGPolylineElement,dots:SVGCircleElement[]}>();
 const stageNames=stageLabels as Record<string,string>;
 function pulse(key:string,color:string,now=performance.now()){if(motion.matches||!graph.byKey.has(key))return;const old=waves.get(key);if(old)for(const ring of old.rings)ring.remove();if(waves.size>=12&&!old)return;const rings=Array.from({length:2},()=>el("circle",{fill:"none",stroke:color,"stroke-width":1.4,"vector-effect":"non-scaling-stroke"},flows));waves.set(key,{at:now,color,rings});invalidate()}
 function baseFit(){camera=cameraFrame(graph.bounds,w,h);return camera.scale/s}
 function origin(){const k=zoom*fit;return {x:w/2-camera.cx*s*k+panX,y:h/2-camera.cy*s*k+panY,k}}
 function updateGlyphs(){
  const {x,y,k}=origin(),inverse=1/Math.max(.00001,k);
  // Draw glyphs at screen size, instead of shrinking every star together with the world.
  if(glyphScale!==inverse){
   glyphScale=inverse;
   for(const [key,g] of glyphs){const n=graph.byKey.get(key);const density=graph.nodes.length>800&&zoom<1.25&&!labels.has(key)&&n?.kind!=="fictional_chapter"?.72:1;g.setAttribute("transform","scale("+(inverse*density)+")")}
   selectionGlyph?.setAttribute("transform","scale("+inverse+")");
  }
  const boxes:{l:number,r:number,t:number,b:number}[]=[];
  const priority=(key:string)=>key==="root"?0:key===active||key==="cloud:api"?1:key.startsWith("hub:")?2:graph.byKey.get(key)?.kind?.endsWith("_root")?3:4;
  for(const [key,t] of [...labels].sort((a,b)=>priority(a[0])-priority(b[0])||a[0].localeCompare(b[0]))){
   const n=graph.byKey.get(key),px=x+n.x*s*k,py=y+n.y*s*k;
   let width=labelWidths.get(key);if(width===undefined){width=Math.max(48,t.getComputedTextLength?.()||((n.label?.length||0)*7.5));labelWidths.set(key,width)}
   const baseline=key==="root"?37:24,box={l:px-width/2-5,r:px+width/2+5,t:py+baseline-16,b:py+baseline+5};
   const visible=items.get(key)?.getAttribute("visibility")!=="hidden"&&box.l>=2&&box.r<=w-2&&box.t>=2&&box.b<=h-2&&!(key===active&&key!=="root")&&!boxes.some(q=>box.l<q.r&&box.r>q.l&&box.t<q.b&&box.b>q.t);
   t.setAttribute("visibility",visible?"visible":"hidden");
   if(visible)boxes.push(box);
  }
 }
 function focusNode(key:string){
  const n=graph.byKey.get(key);if(!n)return;
  const target=key==="root"?1:Math.min(5,Math.max(2.3,zoom));
  const k=target*desired;
  focusMotion={start:performance.now(),fromZoom:zoom,toZoom:target,fromX:panX,fromY:panY,toX:key==="root"?0:-(n.x-camera.cx)*s*k,toY:key==="root"?0:-(n.y-camera.cy)*s*k};
  invalidate();
 }
 function status(){const count=[...works.values()].filter(a=>!a.terminal).length;info.textContent=(snapshot.volume?"Том "+snapshot.volume+" · ":"")+snapshot.total+" записей · "+graph.edges.length+" связей"+(snapshot.limited?" · ограничено 5000":"")+(snapshot.volume?" · ↻ общая карта":"")+(count?" · "+([...stages.values()].find(a=>!a.terminal)?.current&&stageNames[[...stages.values()].find(a=>!a.terminal)!.current.stage]||"Cloud.ru: "+count):[...stages.values()].some(a=>a.terminal)?" · "+(stageNames[[...stages.values()].at(-1)?.current.stage||""]||""):"")}
 function redrawSelection(){
  overlay.replaceChildren();selectionGlyph=null;const n=graph.byKey.get(active);if(!n)return;
  const outer=el("g",{transform:"translate("+n.x*s+" "+n.y*s+")"},overlay),color=colors[n.group+1];
  const g=el("g",{transform:"scale("+(1/Math.max(.00001,zoom*fit))+")"},outer);selectionGlyph=g;
  el("circle",{r:Math.max(10,n.r*2.0),fill:"none",stroke:color,"stroke-width":.9},g);
  if(n.label){const title=String(n.label).slice(0,54);const label=el("text",{x:Math.max(16,n.r*2+5),y:-12,fill:color,class:"active-label"},g);label.textContent=title;const b=label.getBBox();const rect=el("rect",{x:b.x-4,y:b.y-2,width:b.width+8,height:b.height+4,rx:2,fill:"#110b0e",stroke:color,"stroke-opacity":.72,"stroke-width":.65},g);g.insertBefore(rect,label)}
 }
 function place(){
  for(const n of graph.nodes)items.get(n.key)?.setAttribute("transform","translate("+n.x*s+" "+n.y*s+")");
  drawnEdges.forEach((e,i)=>{const a=graph.byKey.get(e.a),b=graph.byKey.get(e.b),line=edgeEls[i];if(!line||!a||!b)return;for(const [k,v] of Object.entries({x1:a.x*s,y1:a.y*s,x2:b.x*s,y2:b.y*s}))line.setAttribute(k,String(v))});
  for(const {circle,node,r} of orbitEls.values()){circle.setAttribute("cx",String(node.x*s));circle.setAttribute("cy",String(node.y*s));circle.setAttribute("r",String(r*s))}
  redrawSelection();
 }
 function invalidate(){if(!raf&&!disposed&&!document.hidden&&!paused)raf=requestAnimationFrame(frame)}
 function resize(){const nw=Math.max(1,svg.clientWidth),nh=Math.max(1,svg.clientHeight);if(nw===w&&nh===h)return;focusMotion=null;panX=panY=0;zoom=1;active="";level=-1;w=nw;h=nh;s=Math.max(1,Math.min(w,h));desired=baseFit();fit=desired;svg.setAttribute("viewBox","0 0 "+w+" "+h);starEls.forEach((e,i)=>{e.setAttribute("cx",String(starData[i].x*w));e.setAttribute("cy",String(starData[i].y*h))});place();glyphScale=NaN;invalidate()}
 function reveal(n:number){
  const visible=new Set(graph.nodes.slice(0,n).map(x=>x.key));graph.nodes.forEach(x=>items.get(x.key)?.setAttribute("visibility",visible.has(x.key)?"visible":"hidden"));drawnEdges.forEach((e,i)=>edgeEls[i]?.setAttribute("visibility",visible.has(e.a)&&visible.has(e.b)?"visible":"hidden"));shown=n;
 }
 function applyDetail(){
  const next=detailLevel(graph.nodes.length,zoom);
  if(level===next||replayAt)return;
  level=next;
  const visible=new Set<string>();
  for(const n of graph.nodes){const major=n.key==="root"||n.key==="cloud:api"||n.key.startsWith("hub:")||n.key.startsWith("canon:")||n.kind==="epoch"||n.kind==="book"||n.kind==="book_segment"||n.kind==="draft"||n.kind==="heart_root"||n.kind==="heart_topic"||n.kind==="shadow_root"||n.kind==="shadow_topic"||n.kind==="guardian_root"||n.kind==="guardian_character"||n.kind==="destiny_root"||n.kind==="destiny_topic"||n.kind==="destiny_character"||n.kind==="living_root"||n.kind==="living_topic"||n.kind==="evolution_root"||n.kind==="evolution_subject"||n.kind==="immortal_root"||n.kind==="immortal_saga"||n.kind==="novel_epoch"||n.kind==="novel_chapter"||n.kind==="infinite_root"||n.kind==="infinite_character"||n.kind==="infinite_stage"||n.key==="character:hero"||n.kind==="realm"||n.key===active||recentChapterKeys.has(n.key);
   const show=next===2||n.group!==4||major||(next===1&&n.kind==="fictional_chapter");
   if(show)visible.add(n.key);items.get(n.key)?.setAttribute("visibility",show?"visible":"hidden");}
  drawnEdges.forEach((e,i)=>edgeEls[i]?.setAttribute("visibility",visible.has(e.a)&&visible.has(e.b)&&(next===2||e.kind!=="keywords")?"visible":"hidden"));
 }
 function render(next:Snapshot,initial=false){
  if(!initial&&JSON.stringify(next)===JSON.stringify(snapshot))return;
  const now=performance.now();
  const oldKeys=new Set(snapshot.records.map(n=>n.key));
  const scopeChanged=snapshot.volume!==next.volume,firstSnapshot=!receivedSnapshot&&!initial;
  if(scopeChanged){zoom=1;panX=0;panY=0;active="";births.clear();replayAt=0;focusMotion=null;}
  for(const n of next.records){if(/^c:[1-9]\d*$/.test(n.key)){const id=Number(n.key.slice(2));if(receivedSnapshot&&!scopeChanged&&!next.volume&&id>maxChapter&&!motion.matches)births.set(n.key,now);}}
  for(const n of next.records){if(/^c:[1-9]\d*$/.test(n.key))maxChapter=Math.max(maxChapter,Number(n.key.slice(2)));}
  if(!initial)receivedSnapshot=true;
  const publication=next.publication,wasReceived=receivedSnapshot&&!firstSnapshot;
  const isNewPublication=!!(publication&&wasReceived&&!scopeChanged&&!next.volume&&publication.number>lastPublication);
  if(publication)lastPublication=Math.max(lastPublication,publication.number);
  snapshot=next;graph=layout({...next,transport:true});level=-1;
  recentChapterKeys=new Set<string>(next.records.filter(n=>/^c:[1-9]\d*$/.test(n.key)).sort((a,b)=>Number(b.key.slice(2))-Number(a.key.slice(2))).slice(0,20).map(n=>n.key));items.clear();glyphs.clear();labels.clear();labelWidths.clear();glyphScale=NaN;links.replaceChildren();dots.replaceChildren();orbits.replaceChildren();orbitEls.clear();overlay.replaceChildren();
  for(const n of graph.nodes){if(n.kind!=="book_segment"||!n.book)continue;const members=graph.nodes.filter(c=>c.kind==="fictional_chapter"&&c.book===n.book&&c.sector===n.sector);if(!members.length)continue;const r=Math.max(.03,...members.map(c=>Math.hypot(c.x-n.x,c.y-n.y)))+.012;const circle=el("circle",{fill:"none",stroke:"#e8ca96","stroke-opacity":.19,"stroke-dasharray":"2 5","stroke-width":.7,"vector-effect":"non-scaling-stroke"},orbits);orbitEls.set(n.key,{circle,node:n,r})}
  // Always preserve root, categories and canon links; thin dense secondary edges only.
  const essential=graph.edges.filter(e=>e.kind==="category"||e.kind==="chronology"||e.a.startsWith("canon:")||e.kind==="draft"||e.kind.startsWith("heart_")||e.kind.startsWith("shadow_")||e.kind.startsWith("guardian_")||e.kind.startsWith("destiny_")||e.kind.startsWith("living_")||e.kind.startsWith("evolution_")||e.kind.startsWith("immortal_")||e.kind.startsWith("infinite_"));
  const essentialSet=new Set(essential);const secondary=graph.edges.filter(e=>!essentialSet.has(e));
  drawnEdges=essential.concat(secondary.slice(0,Math.max(0,10000-essential.length)));
  edgeEls=drawnEdges.map(e=>{const b=graph.byKey.get(e.b);return el("line",{stroke:e.kind==="infinite_hero"?"#e7c46d":e.kind==="infinite_love"?"#f0a3c5":e.kind==="infinite_cross_volume"?"#9ec8f0":e.kind.startsWith("infinite_")?"#c7b3df":e.kind==="immortal_consequence"?"#d9bd80":e.kind==="immortal_love"?"#efa3c4":e.kind==="immortal_clue"||e.kind==="immortal_reveal"?"#c0a9e8":e.kind==="immortal_journey"?"#9fc9ec":e.kind.startsWith("immortal_")?"#d0c0a5":e.kind.startsWith("evolution_")?"#c5b7ed":e.kind.startsWith("living_")?"#b1d9ca":e.kind.startsWith("destiny_")?"#b8c9e8":e.kind.startsWith("guardian_")?"#e4d8ac":e.kind.startsWith("shadow_")?"#d9c799":e.kind.startsWith("heart_")?"#efa3c4":e.kind==="category"&&e.a==="root"?"#bbb2ab":colors[(b?.group??-1)+1],"stroke-opacity":e.kind==="category"?.22:e.kind==="keywords"?.12:Math.min(.65,.23+.07*(e.shared||0)),"stroke-width":e.a==="root"?1.1:Math.min(1.5,.65+.12*(e.shared||0)),"vector-effect":"non-scaling-stroke",...(e.kind==="draft"?{"stroke-dasharray":"2 3"}:{})},links)});
  const dense=graph.nodes.length>800;
  for(const n of graph.nodes){
   const kind=typeof n.kind==="string"?n.kind:"memory";
   const g=el("g",{class:"node","data-key":n.key},dots),col=kind==="cloud_api"?"#9acfff":n.key==="character:hero"||kind==="infinite_hero"?"#e7c46d":kind==="infinite_love"?"#f0a3c5":kind.startsWith("infinite_")?"#c7b3df":kind.startsWith("novel_")?"#e0c497":kind.startsWith("immortal_")?"#d0c0a5":kind.startsWith("evolution_")?"#c5b7ed":kind.startsWith("living_")?"#b1d9ca":kind.startsWith("destiny_")?"#b8c9e8":kind.startsWith("guardian_")?(["#dcf0ff","#a1e7bd","#b5a9e9","#dcc7ff","#ed9772","#f0d496","#eea8cb","#a9d8e4","#fff0d0"][["reika","seirana","mikage","tokihana","akatsuki","shiori","yumeka","meirin","amatsuka"].indexOf(n.guardian_actor)]||"#e4d8ac"):kind.startsWith("shadow_")?"#d9c799":kind.startsWith("heart_")?"#f2a9c9":colors[n.group+1];items.set(n.key,g);
   const major=n.key==="root"||n.key==="cloud:api"||n.key.startsWith("hub:")||n.kind==="fictional_chapter"||n.kind==="book"||n.kind==="epoch"||n.kind==="book_segment"||n.kind==="heart_root"||n.kind==="heart_topic"||n.kind==="shadow_root"||n.kind==="shadow_topic"||n.kind==="guardian_root"||n.kind==="guardian_character"||n.kind==="destiny_root"||n.kind==="destiny_topic"||n.kind==="destiny_character"||n.kind==="living_root"||n.kind==="living_topic"||n.kind==="evolution_root"||n.kind==="evolution_subject"||n.kind==="immortal_root"||n.kind==="immortal_saga"||n.kind==="novel_epoch"||n.kind==="novel_chapter"||n.kind==="infinite_root"||n.kind==="infinite_character"||n.kind==="infinite_stage"||n.key==="character:hero"||n.kind==="realm";
   const glyph=el("g",{},g);glyphs.set(n.key,glyph);
   if(births.has(n.key))g.setAttribute("opacity",".08");
   const root=n.key==="root",r=n.r;
   if(!dense||major)el("circle",{r:r*(root?5:4.5),fill:kind==="cloud_api"?"url(#cloud-glow)":"url(#glow"+(n.group+1)+")",opacity:root?1:.9,"pointer-events":"none"},glyph);
   if(kind==="cloud_api"){el("circle",{r:17,fill:"none",stroke:col,"stroke-width":.8,"stroke-opacity":.7},glyph);el("circle",{r:23,fill:"none",stroke:col,"stroke-width":.6,"stroke-dasharray":"2 5","stroke-opacity":.35},glyph)}
   if(root){el("circle",{r:r*2.3,fill:"none",stroke:"#ddcda9","stroke-opacity":.48,"stroke-width":.8},glyph);el("circle",{r:r*3.05,fill:"none",stroke:"#e5ceb0","stroke-opacity":.17,"stroke-width":.7},glyph)}
   if(n.kind==="draft"){el("circle",{r:r*1.7,fill:"none",stroke:col,"stroke-dasharray":"2 2","stroke-width":1},glyph)}
   else{el("circle",{r:r,fill:col,opacity:.91},glyph);if(!dense||major)el("circle",{r:r*.42,fill:"#fff9eb"},glyph)}
   el("circle",{r:Math.max(dense&&!major?4:7,r*1.6),fill:"transparent"},glyph);
   if(n.key==="root"||n.key==="cloud:api"||n.key.startsWith("hub:")||n.kind==="epoch"||n.kind==="heart_root"||n.kind==="heart_topic"||n.kind==="shadow_root"||n.kind==="shadow_topic"||n.kind==="guardian_root"||n.kind==="guardian_character"||n.kind==="destiny_root"||n.kind==="destiny_topic"||n.kind==="destiny_character"||n.kind==="living_root"||n.kind==="living_topic"||n.kind==="evolution_root"||n.kind==="evolution_subject"||n.kind==="immortal_root"||n.kind==="immortal_saga"||n.kind==="novel_epoch"||n.kind==="novel_chapter"||n.kind==="infinite_root"||n.kind==="infinite_character"||n.kind==="infinite_stage"||n.key==="character:hero"||n.kind==="realm"){
    if(!root)el("path",{d:"M-9 0H9M0 -9V9",stroke:col,"stroke-width":.8,opacity:.65},glyph);
    const t=el("text",{x:0,y:root?37:24,"text-anchor":"middle",fill:col,class:root?"label root-label":"label"},glyph);t.textContent=n.label;labels.set(n.key,t);
   }
   const title=el("title",{},g);title.textContent=n.label;
  }
  desired=baseFit();if(initial||firstSnapshot||scopeChanged||motion.matches)fit=desired;
  if(!graph.byKey.has(active))active="";
  replayAt=0;shown=graph.nodes.length;place();applyDetail();updateGlyphs();
  if(isNewPublication&&publication&&!motion.matches&&!paused&&!document.hidden){for(const [i,link] of publicationLinks(publication,graph).entries())birthTrails.set("birth:"+publication.number+":"+i,{...link,at:now});while(birthTrails.size>10)birthTrails.delete(birthTrails.keys().next().value!);pulse(publication.key,"#ffe2a0",now);births.set(publication.key,now);if(publication.first){for(const key of [publication.segment,"book:"+publication.volume])if(graph.byKey.has(key)){births.set(key,now);pulse(key,"#e7c46d",now)}if((publication.volume-1)%8===0){const key="novel:epoch:"+publication.epoch;if(graph.byKey.has(key)){births.set(key,now);pulse(key,"#c0a9e8",now)}}}if(publication.complete)pulse(publication.segment,"#fff3cb",now);if(!readerOpen&&!active&&!drag&&now>manualUntil&&zoom===1&&graph.byKey.has(publication.key)){const n=graph.byKey.get(publication.key),target=1.35,k=target*desired;focusMotion={start:now,fromZoom:zoom,toZoom:target,fromX:panX,fromY:panY,toX:-(n.x-camera.cx)*s*k,toY:-(n.y-camera.cy)*s*k}}}
  if(wasReceived&&!scopeChanged&&!paused&&!motion.matches){for(const n of next.records){if(n.key.startsWith("draft:")&&!oldKeys.has(n.key)){births.set(n.key,now);pulse(n.key,"#e8c6ed",now)}}}
  status();invalidate();
 }
 function clearActivity(){works.clear();stages.clear();birthTrails.clear();for(const p of particles.values())p.group.remove();particles.clear();for(const ring of highlighted.values())ring.remove();highlighted.clear();status();invalidate()}
 function setActivity(next:Activity){
  if(next.session!==session){clearActivity();seen.clear();session=next.session}
  if(paused||document.hidden)return;
  const now=performance.now(),incoming=new Set(next.active.map(a=>a.id));
  for(const [id,a] of works)if(!a.terminal&&!incoming.has(id)&&!next.recent.some(x=>x.id===id)){works.delete(id);stages.delete(id)}
  function ingest(item:Work,terminal:boolean){
   if(terminal&&seen.has(item.id))return;
   const old=stages.get(item.id),events=activityEvents(item,old?.seq||0) as Work[];
   const fallback=!events.length&&(!old||(!item.events?.length&&old.current.stage!==item.stage))?[item]:[];
   const queue=[...(old?.queue||[]),...events,...fallback].slice(-10);
   const current=old?.current||queue.shift()||item;
   const seq=Math.max(old?.seq||0,...events.map(e=>e.seq||0));
   stages.set(item.id,{seq,queue,started:old?.started||now,current,terminal});
   works.set(item.id,{item,started:now,terminal});
   if(terminal)seen.add(item.id);
  }
  for(const item of next.active)ingest(item,false);
  for(const item of next.recent)ingest(item,true);
  while(seen.size>256)seen.delete(seen.values().next().value!);
  status();invalidate();
 }
 function drawActivity(now:number){
  const used=new Set<string>(),hot=new Map<string,string>(),inverse=1/Math.max(.00001,zoom*fit);
  let routeBudget=graph.nodes.length>800?6:16;
  for(const [id,a] of stages){
   let elapsed=now-a.started;
   const duration=a.current.stage==="waiting"?950:a.current.stage==="received"?680:500;
   if(a.queue.length&&(elapsed>=duration||motion.matches)){a.current=motion.matches?a.queue[a.queue.length-1]:a.queue.shift()!;if(motion.matches)a.queue=[];a.started=now;elapsed=0;status();if(a.current.stage==="received")pulse("root","#ffe2a0",now);if(a.current.stage==="saved"||a.current.stage==="published")pulse(a.current.target,"#ffe2a0",now)}
   if(a.terminal&&!a.queue.length&&elapsed>1500){stages.delete(id);works.delete(id);status();continue}
   const fade=a.terminal&&!a.queue.length?Math.max(0,1-elapsed/1500):1;
   const routes=flowPaths(a.current,graph).slice(0,routeBudget);routeBudget-=routes.length;
   routes.forEach((route,i)=>{
    const key=id+":"+i;used.add(key);
    let p=particles.get(key);
    if(!p){const group=el("g",{},flows),line=el("polyline",{fill:"none","stroke-width":1.1},group),dots=Array.from({length:6},()=>el("circle",{r:1.5},group));p={group,line,dots};particles.set(key,p)}
    p.line.setAttribute("points",route.points.map(q=>(q.x*s)+","+(q.y*s)).join(" "));
    p.line.setAttribute("vector-effect","non-scaling-stroke");p.line.setAttribute("stroke",route.color);p.line.setAttribute("opacity",String(.35*fade));
    p.dots.forEach((d,j)=>{const count=graph.nodes.length>800?3:6,t=motion.matches?.5:((elapsed/(1000+120*i)+i*.17-j*.055+2)%1),q=pointOn(route.points,t);d.setAttribute("r",String((j===0?2.8:Math.max(.65,2.1-j*.27))*inverse));d.setAttribute("cx",String(q.x*s));d.setAttribute("cy",String(q.y*s));d.setAttribute("fill",route.color);d.setAttribute("opacity",String((j>=count||motion.matches&&j>0?0:1-j*.14)*fade))});
   });
   if(!a.terminal||fade>.15){
    hot.set("root","#e9cf9c");
    if(a.current.stage==="waiting"||a.current.stage==="received")hot.set("cloud:api","#91cbff");
    if(a.current.stage==="request"||a.current.stage==="context")for(const key of [a.current.source,...(a.current.sources||[])].slice(0,8))hot.set(key,"#e8c6ed");
    if(a.current.stage==="validating")hot.set("hub:4","#c0a9e8");
    if(a.current.stage==="saving"||a.current.stage==="saved"||a.current.stage==="published")hot.set(a.current.target,"#ffe2a0");
   }
  }
  for(const [key,b] of birthTrails){
   const a=graph.byKey.get(b.a),z=graph.byKey.get(b.b),t=(now-b.at)/1700;
   if(t>=1||!a||!z||motion.matches){birthTrails.delete(key);continue}
   if(routeBudget<=0)continue;routeBudget--;used.add(key);
   let p=particles.get(key);if(!p){const group=el("g",{},flows),line=el("polyline",{fill:"none","stroke-width":1.2,"vector-effect":"non-scaling-stroke"},group),dots=Array.from({length:4},()=>el("circle",{},group));p={group,line,dots};particles.set(key,p)}
   p.line.setAttribute("points",[[a.x*s,a.y*s],[z.x*s,z.y*s]].map(v=>v.join(",")).join(" "));p.line.setAttribute("stroke",b.color);p.line.setAttribute("opacity",String(.5*(1-t)));
   p.dots.forEach((dot,i)=>{const q=pointOn([a,z],Math.max(0,Math.min(1,t*1.3-i*.09)));dot.setAttribute("cx",String(q.x*s));dot.setAttribute("cy",String(q.y*s));dot.setAttribute("r",String((2.8-i*.5)*inverse));dot.setAttribute("fill",b.color);dot.setAttribute("opacity",String((1-t)*(1-i*.15)))})
  }
  for(const [id,p] of particles)if(!used.has(id)){p.group.remove();particles.delete(id)}
  for(const [key,ring] of highlighted)if(!hot.has(key)||!graph.byKey.has(key)){ring.remove();highlighted.delete(key)}
  for(const [key,color] of [...hot].slice(0,12)){
   const n=graph.byKey.get(key);if(!n)continue;
   let ring=highlighted.get(key);if(!ring){ring=el("circle",{fill:"none","stroke-width":1.4,"vector-effect":"non-scaling-stroke"},flows);highlighted.set(key,ring)}
   ring.setAttribute("cx",String(n.x*s));ring.setAttribute("cy",String(n.y*s));ring.setAttribute("stroke",color);ring.setAttribute("r",String((n.r+8+(motion.matches?0:4*Math.sin(now/240)))*inverse));ring.setAttribute("opacity",String(motion.matches?.6:.55+.35*Math.sin(now/220)**2));
  }
  for(const [key,wave] of waves){
   const n=graph.byKey.get(key),t=(now-wave.at)/1300;
   if(t>=1||!n||motion.matches){for(const ring of wave.rings)ring.remove();waves.delete(key);continue}
   wave.rings.forEach((ring,i)=>{const phase=Math.max(0,t-i*.18);ring.setAttribute("cx",String(n.x*s));ring.setAttribute("cy",String(n.y*s));ring.setAttribute("r",String((n.r+6+phase*45)*inverse));ring.setAttribute("opacity",String((1-phase)*.75))});
  }
 }
 function frame(now:number){
  raf=0;const dt=Math.max(0,Math.min(60,now-last));last=now;
  if(replayAt){const n=motion.matches?graph.nodes.length:Math.min(graph.nodes.length,1+Math.floor((now-replayAt)/Math.max(22,Math.min(245,30000/Math.max(1,graph.nodes.length-1)))));if(n!==shown)reveal(n);if(n===graph.nodes.length){replayAt=0;level=-1;status()}}
  const k=motion.matches?1:1-Math.exp(-dt/200);fit+=(desired-fit)*k;if(Math.abs(desired-fit)<.001)fit=desired;
  if(focusMotion){const f=focusMotion,t=motion.matches?1:Math.min(1,(now-f.start)/360),e=1-Math.pow(1-t,3);zoom=f.fromZoom+(f.toZoom-f.fromZoom)*e;panX=f.fromX+(f.toX-f.fromX)*e;panY=f.fromY+(f.toY-f.fromY)*e;if(t===1)focusMotion=null}
  const cameraOrigin=origin();world.setAttribute("transform","translate("+cameraOrigin.x+" "+cameraOrigin.y+") scale("+cameraOrigin.k+")");
  applyDetail();if(now-lastLabelFrame>80||fit!==desired||focusMotion||!stages.size){updateGlyphs();lastLabelFrame=now}
  drawActivity(now);
  for(const [key,start] of births){const t=Math.min(1,(now-start)/1000);const g=items.get(key);if(g)g.setAttribute("opacity",String(.08+.92*t));if(t===1||!g||motion.matches){g?.removeAttribute("opacity");births.delete(key)}}
  if(births.size||waves.size||birthTrails.size||replayAt||focusMotion||fit!==desired||[...stages.values()].some(a=>a.terminal||a.queue.length||!motion.matches))invalidate();
 }
 resize();render(snapshot,true);
 const observer=typeof ResizeObserver==="function"?new ResizeObserver(resize):null;
 if(observer)observer.observe(svg);else window.addEventListener("resize",resize);
 function visibility(){if(document.hidden){cancelAnimationFrame(raf);raf=0;for(const key of births.keys())items.get(key)?.removeAttribute("opacity");births.clear();for(const wave of waves.values())for(const ring of wave.rings)ring.remove();waves.clear();birthTrails.clear();clearActivity()}else{last=performance.now();invalidate()}}
 document.addEventListener("visibilitychange",visibility);
 svg.addEventListener("wheel",e=>{e.preventDefault();manualUntil=performance.now()+60000;focusMotion=null;const rect=svg.getBoundingClientRect(),x=e.clientX-rect.left,y=e.clientY-rect.top,old=origin(),next=clamp(zoom*Math.exp(-e.deltaY*.001),.35,12),ratio=next/zoom;zoom=next;panX=x-(x-old.x)*ratio-w/2+camera.cx*s*zoom*fit;panY=y-(y-old.y)*ratio-h/2+camera.cy*s*zoom*fit;invalidate()},{passive:false});
 svg.addEventListener("pointerdown",e=>{if(e.button===0){manualUntil=performance.now()+60000;focusMotion=null;drag={x:e.clientX,y:e.clientY,moved:false}}});
 svg.addEventListener("pointermove",e=>{if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>2){drag.moved=true;if(!svg.hasPointerCapture(e.pointerId))svg.setPointerCapture(e.pointerId)}if(drag.moved){panX+=dx;panY+=dy;invalidate()}drag.x=e.clientX;drag.y=e.clientY});
 svg.addEventListener("pointerup",e=>{if(!drag?.moved){const key=(e.target as Element).closest("[data-key]")?.getAttribute("data-key");if(key&&graph.byKey.has(key)){active=key;redrawSelection();info.textContent=graph.byKey.get(key).label;const match=/^(?:book:|segment:[a-z]+:)([1-9]\d*)$/.exec(key);if(match&&zoom>=2.4)onVolume?.(Number(match[1]));else if(!match&&(labels.has(key)))focusNode(key);else invalidate()}}drag=null});
 svg.addEventListener("dblclick",e=>{const key=(e.target as Element).closest("[data-key]")?.getAttribute("data-key")||"";const match=/^(?:book:|segment:[a-z]+:)([1-9]\d*)$/.exec(key);if(match)onVolume?.(Number(match[1]))});
 for(const name of ["pointercancel","lostpointercapture"])svg.addEventListener(name,()=>{drag=null});
 return {render,setActivity,clearActivity,resize,setReader(open:boolean,full:boolean){readerOpen=open;paused=full;if(full){cancelAnimationFrame(raf);raf=0;for(const key of births.keys())items.get(key)?.removeAttribute("opacity");births.clear();focusMotion=null;clearActivity();for(const wave of waves.values())for(const ring of wave.rings)ring.remove();waves.clear();birthTrails.clear()}else{last=performance.now();invalidate()}},replay(){focusMotion=null;zoom=1;panX=panY=0;active="";redrawSelection();if(graph.nodes.length<=1){status();invalidate();return}replayAt=performance.now();reveal(1);invalidate()},dispose(){disposed=true;cancelAnimationFrame(raf);observer?.disconnect();if(!observer)window.removeEventListener("resize",resize);document.removeEventListener("visibilitychange",visibility);for(const wave of waves.values())for(const ring of wave.rings)ring.remove();waves.clear();birthTrails.clear();clearActivity()}};
}
