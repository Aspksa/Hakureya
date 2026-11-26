// No synthetic work events. A boundary coordinate represents transport, never a Cloud node.
export function flowPaths(item, graph){
 const root=graph.byKey.get("root");
 const source=graph.byKey.get(item.source)||graph.byKey.get(item.kind==="chronicle"?"hub:3":"hub:0")||root;
 const target=graph.byKey.get(item.target)||graph.byKey.get(item.kind==="chronicle"?"hub:4":"hub:2")||root;
 const boundary={x:-Math.max(.34,graph.extent*.72),y:item.kind==="chronicle"?.10:-.10};
 const kind=item.kind==="chronicle"?"#e8c6ed":"#e8ce72";
 if(item.stage==="request"||item.stage==="waiting")return [{points:[source,root,boundary],color:kind}];
 if(item.stage==="received"||item.stage==="validating"||item.stage==="done")return [{points:[boundary,root,target],color:"#f7ede4"}];
 if(item.stage==="error")return [{points:[boundary,root],color:"#ed657d"}];
 if(item.stage==="discarded")return [{points:[boundary,root],color:"#b7aaa4"}];
 return [];
}
export function pointOn(points,t){
 const lengths=points.slice(1).map((p,i)=>Math.hypot(p.x-points[i].x,p.y-points[i].y));
 const total=lengths.reduce((a,b)=>a+b,0);
 let d=Math.max(0,Math.min(1,t))*total;
 for(let i=0;i<lengths.length;i++){const l=lengths[i];if(l>0&&(d<=l||i===lengths.length-1)){const f=Math.min(1,d/l);return {x:points[i].x+(points[i+1].x-points[i].x)*f,y:points[i].y+(points[i+1].y-points[i].y)*f}}d-=l}
 return points[points.length-1];
}
