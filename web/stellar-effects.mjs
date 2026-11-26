// Semantic visual styles. These are presentation categories, not inferred story facts.
export const stellarPalette={core:"#fffdf4",chapter:"#f3cd76",character:"#efa66c",love:"#efa0bd",magic:"#bd9aed",world:"#91c9ef",conflict:"#f08a82",memory:"#c4b8ac"};
export function stellarKind(node){
 const k=String(node.kind||""),key=String(node.key||"");
 if(key==="root"||key==="cloud:api")return "core";
 if(/^(?:c:|canon:|book:|segment:|novel:epoch:)/.test(key)||/^(fictional_chapter|book|book_segment|epoch|novel_chapter|novel_epoch)$/.test(k))return "chapter";
 if(k==="draft")return "chapter";
 if(/love|^heart_/.test(k)||key.startsWith("heart:")||key==="arc:love")return "love";
 if(/power|magic|limit|clue|mystery|reveal/.test(k))return "magic";
 if(/world|realm|place|journey/.test(k))return "world";
 if(/conflict|rival/.test(k))return "conflict";
 if(/character|hero|family|actor/.test(k)||key.startsWith("character:"))return "character";
 return null;
}
export function stellarColor(node,fallback=stellarPalette.memory){
 const kind=stellarKind(node);return kind?stellarPalette[kind]:fallback;
}
export function edgeKey(e){return JSON.stringify([e.a,e.b,e.kind])}
export function publicationChanges(previous,next,publication){
 // New visible records are not necessarily new entities when the graph is bounded.
 // Only animate new real links attached to this publication or its new visible neighbors.
 if(!publication||!next.records.some(n=>n.key===publication.key))return {nodes:[],edges:[]};
 const oldNodes=new Set(previous.records.map(n=>n.key)),oldEdges=new Set(previous.edges.map(edgeKey));
 const newNodes=new Set(next.records.filter(n=>!oldNodes.has(n.key)).map(n=>n.key));
 const related=new Set([publication.key]);
 for(const e of next.edges)if(e.a===publication.key||e.b===publication.key)related.add(e.a===publication.key?e.b:e.a);
 const edges=next.edges.filter(e=>!oldEdges.has(edgeKey(e))&&e.kind!=="category"&&e.kind!=="keywords"&&
  (e.a===publication.key||e.b===publication.key||(related.has(e.a)&&newNodes.has(e.a))||(related.has(e.b)&&newNodes.has(e.b)))).slice(0,24);
 const nodes=[...newNodes].filter(k=>related.has(k)||edges.some(e=>e.a===k||e.b===k)).slice(0,24);
 return {nodes,edges};
}
export function smoothStep(t){const x=Math.max(0,Math.min(1,t));return x*x*(3-2*x)}
export function frameBudget(count,mean){return count>1600||mean>26?.35:count>800||mean>20?.65:1}
