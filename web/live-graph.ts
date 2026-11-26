import {layout,palette,detailLevel,cameraFrame} from "./memory-layout.mjs";
import {flowPaths,pointOn} from "./activity-flow.mjs";
import {rng,clamp} from "./geometry.mjs";
type Snapshot={records:any[],edges:any[],total:number,limited:boolean,volume?:number};
type Work={id:string,kind:string,source:string,target:string,stage:string};
type Activity={session:string,revision:number,active:Work[],recent:Work[]};
export function mountGraph(svg:SVGSVGElement,info:HTMLElement,onVolume?:(volume:number)=>void){
 const ns="http://www.w3.org/2000/svg";
 function el<K extends keyof SVGElementTagNameMap>(tag:K,attrs:Record<string,string|number>={},parent:SVGElement=svg){const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,String(v));parent.append(e);return e}
 const defs=el("defs"),colors=["#fffdf4",...palette];
 colors.forEach((c,i)=>{const g=el("radialGradient",{id:"glow"+i},defs);for(const [offset,opacity] of [[0,.92],[.11,.65],[.25,.26],[.5,.08],[1,0]])el("stop",{offset,"stop-color":c,"stop-opacity":opacity},g)});
 const stars=el("g",{"pointer-events":"none"}),world=el("g"),links=el("g",{"pointer-events":"none"},world),dots=el("g",{},world),flows=el("g",{"pointer-events":"none"},world),overlay=el("g",{"pointer-events":"none"},world);
 const random=rng(920),starData=Array.from({length:2200},()=>({x:random(),y:random(),r:.12+random()**7*.72,o:.035+random()**2*.34}));
 const starEls=starData.map((p,i)=>el("circle",{r:p.r,fill:i%13===0?"#d8b9a1":"#e1dcd8",opacity:p.o},stars));
 let snapshot:Snapshot={records:[],edges:[],total:0,limited:false},graph=layout(snapshot),w=1,h=1,s=1,zoom=1,panX=0,panY=0,fit=1,desired=1,active="",drag:null|{x:number,y:number,moved:boolean}=null,items=new Map<string,SVGGElement>(),edgeEls:SVGLineElement[]=[],drawnEdges:any[]=[],replayAt=0,shown=0,last=performance.now(),raf=0,disposed=false;
 let session="",works=new Map<string,{item:Work,started:number,terminal:boolean}>(),seen=new Set<string>();
 let receivedSnapshot=false,maxChapter=0,level=-1;
 let recentChapterKeys=new Set<string>();
 const births=new Map<string,number>();
 const glyphs=new Map<string,SVGGElement>(),labels=new Map<string,SVGTextElement>(),labelWidths=new Map<string,number>();
 let camera=cameraFrame(graph.bounds,w,h),glyphScale=NaN,selectionGlyph:SVGGElement|null=null;
 let focusMotion:null|{start:number,fromZoom:number,toZoom:number,fromX:number,fromY:number,toX:number,toY:number}=null;
 const motion=matchMedia("(prefers-reduced-motion: reduce)");
 const particles=new Map<string,{group:SVGGElement,line:SVGPolylineElement,dots:SVGCircleElement[]}>();
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
  const priority=(key:string)=>key==="root"?0:key===active?1:key.startsWith("hub:")?2:graph.byKey.get(key)?.kind?.endsWith("_root")?3:4;
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
 function status(){const count=[...works.values()].filter(a=>!a.terminal).length;info.textContent=(snapshot.volume?"Том "+snapshot.volume+" · ":"")+snapshot.total+" записей · "+graph.edges.length+" связей"+(snapshot.limited?" · ограничено 5000":"")+(snapshot.volume?" · ↻ общая карта":"")+(count?" · Cloud.ru: "+count:"")}
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
  redrawSelection();
 }
 function invalidate(){if(!raf&&!disposed&&!document.hidden)raf=requestAnimationFrame(frame)}
 function resize(){const nw=Math.max(1,svg.clientWidth),nh=Math.max(1,svg.clientHeight);if(nw===w&&nh===h)return;focusMotion=null;panX=panY=0;zoom=1;active="";level=-1;w=nw;h=nh;s=Math.max(1,Math.min(w,h));desired=baseFit();fit=desired;svg.setAttribute("viewBox","0 0 "+w+" "+h);starEls.forEach((e,i)=>{e.setAttribute("cx",String(starData[i].x*w));e.setAttribute("cy",String(starData[i].y*h))});place();glyphScale=NaN;invalidate()}
 function reveal(n:number){
  const visible=new Set(graph.nodes.slice(0,n).map(x=>x.key));graph.nodes.forEach(x=>items.get(x.key)?.setAttribute("visibility",visible.has(x.key)?"visible":"hidden"));drawnEdges.forEach((e,i)=>edgeEls[i]?.setAttribute("visibility",visible.has(e.a)&&visible.has(e.b)?"visible":"hidden"));shown=n;
 }
 function applyDetail(){
  const next=detailLevel(graph.nodes.length,zoom);
  if(level===next||replayAt)return;
  level=next;
  const visible=new Set<string>();
  for(const n of graph.nodes){const major=n.key==="root"||n.key.startsWith("hub:")||n.key.startsWith("canon:")||n.kind==="epoch"||n.kind==="book"||n.kind==="book_segment"||n.kind==="draft"||n.kind==="heart_root"||n.kind==="heart_topic"||n.kind==="shadow_root"||n.kind==="shadow_topic"||n.kind==="guardian_root"||n.kind==="guardian_character"||n.kind==="destiny_root"||n.kind==="destiny_topic"||n.kind==="destiny_character"||n.kind==="living_root"||n.kind==="living_topic"||n.kind==="evolution_root"||n.kind==="evolution_subject"||n.kind==="immortal_root"||n.kind==="immortal_saga"||n.kind==="realm"||n.key===active||recentChapterKeys.has(n.key);
   const show=next===2||n.group!==4||major||(next===1&&n.kind==="fictional_chapter");
   if(show)visible.add(n.key);items.get(n.key)?.setAttribute("visibility",show?"visible":"hidden");}
  drawnEdges.forEach((e,i)=>edgeEls[i]?.setAttribute("visibility",visible.has(e.a)&&visible.has(e.b)&&(next===2||e.kind!=="keywords")?"visible":"hidden"));
 }
 function render(next:Snapshot,initial=false){
  if(!initial&&JSON.stringify(next)===JSON.stringify(snapshot))return;
  const now=performance.now();
  const scopeChanged=snapshot.volume!==next.volume,firstSnapshot=!receivedSnapshot&&!initial;
  if(scopeChanged){zoom=1;panX=0;panY=0;active="";births.clear();replayAt=0;focusMotion=null;}
  for(const n of next.records){if(/^c:[1-9]\d*$/.test(n.key)){const id=Number(n.key.slice(2));if(receivedSnapshot&&!scopeChanged&&!next.volume&&id>maxChapter&&!motion.matches)births.set(n.key,now);}}
  for(const n of next.records){if(/^c:[1-9]\d*$/.test(n.key))maxChapter=Math.max(maxChapter,Number(n.key.slice(2)));}
  if(!initial)receivedSnapshot=true;
  snapshot=next;graph=layout(next);level=-1;
  recentChapterKeys=new Set<string>(next.records.filter(n=>/^c:[1-9]\d*$/.test(n.key)).sort((a,b)=>Number(b.key.slice(2))-Number(a.key.slice(2))).slice(0,20).map(n=>n.key));items.clear();glyphs.clear();labels.clear();labelWidths.clear();glyphScale=NaN;links.replaceChildren();dots.replaceChildren();overlay.replaceChildren();
  // Always preserve root, categories and canon links; thin dense secondary edges only.
  const essential=graph.edges.filter(e=>e.kind==="category"||e.kind==="chronology"||e.a.startsWith("canon:")||e.kind==="draft"||e.kind.startsWith("heart_")||e.kind.startsWith("shadow_")||e.kind.startsWith("guardian_")||e.kind.startsWith("destiny_")||e.kind.startsWith("living_")||e.kind.startsWith("evolution_")||e.kind.startsWith("immortal_"));
  const essentialSet=new Set(essential);const secondary=graph.edges.filter(e=>!essentialSet.has(e));
  drawnEdges=essential.concat(secondary.slice(0,Math.max(0,10000-essential.length)));
  edgeEls=drawnEdges.map(e=>{const b=graph.byKey.get(e.b);return el("line",{stroke:e.kind==="immortal_consequence"?"#d9bd80":e.kind==="immortal_love"?"#efa3c4":e.kind==="immortal_clue"||e.kind==="immortal_reveal"?"#c0a9e8":e.kind==="immortal_journey"?"#9fc9ec":e.kind.startsWith("immortal_")?"#d0c0a5":e.kind.startsWith("evolution_")?"#c5b7ed":e.kind.startsWith("living_")?"#b1d9ca":e.kind.startsWith("destiny_")?"#b8c9e8":e.kind.startsWith("guardian_")?"#e4d8ac":e.kind.startsWith("shadow_")?"#d9c799":e.kind.startsWith("heart_")?"#efa3c4":e.kind==="category"&&e.a==="root"?"#bbb2ab":colors[(b?.group??-1)+1],"stroke-opacity":e.kind==="category"?.22:e.kind==="keywords"?.12:Math.min(.65,.23+.07*(e.shared||0)),"stroke-width":e.a==="root"?1.1:Math.min(1.5,.65+.12*(e.shared||0)),"vector-effect":"non-scaling-stroke",...(e.kind==="draft"?{"stroke-dasharray":"2 3"}:{})},links)});
  const dense=graph.nodes.length>800;
  for(const n of graph.nodes){
   const kind=typeof n.kind==="string"?n.kind:"memory";
   const g=el("g",{class:"node","data-key":n.key},dots),col=kind.startsWith("immortal_")?"#d0c0a5":kind.startsWith("evolution_")?"#c5b7ed":kind.startsWith("living_")?"#b1d9ca":kind.startsWith("destiny_")?"#b8c9e8":kind.startsWith("guardian_")?(["#dcf0ff","#a1e7bd","#b5a9e9","#dcc7ff","#ed9772","#f0d496","#eea8cb","#a9d8e4","#fff0d0"][["reika","seirana","mikage","tokihana","akatsuki","shiori","yumeka","meirin","amatsuka"].indexOf(n.guardian_actor)]||"#e4d8ac"):kind.startsWith("shadow_")?"#d9c799":kind.startsWith("heart_")?"#f2a9c9":colors[n.group+1];items.set(n.key,g);
   const major=n.key==="root"||n.key.startsWith("hub:")||n.kind==="fictional_chapter"||n.kind==="book"||n.kind==="epoch"||n.kind==="book_segment"||n.kind==="heart_root"||n.kind==="heart_topic"||n.kind==="shadow_root"||n.kind==="shadow_topic"||n.kind==="guardian_root"||n.kind==="guardian_character"||n.kind==="destiny_root"||n.kind==="destiny_topic"||n.kind==="destiny_character"||n.kind==="living_root"||n.kind==="living_topic"||n.kind==="evolution_root"||n.kind==="evolution_subject"||n.kind==="immortal_root"||n.kind==="immortal_saga"||n.kind==="realm";
   const glyph=el("g",{},g);glyphs.set(n.key,glyph);
   if(births.has(n.key))g.setAttribute("opacity",".08");
   const root=n.key==="root",r=n.r;
   if(!dense||major)el("circle",{r:r*(root?5:4.5),fill:"url(#glow"+(n.group+1)+")",opacity:root?1:.9,"pointer-events":"none"},glyph);
   if(root){el("circle",{r:r*2.3,fill:"none",stroke:"#ddcda9","stroke-opacity":.48,"stroke-width":.8},glyph);el("circle",{r:r*3.05,fill:"none",stroke:"#e5ceb0","stroke-opacity":.17,"stroke-width":.7},glyph)}
   if(n.kind==="draft"){el("circle",{r:r*1.7,fill:"none",stroke:col,"stroke-dasharray":"2 2","stroke-width":1},glyph)}
   else{el("circle",{r:r,fill:col,opacity:.91},glyph);if(!dense||major)el("circle",{r:r*.42,fill:"#fff9eb"},glyph)}
   el("circle",{r:Math.max(dense&&!major?4:7,r*1.6),fill:"transparent"},glyph);
   if(n.key==="root"||n.key.startsWith("hub:")||n.kind==="epoch"||n.kind==="heart_root"||n.kind==="heart_topic"||n.kind==="shadow_root"||n.kind==="shadow_topic"||n.kind==="guardian_root"||n.kind==="guardian_character"||n.kind==="destiny_root"||n.kind==="destiny_topic"||n.kind==="destiny_character"||n.kind==="living_root"||n.kind==="living_topic"||n.kind==="evolution_root"||n.kind==="evolution_subject"||n.kind==="immortal_root"||n.kind==="immortal_saga"||n.kind==="realm"){
    if(!root)el("path",{d:"M-9 0H9M0 -9V9",stroke:col,"stroke-width":.8,opacity:.65},glyph);
    const t=el("text",{x:0,y:root?37:24,"text-anchor":"middle",fill:col,class:root?"label root-label":"label"},glyph);t.textContent=n.label;labels.set(n.key,t);
   }
   const title=el("title",{},g);title.textContent=n.label;
  }
  desired=baseFit();if(initial||firstSnapshot||scopeChanged||motion.matches)fit=desired;
  if(!graph.byKey.has(active))active="";
  replayAt=0;shown=graph.nodes.length;place();applyDetail();updateGlyphs();status();invalidate();
 }
 function clearActivity(){works.clear();for(const p of particles.values())p.group.remove();particles.clear();status();invalidate()}
 function setActivity(next:Activity){
  if(next.session!==session){clearActivity();seen.clear();session=next.session}
  const now=performance.now(),incoming=new Set(next.active.map(a=>a.id));
  for(const [id,a] of works)if(!a.terminal&&!incoming.has(id))works.delete(id);
  for(const item of next.active){const old=works.get(item.id);works.set(item.id,{item,started:old&&old.item.stage===item.stage?old.started:now,terminal:false})}
  for(const item of next.recent)if(!seen.has(item.id)){seen.add(item.id);works.set(item.id,{item,started:now,terminal:true})}
  while(seen.size>256)seen.delete(seen.values().next().value!);
  if(!active||works.size)status();invalidate();
 }
 function drawActivity(now:number){
  for(const [id,a] of works){
   const elapsed=now-a.started;
   if(a.terminal&&elapsed>1100){works.delete(id);continue}
   const route=flowPaths(a.item,graph)[0];if(!route)continue;
   let p=particles.get(id);
   if(!p){const group=el("g",{},flows),line=el("polyline",{fill:"none","stroke-width":.7},group),dots=Array.from({length:6},()=>el("circle",{r:1.5},group));p={group,line,dots};particles.set(id,p)}
   const fade=a.terminal?Math.max(0,1-elapsed/1100):1;
   p.line.setAttribute("points",route.points.map(q=>(q.x*s)+","+(q.y*s)).join(" "));
   p.line.setAttribute("vector-effect","non-scaling-stroke");p.line.setAttribute("stroke",route.color);p.line.setAttribute("opacity",String(.28*fade));
   p.dots.forEach((d,i)=>{const t=motion.matches?.5:a.terminal?Math.min(1,elapsed/1000+i*.025):((elapsed/1500+i/6)%1);const q=pointOn(route.points,t);d.setAttribute("r",String(2/Math.max(.00001,zoom*fit)));d.setAttribute("cx",String(q.x*s));d.setAttribute("cy",String(q.y*s));d.setAttribute("fill",route.color);d.setAttribute("opacity",String((motion.matches&&i>0?0:.9)*fade))});
   // The validating stage is the actual local schema/canon check, not model introspection.
   if(a.item.stage==="validating"){for(const key of ["canon:5","canon:6","canon:13"])items.get(key)?.setAttribute("opacity",String(.72+.28*(motion.matches?1:Math.sin(now/100)**2)))}
  }
  if(![...works.values()].some(a=>a.item.stage==="validating"))for(const key of ["canon:5","canon:6","canon:13"])items.get(key)?.removeAttribute("opacity");
  for(const [id,p] of particles)if(!works.has(id)){p.group.remove();particles.delete(id)}
 }
 function frame(now:number){
  raf=0;const dt=Math.max(0,Math.min(60,now-last));last=now;
  if(replayAt){const n=motion.matches?graph.nodes.length:Math.min(graph.nodes.length,1+Math.floor((now-replayAt)/Math.max(22,Math.min(245,30000/Math.max(1,graph.nodes.length-1)))));if(n!==shown)reveal(n);if(n===graph.nodes.length){replayAt=0;level=-1;status()}}
  const k=motion.matches?1:1-Math.exp(-dt/200);fit+=(desired-fit)*k;if(Math.abs(desired-fit)<.001)fit=desired;
  if(focusMotion){const f=focusMotion,t=motion.matches?1:Math.min(1,(now-f.start)/360),e=1-Math.pow(1-t,3);zoom=f.fromZoom+(f.toZoom-f.fromZoom)*e;panX=f.fromX+(f.toX-f.fromX)*e;panY=f.fromY+(f.toY-f.fromY)*e;if(t===1)focusMotion=null}
  const cameraOrigin=origin();world.setAttribute("transform","translate("+cameraOrigin.x+" "+cameraOrigin.y+") scale("+cameraOrigin.k+")");
  applyDetail();updateGlyphs();
  drawActivity(now);
  for(const [key,start] of births){const t=Math.min(1,(now-start)/700);const g=items.get(key);if(g)g.setAttribute("opacity",String(.08+.92*t));if(t===1||!g||motion.matches){g?.removeAttribute("opacity");births.delete(key)}}
  if(births.size||replayAt||focusMotion||fit!==desired||[...works.values()].some(a=>a.terminal||!motion.matches))invalidate();
 }
 resize();render(snapshot,true);
 const observer=typeof ResizeObserver==="function"?new ResizeObserver(resize):null;
 if(observer)observer.observe(svg);else window.addEventListener("resize",resize);
 function visibility(){if(document.hidden){cancelAnimationFrame(raf);raf=0;for(const key of births.keys())items.get(key)?.removeAttribute("opacity");births.clear();clearActivity()}else{last=performance.now();invalidate()}}
 document.addEventListener("visibilitychange",visibility);
 svg.addEventListener("wheel",e=>{e.preventDefault();focusMotion=null;const rect=svg.getBoundingClientRect(),x=e.clientX-rect.left,y=e.clientY-rect.top,old=origin(),next=clamp(zoom*Math.exp(-e.deltaY*.001),.35,12),ratio=next/zoom;zoom=next;panX=x-(x-old.x)*ratio-w/2+camera.cx*s*zoom*fit;panY=y-(y-old.y)*ratio-h/2+camera.cy*s*zoom*fit;invalidate()},{passive:false});
 svg.addEventListener("pointerdown",e=>{if(e.button===0){focusMotion=null;drag={x:e.clientX,y:e.clientY,moved:false}}});
 svg.addEventListener("pointermove",e=>{if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>2){drag.moved=true;if(!svg.hasPointerCapture(e.pointerId))svg.setPointerCapture(e.pointerId)}if(drag.moved){panX+=dx;panY+=dy;invalidate()}drag.x=e.clientX;drag.y=e.clientY});
 svg.addEventListener("pointerup",e=>{if(!drag?.moved){const key=(e.target as Element).closest("[data-key]")?.getAttribute("data-key");if(key&&graph.byKey.has(key)){active=key;redrawSelection();info.textContent=graph.byKey.get(key).label;const match=/^(?:book:|segment:[a-z]+:)([1-9]\d*)$/.exec(key);if(match&&zoom>=2.4)onVolume?.(Number(match[1]));else if(!match&&(labels.has(key)))focusNode(key);else invalidate()}}drag=null});
 svg.addEventListener("dblclick",e=>{const key=(e.target as Element).closest("[data-key]")?.getAttribute("data-key")||"";const match=/^(?:book:|segment:[a-z]+:)([1-9]\d*)$/.exec(key);if(match)onVolume?.(Number(match[1]))});
 for(const name of ["pointercancel","lostpointercapture"])svg.addEventListener(name,()=>{drag=null});
 return {render,setActivity,clearActivity,resize,replay(){focusMotion=null;zoom=1;panX=panY=0;active="";redrawSelection();if(graph.nodes.length<=1){status();invalidate();return}replayAt=performance.now();reveal(1);invalidate()},dispose(){disposed=true;cancelAnimationFrame(raf);observer?.disconnect();if(!observer)window.removeEventListener("resize",resize);document.removeEventListener("visibilitychange",visibility);clearActivity()}};
}
