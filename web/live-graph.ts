import {layout,palette} from "./memory-layout.mjs";
import {rng,clamp} from "./geometry.mjs";
type Snapshot={records:any[],edges:any[],total:number,limited:boolean};
export function mountGraph(svg:SVGSVGElement,info:HTMLElement){
 const ns="http://www.w3.org/2000/svg";
 function el<K extends keyof SVGElementTagNameMap>(tag:K,attrs:Record<string,string|number>={},parent:SVGElement=svg){const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,String(v));parent.append(e);return e}
 const defs=el("defs"),colors=["#fffdf4",...palette];
 colors.forEach((c,i)=>{const g=el("radialGradient",{id:"glow"+i},defs);for(const [offset,opacity] of [[0,.92],[.11,.65],[.25,.26],[.5,.08],[1,0]])el("stop",{offset,"stop-color":c,"stop-opacity":opacity},g)});
 const stars=el("g",{"pointer-events":"none"}),world=el("g"),links=el("g",{"pointer-events":"none"},world),dots=el("g",{},world),overlay=el("g",{"pointer-events":"none"},world);
 const random=rng(920), starData=Array.from({length:2200},()=>({x:random(),y:random(),r:.12+random()**7*.72,o:.035+random()**2*.34}));
 const starEls=starData.map((p,i)=>el("circle",{r:p.r,fill:i%13===0?"#d8b9a1":"#e1dcd8",opacity:p.o},stars));
 let snapshot:Snapshot={records:[],edges:[],total:0,limited:false},graph=layout(snapshot),w=1,h=1,s=1,zoom=1,panX=0,panY=0,fit=1,desired=1,focusX=0,focusY=0,targetX=0,targetY=0,active="",busy=false,drag:null|{x:number,y:number,moved:boolean}=null,items=new Map<string,SVGGElement>(),edgeEls:SVGLineElement[]=[],replayAt=0,shown=0,last=performance.now(),raf=0;
 const reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
 function baseFit(){return Math.min(1,.45/graph.extent)}
 function status(){info.textContent=snapshot.total+" записей · "+graph.edges.length+" связей"+(snapshot.limited?" · последние 5000":"")}
 function redrawSelection(){
  overlay.replaceChildren();const n=graph.byKey.get(busy?"root":active);if(!n)return;
  const g=el("g",{transform:"translate("+n.x*s+" "+n.y*s+")"},overlay),color=colors[n.group+1];
  el("circle",{r:Math.max(6,n.r*3.1),fill:"none",stroke:color,"stroke-width":.9},g);
  el("circle",{r:Math.max(8,n.r*4),fill:"none",stroke:color,"stroke-width":1,class:"pulse"},g);
  if(n.label){const title=String(n.label).slice(0,54);const label=el("text",{x:13,y:-7,fill:color,class:"active-label"},g);label.textContent=title;const b=label.getBBox();const rect=el("rect",{x:b.x-4,y:b.y-2,width:b.width+8,height:b.height+4,rx:2,fill:"#110b0e",stroke:color,"stroke-opacity":.72,"stroke-width":.65},g);g.insertBefore(rect,label)}
 }
 function place(){
  for(const n of graph.nodes){items.get(n.key)?.setAttribute("transform","translate("+n.x*s+" "+n.y*s+")")}
  graph.edges.forEach((e,i)=>{const a=graph.byKey.get(e.a),b=graph.byKey.get(e.b),line=edgeEls[i];if(!line||!a||!b)return;for(const [k,v] of Object.entries({x1:a.x*s,y1:a.y*s,x2:b.x*s,y2:b.y*s}))line.setAttribute(k,String(v))});
  redrawSelection();
 }
 function resize(){w=Math.max(1,svg.clientWidth);h=Math.max(1,svg.clientHeight);s=Math.min(w*1.52,h*.91);svg.setAttribute("viewBox","0 0 "+w+" "+h);starEls.forEach((e,i)=>{e.setAttribute("cx",String(starData[i].x*w));e.setAttribute("cy",String(starData[i].y*h))});place()}
 function reveal(n:number){
  const visible=new Set(graph.nodes.slice(0,n).map(x=>x.key));graph.nodes.forEach(x=>items.get(x.key)?.setAttribute("visibility",visible.has(x.key)?"visible":"hidden"));graph.edges.forEach((e,i)=>edgeEls[i]?.setAttribute("visibility",visible.has(e.a)&&visible.has(e.b)?"visible":"hidden"));shown=n;
 }
 function render(next:Snapshot,initial=false){
  const previous=new Set(snapshot.records.map(n=>n.key)),added=next.records.filter(n=>!previous.has(n.key));
  if(!initial&&JSON.stringify(next)===JSON.stringify(snapshot))return;
  snapshot=next;graph=layout(next);items.clear();links.replaceChildren();dots.replaceChildren();overlay.replaceChildren();
  edgeEls=graph.edges.map(e=>{const b=graph.byKey.get(e.b);return el("line",{stroke:e.kind==="category"&&e.a==="root"?"#bbb2ab":colors[(b?.group??-1)+1],"stroke-opacity":e.kind==="category"?.22:e.kind==="keywords"?.12:.27,"stroke-width":e.a==="root"?.55:.36},links)});
  for(const n of graph.nodes){
   const g=el("g",{class:"node","data-key":n.key},dots),col=colors[n.group+1];items.set(n.key,g);
   el("circle",{r:n.r*6.2,fill:"url(#glow"+(n.group+1)+")"},g);
   el("circle",{r:Math.max(4,n.r*2.5),fill:"transparent"},g);
   el("circle",{r:n.r*.9,fill:col,opacity:.74},g);el("circle",{r:n.r*.36,fill:"#fff9eb"},g);
   if(n.key==="root"||n.key.startsWith("hub:")){
    el("path",{d:"M-11 0H11M0 -11V11M-5 -5L5 5M-5 5L5 -5",stroke:col,"stroke-width":.55,opacity:.75},g);
    const t=el("text",{x:0,y:14,"text-anchor":"middle",fill:col,class:"label"},g);t.textContent=n.label;
   }
   const title=el("title",{},g);title.textContent=n.label;
   g.addEventListener("click",()=>{if(!drag?.moved){active=n.key;redrawSelection();info.textContent=n.label||n.key}})
  }
  desired=baseFit();if(initial)fit=desired;
  if(!initial&&added.length){active=added[added.length-1].key;const n=graph.byKey.get(active);if(n&&!reduce){focusX=n.x*s*.18;focusY=n.y*s*.18;fit=Math.min(desired*1.3,1.6)}}
  if(!graph.byKey.has(active))active="";
  replayAt=0;shown=graph.nodes.length;place();status();
 }
 function frame(now:number){
  const dt=Math.min(60,now-last);last=now;
  if(replayAt){const n=reduce?graph.nodes.length:Math.min(graph.nodes.length,1+Math.floor((now-replayAt)/Math.max(22,Math.min(245,30000/Math.max(1,graph.nodes.length-1)))));
   if(n!==shown){reveal(n);active=graph.nodes[n-1].key;redrawSelection()}
   desired=baseFit()*(1+1.65*(1-n/graph.nodes.length));if(n===graph.nodes.length){replayAt=0;desired=baseFit();active="";redrawSelection();status()}
  }
  const k=reduce?1:1-Math.exp(-dt/340);fit+=(desired-fit)*k;focusX+=(targetX-focusX)*k;focusY+=(targetY-focusY)*k;
  world.setAttribute("transform","translate("+(w*.5+panX-focusX)+" "+(h*.39+panY-focusY)+") scale("+(zoom*fit)+")");
  raf=requestAnimationFrame(frame)
 }
 new ResizeObserver(resize).observe(svg);resize();render(snapshot,true);raf=requestAnimationFrame(frame);
 svg.addEventListener("wheel",e=>{e.preventDefault();zoom=clamp(zoom*Math.exp(-e.deltaY*.001),.35,8)},{passive:false});
 svg.addEventListener("pointerdown",e=>{if(e.button===0)drag={x:e.clientX,y:e.clientY,moved:false}});
 svg.addEventListener("pointermove",e=>{if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>2){drag.moved=true;if(!svg.hasPointerCapture(e.pointerId))svg.setPointerCapture(e.pointerId)}if(drag.moved){panX+=dx;panY+=dy}drag.x=e.clientX;drag.y=e.clientY});
 for(const name of ["pointerup","pointercancel","lostpointercapture"])svg.addEventListener(name,()=>{drag=null});
 return {render,setBusy(value:boolean){busy=value;redrawSelection()},replay(){zoom=1;panX=panY=0;active="";if(graph.nodes.length<=1){status();return}replayAt=performance.now();reveal(1);redrawSelection()},dispose(){cancelAnimationFrame(raf)}};
}
