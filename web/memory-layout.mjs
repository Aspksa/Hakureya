// Stable hex-lattice slots and separated constellation envelopes, all SVG.
export const palette=["#e8ce72","#f5a064","#ed657d","#df6e9e","#e8c6ed"];
export const categories=["Запросы","Знания","Ответы","Опыт","Биография"];
const centers=[[-.026,-.28],[.082,-.042],[-.078,.182],[.069,.408],[.36,-.13]];
const STEP=.026;
// Slot zero is the first cell of ring 1; the hub owns the origin.
export function cell(slot){
 const n=Math.max(0,Math.floor(slot))+1;
 const ring=Math.ceil((Math.sqrt(12*n+9)-3)/6);
 const base=1+3*(ring-1)*ring;
 const offset=n-base, side=Math.floor(offset/ring), k=offset%ring;
 const corners=[[ring,0],[0,ring],[-ring,ring],[-ring,0],[0,-ring],[ring,-ring],[ring,0]];
 const a=corners[side],b=corners[side+1],q=a[0]+(b[0]-a[0])*k/ring,r=a[1]+(b[1]-a[1])*k/ring;
 return {x:STEP*(q+r*.5),y:STEP*Math.sqrt(3)*r*.5};
}
export function detailLevel(count,zoom){return count<800||zoom>=2.4?2:zoom>=1.25?1:0}
export function layout(snapshot){
 const nodes=[{key:"root",group:-1,x:0,y:0,r:3.6,label:"hakureya"}],edges=[],byKey=new Map([[ "root",nodes[0] ]]);
 const count=categories.map(()=>0),radius=categories.map(()=>.035),valid=(Array.isArray(snapshot.records)?snapshot.records:[]).filter(n=>Number.isInteger(n.group)&&n.group>=0&&n.group<categories.length&&typeof n.key==="string");
 const occupied=categories.map(()=>new Set());
 const bio=[],heart=[],shadow=[];
 const shadowTopics=["court","visits","suitors","threat","mask","power"];
 const heartTopics=["meeting","tenderness","trust","memory","letters","adventure"];
 for(const n of valid){
  if(byKey.has(n.key))continue;
  const g=n.group;
  if(!count[g]){const key="hub:"+g,hub={key,group:g,x:0,y:0,r:3.5,label:categories[g]};nodes.push(hub);byKey.set(key,hub);edges.push({a:"root",b:key,kind:"category"})}
  let slot=Number.isSafeInteger(n.slot)&&n.slot>=0?n.slot:count[g];
  while(occupied[g].has(slot))slot++;
  occupied[g].add(slot);count[g]++;
  const p=cell(slot);
  const nested=g===4&&["past","meeting","love","future"].includes(n.sector)&&Number.isSafeInteger(n.book)&&n.book>=0&&n.book<=1000000&&Number.isSafeInteger(n.chapter_slot)&&n.chapter_slot>=-1&&n.chapter_slot<=12;
  const heartNode=g===4&&(n.heart_topic==="root"||heartTopics.includes(n.heart_topic))&&Number.isSafeInteger(n.heart_slot)&&n.heart_slot>=-1;
  const shadowNode=g===4&&(n.shadow_topic==="root"||shadowTopics.includes(n.shadow_topic))&&Number.isSafeInteger(n.shadow_slot)&&n.shadow_slot>=-1&&n.shadow_slot<=1000000;
  if(!nested&&!heartNode&&!shadowNode)radius[g]=Math.max(radius[g],Math.hypot(p.x,p.y)+.035);
  const r=n.kind==="shadow_root"?4.2:n.kind==="shadow_topic"?3.1:n.kind==="shadow_event"?1.8:n.kind==="heart_root"?4.2:n.kind==="heart_topic"?3.1:n.kind==="heart_moment"?1.8:n.kind==="epoch"?3.6:n.kind==="book_segment"?3:n.kind==="fictional_chapter"?2.7:n.kind==="draft"?2.1:n.kind==="theme"?1.7:1.5;
  const item={...n,slot,x:p.x,y:p.y,r};nodes.push(item);byKey.set(item.key,item);
  if(nested)bio.push(item);
  if(heartNode)heart.push(item);
  if(shadowNode)shadow.push(item);
  edges.push({a:"hub:"+g,b:item.key,kind:"category"});
 }
 // Four epoch galaxies surround the permanent biography hub. Each volume occupies a hex cell;
 // chapters retain their publication slot inside that volume, independent of insertion/eviction.
 if(bio.length){
  const sectors=["past","meeting","love","future"], extent=[.08,.08,.08,.08];
  for(const n of bio){const i=sectors.indexOf(n.sector);const book=n.book===0?{x:0,y:0}:cell(n.book-1);const local=n.book===0||n.chapter_slot===-1?{x:0,y:0}:cell(n.chapter_slot);n.x=book.x*7+local.x;n.y=book.y*7+local.y;extent[i]=Math.max(extent[i],Math.hypot(n.x,n.y)+.06)}
  const central=radius[4];const spacing=Math.max(central,...extent)+.10;
  for(const n of bio){const i=sectors.indexOf(n.sector),angle=-Math.PI/2+i*Math.PI/2;const distance=central+extent[i]+spacing; n.x+=Math.cos(angle)*distance;n.y+=Math.sin(angle)*distance;radius[4]=Math.max(radius[4],Math.hypot(n.x,n.y)+.04)}
 }
 // Dedicated Heart constellation inside biography, outside existing epoch envelopes.
 if(heart.length){
  const ext=heartTopics.map(()=>.045);
  for(const n of heart){const i=heartTopics.indexOf(n.heart_topic);if(i<0||n.heart_slot<0){n.x=0;n.y=0;continue}
   const p=cell(n.heart_slot);n.x=p.x;n.y=p.y;ext[i]=Math.max(ext[i],Math.hypot(p.x,p.y)+.045)}
  const ring=2*Math.max(...ext)+.09;
  const area=ring+Math.max(...ext)+.045;
  const distance=radius[4]+area+.10;
  const cx=distance/Math.SQRT2,cy=distance/Math.SQRT2;
  for(const n of heart){const i=heartTopics.indexOf(n.heart_topic),angle=-Math.PI/2+i*Math.PI/3;
   n.x+=cx+(i>=0?Math.cos(angle)*ring:0);n.y+=cy+(i>=0?Math.sin(angle)*ring:0)}
  radius[4]=Math.max(radius[4],distance+area);
 }
 // Court intrigue occupies a separate envelope from Heart and the four epochs.
 if(shadow.length){
  const ext=shadowTopics.map(()=>.045);
  for(const n of shadow){const i=shadowTopics.indexOf(n.shadow_topic);if(i<0||n.shadow_slot<0){n.x=0;n.y=0;continue}
   const p=cell(n.shadow_slot);n.x=p.x;n.y=p.y;ext[i]=Math.max(ext[i],Math.hypot(p.x,p.y)+.045)}
  const ring=2*Math.max(...ext)+.09,area=ring+Math.max(...ext)+.045;
  const distance=radius[4]+area+.10,cx=distance/Math.SQRT2,cy=-distance/Math.SQRT2;
  for(const n of shadow){const i=shadowTopics.indexOf(n.shadow_topic),angle=-Math.PI/2+i*Math.PI/3;
   n.x+=cx+(i>=0?Math.cos(angle)*ring:0);n.y+=cy+(i>=0?Math.sin(angle)*ring:0)}
  radius[4]=Math.max(radius[4],distance+area);
 }
 let spread=1;
 for(let i=0;i<centers.length;i++){
  if(!count[i])continue;
  spread=Math.max(spread,(radius[i]+.05)/Math.hypot(...centers[i]));
  for(let j=0;j<i;j++)if(count[j])spread=Math.max(spread,(radius[i]+radius[j]+.035)/Math.hypot(centers[i][0]-centers[j][0],centers[i][1]-centers[j][1]));
 }
 for(const n of nodes)if(n.group>=0){n.x+=centers[n.group][0]*spread;n.y+=centers[n.group][1]*spread}
 const seen=new Set(edges.map(e=>e.a+"|"+e.b+"|"+e.kind));
 for(const e of snapshot.edges||[]){const k=e.a+"|"+e.b+"|"+e.kind;if(byKey.has(e.a)&&byKey.has(e.b)&&e.a!==e.b&&!seen.has(k)){edges.push(e);seen.add(k)}}
 const extent=Math.max(.45,...nodes.map(n=>Math.max(Math.abs(n.x)*1.35,Math.abs(n.y))));
 return {nodes,edges,byKey,extent,spread,radius};
}
