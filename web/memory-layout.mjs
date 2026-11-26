// Stable hex-lattice slots and separated constellation envelopes, all SVG.
export const palette=["#e8ce72","#f5a064","#ed657d","#df6e9e","#e8c6ed"];
export const categories=["Запросы","Знания","Ответы","Опыт","Биография"];

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
// Pack a small number of circular envelopes without a cumulative radial staircase.
// Local lattice positions never change; only constellation centers can move.
export function packCircles(disks,core=.09,gap=.045){
 const placed=[{key:"core",x:0,y:0,r:core}],result=new Map();
 for(const disk of [...disks].sort((a,b)=>b.r-a.r)){
  const r=disk.r;
  let best=null,bestScore=Infinity;
  for(const anchor of placed){
   for(let i=0;i<72;i++){
    const a=-Math.PI/2+i*Math.PI/36,d=anchor.r+r+gap;
    const x=anchor.x+Math.cos(a)*d,y=anchor.y+Math.sin(a)*d;
    if(placed.some(p=>Math.hypot(x-p.x,y-p.y)<r+p.r+gap-1e-8))continue;
    const all=[...placed,{x,y,r}];
    const left=Math.min(...all.map(p=>p.x-p.r)),right=Math.max(...all.map(p=>p.x+p.r));
    const top=Math.min(...all.map(p=>p.y-p.r)),bottom=Math.max(...all.map(p=>p.y+p.r));
    const width=right-left,height=bottom-top;
    const score=Math.max(width/1.5,height)+.12*(width+height)+.03*Math.hypot(x,y);
    if(score<bestScore){bestScore=score;best={key:disk.key,x,y,r}}
   }
  }
  if(!best){
   const x=Math.max(...placed.map(p=>p.x+p.r))+gap+r;
   best={key:disk.key,x,y:0,r};
  }
  placed.push(best);result.set(disk.key,best);
 }
 return result;
}
export function graphBounds(nodes){
 let left=0,right=0,top=0,bottom=0;
 for(const n of nodes){left=Math.min(left,n.x);right=Math.max(right,n.x);top=Math.min(top,n.y);bottom=Math.max(bottom,n.y)}
 return {left,right,top,bottom};
}
// Fit the actual bounds to the available viewport; glyphs are separately screen-sized.
export function cameraFrame(bounds,width,height){
 const w=Math.max(1,width),h=Math.max(1,height),pad=Math.min(56,w*.12,h*.12);
 const bw=Math.max(.18,bounds.right-bounds.left),bh=Math.max(.18,bounds.bottom-bounds.top);
 const scale=Math.min(1200,Math.max(1,(w-2*pad))/bw,Math.max(1,(h-2*pad))/bh);
 return {scale,cx:(bounds.left+bounds.right)/2,cy:(bounds.top+bounds.bottom)/2,pad};
}
export function detailLevel(count,zoom){return count<800||zoom>=2.4?2:zoom>=1.25?1:0}
export function layout(snapshot){
 const nodes=[{key:"root",kind:"root",group:-1,x:0,y:0,r:9,label:"HAKUREYA"}],edges=[],byKey=new Map([[ "root",nodes[0] ]]);
 const count=categories.map(()=>0),radius=categories.map(()=>.035),valid=(Array.isArray(snapshot.records)?snapshot.records:[]).filter(n=>Number.isInteger(n.group)&&n.group>=0&&n.group<categories.length&&typeof n.key==="string").map(n=>({...n}));
 const occupied=categories.map(()=>new Set());
 const bio=[],heart=[],shadow=[],guardians=[],destiny=[],immortal=[],infinite=[],areas=[];
 const destinyTopics=["love","power","guardians","court","worlds","cast","growth",...["iori","lian","kaen","meixiu","jun","renho","setsuna","nari","kagari","orum"].map(k=>"actor:"+k),...Array.from({length:9},(_,i)=>"realm:"+(i+1))];
 const guardianActors=["reika","seirana","mikage","tokihana","akatsuki","shiori","yumeka","meirin","amatsuka"];
 const shadowTopics=["court","visits","suitors","threat","mask","power"];
 const heartTopics=["meeting","tenderness","trust","memory","letters","adventure"];
 // Attach new facts to the existing Heart and guardian lattices; keep the original hubs.
 const infiniteGroups=new Set(valid.map(n=>n.infinite_group).filter(x=>typeof x==="string"));
 const nextGuardian=new Map(),nextHeart=new Map();
 for(const n of valid){
  if(guardianActors.includes(n.guardian_actor)&&Number.isSafeInteger(n.guardian_slot))nextGuardian.set(n.guardian_actor,Math.max(nextGuardian.get(n.guardian_actor)||0,n.guardian_slot+1));
  if(heartTopics.includes(n.heart_topic)&&Number.isSafeInteger(n.heart_slot))nextHeart.set(n.heart_topic,Math.max(nextHeart.get(n.heart_topic)||0,n.heart_slot+1));
 }
 for(const n of [...valid].sort((a,b)=>a.key.localeCompare(b.key))){
  const group=n.infinite_group;
  if(typeof group==="string"&&group.startsWith("guardian:")&&guardianActors.includes(group.slice(9))){
   const actor=group.slice(9),slot=nextGuardian.get(actor)||0;
   n.guardian_actor=actor;n.guardian_slot=slot;nextGuardian.set(actor,slot+1);delete n.infinite_group;
  }else if(group==="heart:root"){
   const topic="tenderness",slot=nextHeart.get(topic)||0;
   n.heart_topic=topic;n.heart_slot=slot;nextHeart.set(topic,slot+1);delete n.infinite_group;
  }else if(n.group===4&&(infiniteGroups.has(n.key)||n.key==="character:hero"))n.infinite_group=n.key;
 }
 for(const n of valid){
  if(byKey.has(n.key))continue;
  const g=n.group;
  if(!count[g]){const key="hub:"+g,hub={key,kind:"hub",group:g,x:0,y:0,r:5.2,label:categories[g]};nodes.push(hub);byKey.set(key,hub);edges.push({a:"root",b:key,kind:"category"})}
  let slot=Number.isSafeInteger(n.slot)&&n.slot>=0?n.slot:count[g];
  while(occupied[g].has(slot))slot++;
  occupied[g].add(slot);count[g]++;
  const p=cell(slot);
  const nested=g===4&&["past","meeting","love","future"].includes(n.sector)&&Number.isSafeInteger(n.book)&&n.book>=0&&n.book<=1000000&&Number.isSafeInteger(n.chapter_slot)&&n.chapter_slot>=-1&&n.chapter_slot<=12;
  const heartNode=g===4&&(n.heart_topic==="root"||heartTopics.includes(n.heart_topic))&&Number.isSafeInteger(n.heart_slot)&&n.heart_slot>=-1;
  const shadowNode=g===4&&(n.shadow_topic==="root"||shadowTopics.includes(n.shadow_topic))&&Number.isSafeInteger(n.shadow_slot)&&n.shadow_slot>=-1&&n.shadow_slot<=1000000;
  const guardianNode=g===4&&(n.guardian_actor==="root"||guardianActors.includes(n.guardian_actor))&&Number.isSafeInteger(n.guardian_slot)&&n.guardian_slot>=-1&&n.guardian_slot<=1000000;
  const destinyNode=g===4&&(n.destiny_topic==="root"||destinyTopics.includes(n.destiny_topic))&&Number.isSafeInteger(n.destiny_slot)&&n.destiny_slot>=-1&&n.destiny_slot<=1000000;
  const immortalNode=g===4&&Number.isSafeInteger(n.immortal_slot)&&n.immortal_slot>=-1&&n.immortal_slot<=10000000;
  const infiniteNode=g===4&&typeof n.infinite_group==="string"&&!nested&&!heartNode&&!shadowNode&&!guardianNode&&!destinyNode&&!immortalNode;
  if(!nested&&!heartNode&&!shadowNode&&!guardianNode&&!destinyNode&&!immortalNode&&!infiniteNode)radius[g]=Math.max(radius[g],Math.hypot(p.x,p.y)+.035);
  const r=1.35*(n.kind==="dynasty_root"?4.2:n.kind==="dynasty_saga"?3.4:n.kind==="dynasty_mystery"?2.4:n.kind==="dynasty_event"?2.1:n.kind==="lit_database"?4.6:n.kind==="lit_brain"?3.3:n.kind==="lit_character"?3.2:n.kind==="lit_world"?3.2:n.kind==="lit_power"?2.4:n.key==="character:hero"?4.2:n.kind==="infinite_root"?3.8:n.kind==="infinite_character"?3:n.kind==="infinite_stage"?2.8:n.kind==="infinite_hero"?2.4:n.kind==="infinite_love"?2.4:n.kind==="novel_epoch"?3.8:n.kind==="novel_chapter"?2.8:n.kind==="immortal_root"?3.8:n.kind==="immortal_saga"?3:n.kind==="immortal_stage"?2.2:n.kind==="living_root"?3.8:n.kind==="living_topic"?2.8:n.kind==="living_subject"?2.2:n.kind==="living_fact"?1.6:n.kind==="destiny_root"?4.2:n.kind==="destiny_topic"||n.kind==="destiny_character"||n.kind==="realm"?3.1:n.kind==="destiny_fact"||n.kind==="destiny_event"?1.8:n.kind==="guardian_root"?4.2:n.kind==="guardian_character"?3.1:n.kind==="guardian_memory"?1.8:n.kind==="shadow_root"?4.2:n.kind==="shadow_topic"?3.1:n.kind==="shadow_event"?1.8:n.kind==="heart_root"?4.2:n.kind==="heart_topic"?3.1:n.kind==="heart_moment"?1.8:n.kind==="epoch"?3.6:n.kind==="book_segment"?3:n.kind==="fictional_chapter"?2.7:n.kind==="draft"?2.1:n.kind==="theme"?1.7:1.5)*(1+Math.min(.3,Math.max(0,Number(n.dynasty_count)||0)*.025));
  const item={...n,kind:typeof n.kind==="string"?n.kind:"memory",label:typeof n.label==="string"?n.label:n.key,slot,x:p.x,y:p.y,r};nodes.push(item);byKey.set(item.key,item);
  if(nested)bio.push(item);
  if(heartNode)heart.push(item);
  if(shadowNode)shadow.push(item);
  if(guardianNode)guardians.push(item);
  if(destinyNode)destiny.push(item);
  if(immortalNode)immortal.push(item);
  if(infiniteNode)infinite.push(item);
  edges.push({a:"hub:"+g,b:item.key,kind:"category"});
 }
 // Four epoch galaxies surround the permanent biography hub. Each volume occupies a hex cell;
 // chapters retain their publication slot inside that volume, independent of insertion/eviction.
 if(bio.length){
  const sectors=["past","meeting","love","future"], extent=[.08,.08,.08,.08];
  for(const n of bio){const i=sectors.indexOf(n.sector);const book=n.book===0?{x:0,y:0}:cell(n.book-1);const local=n.book===0||n.chapter_slot===-1?{x:0,y:0}:cell(n.chapter_slot);n.x=book.x*7+local.x;n.y=book.y*7+local.y;extent[i]=Math.max(extent[i],Math.hypot(n.x,n.y)+.06)}
  for(let i=0;i<sectors.length;i++){const members=bio.filter(n=>n.sector===sectors[i]);if(members.length)areas.push({key:"epoch:"+sectors[i],r:extent[i],members})}
 }
 // Dedicated Heart constellation inside biography, outside existing epoch envelopes.
 if(heart.length){
  const ext=heartTopics.map(()=>.045);
  for(const n of heart){const i=heartTopics.indexOf(n.heart_topic);if(i<0||n.heart_slot<0){n.x=0;n.y=0;continue}
   const p=cell(n.heart_slot);n.x=p.x;n.y=p.y;ext[i]=Math.max(ext[i],Math.hypot(p.x,p.y)+.045)}
  const ring=2*Math.max(...ext)+.09;
  const area=ring+Math.max(...ext)+.045;
  for(const n of heart){const i=heartTopics.indexOf(n.heart_topic),angle=-Math.PI/2+i*Math.PI/3;
   n.x+=i>=0?Math.cos(angle)*ring:0;n.y+=i>=0?Math.sin(angle)*ring:0}
  areas.push({key:"heart",r:area,members:heart});
 }
 // Court intrigue occupies a separate envelope from Heart and the four epochs.
 if(shadow.length){
  const ext=shadowTopics.map(()=>.045);
  for(const n of shadow){const i=shadowTopics.indexOf(n.shadow_topic);if(i<0||n.shadow_slot<0){n.x=0;n.y=0;continue}
   const p=cell(n.shadow_slot);n.x=p.x;n.y=p.y;ext[i]=Math.max(ext[i],Math.hypot(p.x,p.y)+.045)}
  const ring=2*Math.max(...ext)+.09,area=ring+Math.max(...ext)+.045;
  for(const n of shadow){const i=shadowTopics.indexOf(n.shadow_topic),angle=-Math.PI/2+i*Math.PI/3;
   n.x+=i>=0?Math.cos(angle)*ring:0;n.y+=i>=0?Math.sin(angle)*ring:0}
  areas.push({key:"shadow",r:area,members:shadow});
 }
 // Nine personal constellations, with ring radius based on the closest neighboring pair.
 if(guardians.length){
  const ext=guardianActors.map(()=>.045);
  for(const n of guardians){const i=guardianActors.indexOf(n.guardian_actor);if(i<0||n.guardian_slot<0){n.x=0;n.y=0;continue}
   const p=cell(n.guardian_slot);n.x=p.x;n.y=p.y;ext[i]=Math.max(ext[i],Math.hypot(p.x,p.y)+.045)}
  const max=Math.max(...ext),ring=(2*max+.06)/(2*Math.sin(Math.PI/9)),area=ring+max+.045;
  for(const n of guardians){const i=guardianActors.indexOf(n.guardian_actor),angle=-Math.PI/2+i*2*Math.PI/9;
   n.x+=i>=0?Math.cos(angle)*ring:0;n.y+=i>=0?Math.sin(angle)*ring:0}
  areas.push({key:"guardians",r:area,members:guardians});
 }
 // Destiny topics and introduced character groups have independent envelopes.
 if(destiny.length){
  const ext=destinyTopics.map(()=>.045);
  for(const n of destiny){const i=destinyTopics.indexOf(n.destiny_topic);if(i<0||n.destiny_slot<0){n.x=0;n.y=0;continue}
   const p=cell(n.destiny_slot);n.x=p.x;n.y=p.y;ext[i]=Math.max(ext[i],Math.hypot(p.x,p.y)+.045)}
  const max=Math.max(...ext),ring=(2*max+.06)/(2*Math.sin(Math.PI/destinyTopics.length)),area=ring+max+.045;
  for(const n of destiny){const i=destinyTopics.indexOf(n.destiny_topic),angle=-Math.PI/2+i*2*Math.PI/destinyTopics.length;
   n.x+=i>=0?Math.cos(angle)*ring:0;n.y+=i>=0?Math.sin(angle)*ring:0}
  areas.push({key:"destiny",r:area,members:destiny});
 }
 if(immortal.length){
  let area=.05;
  for(const n of immortal){const p=n.immortal_slot<0?{x:0,y:0}:cell(n.immortal_slot);n.x=p.x;n.y=p.y;area=Math.max(area,Math.hypot(p.x,p.y)+.05)}
  areas.push({key:"immortal",r:area,members:immortal});
 }
 // Character sub-constellations share a bounded hex grid of non-overlapping envelopes.
 if(infinite.length){
  const groups=new Map();
  for(const n of infinite){if(!groups.has(n.infinite_group))groups.set(n.infinite_group,[]);groups.get(n.infinite_group).push(n)}
  const clusters=[];
  for(const [key,members] of [...groups].sort((a,b)=>a[0].localeCompare(b[0]))){
   const hub=members.find(n=>n.key===key);let r=.045,i=0;
   for(const n of [...members].sort((a,b)=>a.key.localeCompare(b.key))){
    const p=n===hub?{x:0,y:0}:cell(i++);
    n.x=p.x;n.y=p.y;r=Math.max(r,Math.hypot(p.x,p.y)+.045);
   }
   clusters.push({key,members,r});
  }
  const spacing=(2*Math.max(...clusters.map(c=>c.r))+.035)/STEP;
  let area=.06;
  clusters.forEach((c,i)=>{
   const p=i===0?{x:0,y:0}:cell(i-1),x=p.x*spacing,y=p.y*spacing;
   for(const n of c.members){n.x+=x;n.y+=y}
   area=Math.max(area,Math.hypot(x,y)+c.r);
  });
  areas.push({key:"infinite",r:area,members:infinite});
 }
 const packed=packCircles(areas,radius[4],.035);
 for(const a of areas){const p=packed.get(a.key);for(const n of a.members){n.x+=p.x;n.y+=p.y}radius[4]=Math.max(radius[4],Math.hypot(p.x,p.y)+a.r)}
 const disks=count.map((c,i)=>({key:i,r:radius[i],count:c})).filter(d=>d.count);
 if(snapshot.transport)disks.push({key:"cloud",r:.085,count:1});
 const groupPositions=packCircles(disks,.10,.045);
 for(const n of nodes)if(n.group>=0){const p=groupPositions.get(n.group);n.x+=p.x;n.y+=p.y}
 if(snapshot.transport){const p=groupPositions.get("cloud"),n={key:"cloud:api",kind:"cloud_api",group:-1,x:p.x,y:p.y,r:7,label:"Cloud.ru"};nodes.push(n);byKey.set(n.key,n)}
 const spread=1;
 // A dedicated neural view: fixed symmetric positions, not global biography slots.
 if(snapshot.network){
  const positions={"lit:db":[-.60,0],"brain:plot":[-.38,-.25],"brain:characters":[-.38,.25],"brain:relations":[-.12,-.36],"brain:magic":[-.12,.36],"brain:time":[.12,-.38],"brain:memory":[.12,.38],"brain:editor":[.37,-.25],"brain:analytics":[.37,.25],"brain:twist":[.58,0],"brain:coordinator":[.12,0],"root":[-.12,0],"cloud:api":[0,.64],"hub:4":[0,-.64]};
  for(const n of nodes){const p=positions[n.key];if(p){n.x=p[0];n.y=p[1]}}
 }
 const seen=new Set(edges.map(e=>e.a+"|"+e.b+"|"+e.kind));
 for(const e of snapshot.edges||[]){const k=e.a+"|"+e.b+"|"+e.kind;if(typeof e.kind==="string"&&byKey.has(e.a)&&byKey.has(e.b)&&e.a!==e.b&&!seen.has(k)){edges.push(e);seen.add(k)}}
 const bounds=graphBounds(nodes);
 const extent=Math.max(.45,Math.abs(bounds.left),Math.abs(bounds.right),Math.abs(bounds.top),Math.abs(bounds.bottom));
 return {nodes,edges,byKey,extent,bounds,spread,radius};
}
