// Routes show observed transport and selected context, not hidden model reasoning.
const guardColors={reika:"#dcf0ff",seirana:"#a1e7bd",mikage:"#b5a9e9",tokihana:"#dcc7ff",akatsuki:"#ed9772",shiori:"#f0d496",yumeka:"#eea8cb",meirin:"#a9d8e4",amatsuka:"#fff0d0"};
export function sourceColor(key){
 if(key.startsWith("guardian:"))return guardColors[key.slice(9)]||"#e4d8ac";
 if(key.startsWith("heart:")||key==="arc:love")return "#f2a9c9";
 if(key==="character:hero"||key.includes(":power"))return "#e7c46d";
 if(key.startsWith("book:")||key.startsWith("c:")||key.startsWith("canon:"))return "#9ec8f0";
 if(key.startsWith("shadow:")||key.startsWith("infinite:")||key.startsWith("mystery:"))return "#c0a9e8";
 return "#e8c6ed";
}
export const stageLabels={request:"Подготовка запроса",context:"Сбор литературного контекста",waiting:"Cloud.ru · ожидание ответа",received:"Ответ получен",validating:"Проверка текста",saving:"Сохранение SQLite",saved:"Черновик сохранён",published:"Глава опубликована",done:"Ответ сохранён",error:"Ошибка запроса",discarded:"Результат отброшен"};
export function flowPaths(item,graph){
 const root=graph.byKey.get("root");
 const source=graph.byKey.get(item.source)||graph.byKey.get(item.kind==="chronicle"?"hub:3":"hub:0")||root;
 const target=graph.byKey.get(item.target)||graph.byKey.get(item.kind==="chronicle"?"hub:4":"hub:2")||root;
 const cloud=graph.byKey.get("cloud:api")||{x:-Math.max(.34,graph.extent*.72),y:item.kind==="chronicle"?.10:-.10};
 const route=(points,color)=>({points,color});
 if(item.stage==="request"||item.stage==="context"){
  const keys=[...new Set([item.source,...(item.sources||[])])].slice(0,8);
  const paths=keys.filter(k=>graph.byKey.has(k)).map(k=>route([graph.byKey.get(k),root],sourceColor(k)));
  return paths.length?paths:[route([source,root],"#e8c6ed")];
 }
 if(item.stage==="waiting")return [route([root,cloud],"#91cbff")];
 if(item.stage==="received")return [route([cloud,root],"#ffe2a0")];
 if(item.stage==="validating")return [route([root,target],"#c0a9e8")];
 if(item.stage==="saving"||item.stage==="saved"||item.stage==="published"||item.stage==="done")return [route([root,target],"#f7d897")];
 if(item.stage==="error")return [route([cloud,root],"#ed657d")];
 if(item.stage==="discarded")return [route([cloud,root],"#b7aaa4")];
 return [];
}
// Consume real server stages in order, including stages that complete between polling ticks.
export function activityEvents(item,after=0){
 const events=Array.isArray(item.events)?item.events.filter(e=>Number.isSafeInteger(e.seq)&&e.seq>after&&stageLabels[e.stage]):[];
 return events.slice(-10).map(e=>({...item,stage:e.stage,target:e.target,seq:e.seq}));
}
export function pointOn(points,t){
 if(t<=0)return {x:points[0].x,y:points[0].y};
 if(t>=1){const p=points[points.length-1];return {x:p.x,y:p.y}}
 const lengths=points.slice(1).map((p,i)=>Math.hypot(p.x-points[i].x,p.y-points[i].y));
 const total=lengths.reduce((a,b)=>a+b,0);
 let d=Math.max(0,Math.min(1,t))*total;
 for(let i=0;i<lengths.length;i++){const l=lengths[i];if(l>0&&(d<=l||i===lengths.length-1)){const f=Math.min(1,d/l);return {x:points[i].x+(points[i+1].x-points[i].x)*f,y:points[i].y+(points[i+1].y-points[i].y)*f}}d-=l}
 return points[points.length-1];
}

 // Only actual published links and a real chronological book boundary may produce birth trails.
export function publicationLinks(publication,graph){
 if(!publication||!graph.byKey.has(publication.key))return [];
 const result=[],seen=new Set();
 function add(a,b,color){
  if(a===b||!graph.byKey.has(a)||!graph.byKey.has(b)||seen.has(a+"|"+b))return;
  seen.add(a+"|"+b);result.push({a,b,color});
 }
 const k=publication.key,v=publication.volume;
 add(k,publication.segment,"#e7c46d");
 if(publication.first&&v>1)add("book:"+(v-1),"book:"+v,"#9ec8f0");
 if(publication.details===false)return result;
 const linked=new Set([k]);
 for(const e of graph.edges)if(e.a===k||e.b===k){
  if(/(?:source|event|character|cause|relationship|story_continuation|cross_volume)/.test(e.kind)){
   const other=e.a===k?e.b:e.a;linked.add(other);
   add(k,other,e.kind.includes("cause")||e.kind.includes("cross_volume")?"#9ec8f0":sourceColor(other));
  }
 }
 for(const e of graph.edges)if((linked.has(e.a)||linked.has(e.b))&&e.kind==="infinite_cross_volume")add(e.a,e.b,"#9ec8f0");
 return result.slice(0,10);
}
