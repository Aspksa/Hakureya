import {rng} from "./geometry.mjs";
// Relative cluster centers measured from the supplied late reference frame.
// The original source and exact font are unavailable.
export const palette=["#e8ce72","#f5a064","#ed657d","#df6e9e"];
export const categories=["Запросы","Знания","Ответы","Опыт"];
const centers=[[-.026,-.28],[.082,-.042],[-.078,.182],[.069,.408]];
export function layout(snapshot){
 const nodes=[{key:"root",group:-1,x:0,y:0,r:3.6,label:"hakureya"}],edges=[],byKey=new Map([["root",nodes[0]]]);
 const count=[0,0,0,0];const list=Array.isArray(snapshot.records)?snapshot.records:[];
 const valid=list.filter(n=>Number.isInteger(n.group)&&n.group>=0&&n.group<4&&typeof n.key==="string");
 for(const n of valid){if(!count[n.group]){const g=n.group,key="hub:"+g,hub={key,group:g,x:centers[g][0],y:centers[g][1],r:3.5,label:categories[g]};nodes.push(hub);byKey.set(key,hub);edges.push({a:"root",b:key,kind:"category"})}const i=count[n.group]++,g=n.group;let seed=0;for(const c of n.key)seed=(Math.imul(seed,31)+c.charCodeAt(0))|0;const random=rng(seed),angle=i*2.399963+random()*.16,d=.019+Math.sqrt(i)*.011;const item={...n,x:centers[g][0]+Math.cos(angle)*d,y:centers[g][1]+Math.sin(angle)*d*.83,r:1.2+random()*1.9};nodes.push(item);byKey.set(item.key,item);edges.push({a:"hub:"+g,b:item.key,kind:"category"})}
 for(const e of snapshot.edges||[]){if(byKey.has(e.a)&&byKey.has(e.b)&&e.a!==e.b)edges.push(e)}
 // Expand crowded groups as a whole. Positions within a group are stable.
 const radius=count.map(c=>.019+Math.sqrt(Math.max(0,c-1))*.011);
 const offset=1+Math.max(0,...radius.map(r=>r-.08))*7;
 for(const n of nodes){if(n.group>=0){n.x+=centers[n.group][0]*(offset-1);n.y+=centers[n.group][1]*(offset-1)}}
 const extent=Math.max(.45,...nodes.map(n=>Math.max(Math.abs(n.x)*1.35,Math.abs(n.y))));
 return {nodes,edges,byKey,extent};
}
