// Preserve every Unicode code point, including whitespace. Measurement is supplied by the reader.
// A saved offset is an anchor so changing font/window size cannot skip unread words.
export function measuredPages(text,fits,anchor=0){
 const chars=Array.from(text),length=chars.length,rows=[];
 const stop=Math.max(0,Math.min(length,Number.isInteger(anchor)?anchor:0));
 const range=(from,limit)=>{
  for(let start=from;start<limit;){
   // Probe only the neighborhood of a page, not the remainder of a long chapter.
   let best=start,step=256,high=Math.min(limit,start+step);
   while(fits(chars.slice(start,high).join(""),start)){
    best=high;if(high===limit)break;
    step*=2;high=Math.min(limit,start+step);
   }
   let low=best+1;
   while(low<=high){
    const mid=Math.floor((low+high)/2);
    if(fits(chars.slice(start,mid).join(""),start)){best=mid;low=mid+1}else high=mid-1;
   }
   // Very small windows still show text, with scrolling rather than a single-character page.
   if(best-start<Math.min(40,limit-start))best=Math.min(limit,start+120);
   if(best<limit&&best-start>=20){
    const floor=start+Math.floor((best-start)*.78);
    let paragraph=-1,sentence=-1,word=-1;
    for(let j=best;j>floor;j--){
     if(word<0&&/\s/u.test(chars[j-1]))word=j;
     if(sentence<0&&/\s/u.test(chars[j-1])&&/[.!?…»”]/u.test(chars[j-2]||""))sentence=j;
     if(chars[j-1]==="\n"&&chars[j-2]==="\n"){paragraph=j;break}
    }
    best=paragraph>start?paragraph:sentence>start?sentence:word>start?word:best;
   }
   rows.push({start,end:best,text:chars.slice(start,best).join("")});start=best;
  }
 };
 if(stop>0&&stop<length){range(0,stop);range(stop,length)}else range(0,length);
 return rows.length?rows:[{start:0,end:0,text:""}];
}
export function pageAt(rows,offset){
 const i=rows.findIndex(p=>p.start<=offset&&offset<p.end);
 return i<0?Math.max(0,rows.length-1):i;
}
