import {layout,palette} from "./memory-layout.mjs";
import {flowPaths,pointOn} from "./activity-flow.mjs";
import {rng,clamp} from "./geometry.mjs";
type Snapshot={records:any[],edges:any[],total:number,limited:boolean};
type Work={id:string,kind:string,source:string,target:string,stage:string};
type Activity={session:string,revision:number,active:Work[],recent:Work[]};
export function mountGraph(svg:SVGSVGElement,info:HTMLElement){
 const ns="http://www.w3.org/2000/svg";
 function el<K extends keyof SVGElementTagNameMap>(tag:K,attrs:Record<string,string|number>={},parent:SVGElement=svg){const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,String(v));parent.append(e);return e}
 const defs=el("defs"),colors=["#fffdf4",...palette];
 colors.forEach((c,i)=>{const g=el("radialGradient",{id:"glow"+i},defs);for(const [offset,opacity] of [[0,.92],[.11,.65],[.25,.26],[.5,.08],[1,0]])el("stop",{offset,"stop-color":c,"stop-opacity":opacity},g)});
 const stars=el("g",{"pointer-events":"none"}),world=el("g"),links=el("g",{"pointer-events":"none"},world),dots=el("g",{},world),flows=el("g",{"pointer-events":"none"},world),overlay=el("g",{"pointer-events":"none"},world);
 const random=rng(920),starData=Array.from({length:2200},()=>({x:random(),y:random(),r:.12+random()**7*.72,o:.035+random()**2*.34}));
 const starEls=starData.map((p,i)=>el("circle",{r:p.r,fill:i%13===0?"#d8b9a1":"#e1dcd8",opacity:p.o},stars));
 let snapshot:Snapshot={records:[],edges:[],total:0,limited:false},graph=layout(snapshot),w=1,h=1,s=1,zoom=1,panX=0,panY=0,fit=1,desired=1,active="",drag:null|{x:number,y:number,moved:boolean}=null,items=new Map<string,SVGGElement>(),edgeEls:SVGLineElement[]=[],drawnEdges:any[]=[],replayAt=0,shown=0,last=performance.now(),raf=0,disposed=false;
 let session="",works=new Map<string,{item:Work,started:number,terminal:boolean}>(),seen=new Set<string>();
 const motion=matchMedia("(prefers-reduced-motion: reduce)");
 const particles=new Map<string,{group:SVGGElement,line:SVGPolylineElement,dots:SVGCircleElement[]}>();
 function baseFit(){return Math.min(1,.45/graph.extent)}
 function status(){const count=[...works.values()].filter(a=>!a.terminal).length;info.textContent=snapshot.total+" записей · "+graph.edges.length+" связей"+(snapshot.limited?" · ограничено 5000":"")+(count?" · Cloud.ru: "+count:"")}
 function redrawSelection(){
  overlay.replaceChildren();const n=graph.byKey.get(active);if(!n)return;
  const g=el("g",{transform:"translate("+n.x*s+" "+n.y*s+")"},overlay),color=colors[n.group+1];
  el("circle",{r:Math.max(6,n.r*3.1),fill:"none",stroke:color,"stroke-width":.9},g);
  if(n.label){const title=String(n.label).slice(0,54);const label=el("text",{x:13,y:-7,fill:color,class:"active-label"},g);label.textContent=title;const b=label.getBBox();const rect=el("rect",{x:b.x-4,y:b.y-2,width:b.width+8,height:b.height+4,rx:2,fill:"#110b0e",stroke:color,"stroke-opacity":.72,"stroke-width":.65},g);g.insertBefore(rect,label)}
 }
 function place(){
  for(const n of graph.nodes)items.get(n.key)?.setAttribute("transform","translate("+n.x*s+" "+n.y*s+")");
  drawnEdges.forEach((e,i)=>{const a=graph.byKey.get(e.a),b=graph.byKey.get(e.b),line=edgeEls[i];if(!line||!a||!b)return;for(const [k,v] of Object.entries({x1:a.x*s,y1:a.y*s,x2:b.x*s,y2:b.y*s}))line.setAttribute(k,String(v))});
  redrawSelection();
 }
 function invalidate(){if(!raf&&!disposed&&!document.hidden)raf=requestAnimationFrame(frame)}
 function resize(){w=Math.max(1,svg.clientWidth);h=Math.max(1,svg.clientHeight);s=Math.min(w*1.52,h*.91);svg.setAttribute("viewBox","0 0 "+w+" "+h);starEls.forEach((e,i)=>{e.setAttribute("cx",String(starData[i].x*w));e.setAttribute("cy",String(starData[i].y*h))});place();invalidate()}
 function reveal(n:number){
  const visible=new Set(graph.nodes.slice(0,n).map(x=>x.key));graph.nodes.forEach(x=>items.get(x.key)?.setAttribute("visibility",visible.has(x.key)?"visible":"hidden"));drawnEdges.forEach((e,i)=>edgeEls[i]?.setAttribute("visibility",visible.has(e.a)&&visible.has(e.b)?"visible":"hidden"));shown=n;
 }
 function render(next:Snapshot,initial=false){
  if(!initial&&JSON.stringify(next)===JSON.stringify(snapshot))return;
  snapshot=next;graph=layout(next);items.clear();links.replaceChildren();dots.replaceChildren();overlay.replaceChildren();
  // Always preserve root, categories and canon links; thin dense secondary edges only.
  const essential=graph.edges.filter(e=>e.kind==="category"||e.kind==="chronology"||e.a.startsWith("canon:")||e.kind==="draft");
  const essentialSet=new Set(essential);const secondary=graph.edges.filter(e=>!essentialSet.has(e));
  drawnEdges=essential.concat(secondary.slice(0,Math.max(0,10000-essential.length)));
  edgeEls=drawnEdges.map(e=>{const b=graph.byKey.get(e.b);return el("line",{stroke:e.kind==="category"&&e.a==="root"?"#bbb2ab":colors[(b?.group??-1)+1],"stroke-opacity":e.kind==="category"?.22:e.kind==="keywords"?.12:Math.min(.65,.23+.07*(e.shared||0)),"stroke-width":e.a==="root"?.55:Math.min(1.25,.36+.12*(e.shared||0)),...(e.kind==="draft"?{"stroke-dasharray":"2 3"}:{})},links)});
  const dense=graph.nodes.length>800;
  for(const n of graph.nodes){
   const g=el("g",{class:"node","data-key":n.key},dots),col=colors[n.group+1];items.set(n.key,g);
   const major=n.key==="root"||n.key.startsWith("hub:")||n.kind==="fictional_chapter";
   if(!dense||major)el("circle",{r:n.r*6.2,fill:"url(#glow"+(n.group+1)+")"},g);
   if(n.kind==="draft"){el("circle",{r:n.r*2,fill:"none",stroke:col,"stroke-dasharray":"2 2","stroke-width":.8},g)}
   else{el("circle",{r:n.r*.9,fill:col,opacity:.74},g);if(!dense||major)el("circle",{r:n.r*.36,fill:"#fff9eb"},g)}
   if(!dense||major)el("circle",{r:Math.max(4,n.r*2.5),fill:"transparent"},g);
   if(n.key==="root"||n.key.startsWith("hub:")){
    el("path",{d:"M-11 0H11M0 -11V11M-5 -5L5 5M-5 5L5 -5",stroke:col,"stroke-width":.55,opacity:.75},g);
    const t=el("text",{x:0,y:14,"text-anchor":"middle",fill:col,class:"label"},g);t.textContent=n.label;
   }
   const title=el("title",{},g);title.textContent=n.label;
  }
  desired=baseFit();if(initial||motion.matches)fit=desired;
  if(!graph.byKey.has(active))active="";
  replayAt=0;shown=graph.nodes.length;place();status();invalidate();
 }
 function clearActivity(){works.clear();for(const p of particles.values())p.group.remove();particles.clear();status();invalidate()}
 function setActivity(next:Activity){
  if(next.session!==session){clearActivity();seen.clear();session=next.session}
  const now=performance.now(),incoming=new Set(next.active.map(a=>a.id));
  for(const [id,a] of works)if(!a.terminal&&!incoming.has(id))works.delete(id);
  for(const item of next.active){const old=works.get(item.id);works.set(item.id,{item,started:old&&old.item.stage===item.stage?old.started:now,terminal:false})}
  for(const item of next.recent)if(!seen.has(item.id)){seen.add(item.id);works.set(item.id,{item,started:now,terminal:true})}
  while(seen.size>256)seen.delete(seen.values().next().value!);
  status();invalidate();
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
   p.line.setAttribute("stroke",route.color);p.line.setAttribute("opacity",String(.28*fade));
   p.dots.forEach((d,i)=>{const t=motion.matches?.5:a.terminal?Math.min(1,elapsed/1000+i*.025):((elapsed/1500+i/6)%1);const q=pointOn(route.points,t);d.setAttribute("cx",String(q.x*s));d.setAttribute("cy",String(q.y*s));d.setAttribute("fill",route.color);d.setAttribute("opacity",String((motion.matches&&i>0?0:.9)*fade))});
   // The validating stage is the actual local schema/canon check, not model introspection.
   if(a.item.stage==="validating"){for(const key of ["canon:5","canon:6","canon:13"])items.get(key)?.setAttribute("opacity",String(.72+.28*(motion.matches?1:Math.sin(now/100)**2)))}
  }
  if(![...works.values()].some(a=>a.item.stage==="validating"))for(const key of ["canon:5","canon:6","canon:13"])items.get(key)?.removeAttribute("opacity");
  for(const [id,p] of particles)if(!works.has(id)){p.group.remove();particles.delete(id)}
 }
 function frame(now:number){
  raf=0;const dt=Math.max(0,Math.min(60,now-last));last=now;
  if(replayAt){const n=motion.matches?graph.nodes.length:Math.min(graph.nodes.length,1+Math.floor((now-replayAt)/Math.max(22,Math.min(245,30000/Math.max(1,graph.nodes.length-1)))));if(n!==shown)reveal(n);if(n===graph.nodes.length){replayAt=0;status()}}
  const k=motion.matches?1:1-Math.exp(-dt/200);fit+=(desired-fit)*k;if(Math.abs(desired-fit)<.001)fit=desired;
  world.setAttribute("transform","translate("+(w*.5+panX)+" "+(h*.39+panY)+") scale("+(zoom*fit)+")");
  drawActivity(now);
  if(replayAt||fit!==desired||[...works.values()].some(a=>a.terminal||!motion.matches))invalidate();
 }
 const observer=new ResizeObserver(resize);observer.observe(svg);resize();render(snapshot,true);
 function visibility(){if(document.hidden){cancelAnimationFrame(raf);raf=0;clearActivity()}else{last=performance.now();invalidate()}}
 document.addEventListener("visibilitychange",visibility);
 svg.addEventListener("wheel",e=>{e.preventDefault();zoom=clamp(zoom*Math.exp(-e.deltaY*.001),.35,8);invalidate()},{passive:false});
 svg.addEventListener("pointerdown",e=>{if(e.button===0)drag={x:e.clientX,y:e.clientY,moved:false}});
 svg.addEventListener("pointermove",e=>{if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>2){drag.moved=true;if(!svg.hasPointerCapture(e.pointerId))svg.setPointerCapture(e.pointerId)}if(drag.moved){panX+=dx;panY+=dy;invalidate()}drag.x=e.clientX;drag.y=e.clientY});
 svg.addEventListener("pointerup",e=>{if(!drag?.moved){const key=(e.target as Element).closest("[data-key]")?.getAttribute("data-key");if(key&&graph.byKey.has(key)){active=key;redrawSelection();info.textContent=graph.byKey.get(key).label}}drag=null});
 for(const name of ["pointercancel","lostpointercapture"])svg.addEventListener(name,()=>{drag=null});
 return {render,setActivity,clearActivity,replay(){zoom=1;panX=panY=0;active="";redrawSelection();if(graph.nodes.length<=1){status();invalidate();return}replayAt=performance.now();reveal(1);invalidate()},dispose(){disposed=true;cancelAnimationFrame(raf);observer.disconnect();document.removeEventListener("visibilitychange",visibility);clearActivity()}};
}
