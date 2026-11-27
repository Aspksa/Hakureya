import test from "node:test";
import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {existsSync} from "node:fs";
import {mkdtemp,readFile,rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join,resolve,extname,sep} from "node:path";
import {createServer} from "node:http";
import {build} from "vite";

const candidates=[process.env.CHROME_PATH,process.env.CHROME_BIN,
 "/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium","/opt/google/chrome/chrome",
 ...[process.env.ProgramFiles,process.env["ProgramFiles(x86)"],process.env.LOCALAPPDATA].filter(Boolean).flatMap(p=>[
 join(p,"Google","Chrome","Application","chrome.exe"),join(p,"Microsoft","Edge","Application","msedge.exe")])];
const chrome=candidates.find(p=>p&&existsSync(p));
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function waitFor(fn,ms=15000){
 const until=Date.now()+ms;
 while(Date.now()<until){try{const result=await fn();if(result)return result}catch{}await delay(100)}
 throw Error("Browser layout test timed out");
}
function connect(ws){
 let next=0;const waiting=new Map();
 ws.addEventListener("message",e=>{
  const msg=JSON.parse(e.data);const pending=waiting.get(msg.id);if(!pending)return;
  waiting.delete(msg.id);clearTimeout(pending.timer);
  if(msg.error)pending.reject(Error(msg.error.message));else pending.resolve(msg.result);
 });
 return (method,params={})=>new Promise((resolve,reject)=>{
  const id=++next,timer=setTimeout(()=>{waiting.delete(id);reject(Error("CDP timeout: "+method))},12000);
  waiting.set(id,{resolve,reject,timer});ws.send(JSON.stringify({id,method,params}));
 });
}
const graph={records:[],edges:[],total:0,limited:false};
for(let i=0;i<80;i++)graph.records.push({key:"m:"+i,group:i%5,slot:Math.floor(i/5),label:"Запись "+i});
for(let i=0;i<4;i++)graph.records.push({key:"era:"+["past","meeting","love","future"][i],group:4,kind:"epoch",sector:["past","meeting","love","future"][i],book:0,chapter_slot:0,label:["Прошлое","Встреча","Любовь","Будущее"][i],slot:20+i});
graph.records.push({key:"immortal:root",group:4,kind:"immortal_root",immortal_slot:-1,label:"Летопись",slot:30});
graph.total=graph.records.length;
const brainKeys=["plot","characters","relations","magic","time","memory","editor","analytics","twist","coordinator"];
const neural={network:true,total:10,limited:false,records:[{key:"lit:db",label:"SQLite",kind:"lit_database",group:4,slot:0},...brainKeys.map((k,i)=>({key:"brain:"+k,label:k,kind:"lit_brain",group:4,slot:i+1,neural_inputs:i?[brainKeys[i-1]]:[]}))],edges:brainKeys.slice(1).map((k,i)=>({a:"brain:"+brainKeys[i],b:"brain:"+k,kind:"neural_input"}))};
const prose=Array.from({length:55},(_,i)=>"Абзац "+(i+1)+". Хакурэя подняла глаза и прислушалась к тишине. — Пойдём дальше, — сказала она. Герой улыбнулся.").join("\n\n");
const checkpoints=[];
let chatCalls=0,historyFailure=false,proposalCalls=0;
const inFlightGraphs=new Map();let maxGraphConcurrency=0;
let activity={session:"test",revision:1,active:[],recent:[]};
const reader={chapter:1,title:"Первая глава",volume:1,page:1,pages:5,text:"Вечный снег. \n\nХакурэя открыла глаза.",chapter_progress:.2,volume_progress:.03,can_back:false,can_next:true,last_published:false,document:{chapter:1,last_chapter:1,title:"Первая глава",volume:1,text:prose,hash:"fixture",offset:0,segments:[{number:1,start:0,end:Array.from(prose).length,hash:"fixture-part"}],latest:2,volume_count:2,volume_ordinal:1,parts:1,epoch:1}};
test("real browser: SVG, chat, book and settings at four viewport widths",{skip:!chrome&&"Chrome/Chromium not installed",timeout:120000},async()=>{
 const dir=await mkdtemp(join(tmpdir(),"hakureya-layout-"));
 const dist=join(dir,"dist");
 let browser,server,ws;
 try{
  await build({logLevel:"error",build:{outDir:dist,emptyOutDir:true}});
  server=createServer(async(req,res)=>{
   const path=new URL(req.url,"http://localhost").pathname;
   if(path.startsWith("/api/")){
    if(path==="/api/reader"&&req.method==="POST"){
     let body="";for await(const chunk of req)body+=chunk;
     const payload=JSON.parse(body);
     if(payload.action==="position")checkpoints.push(payload);
     res.writeHead(200,{"Content-Type":"application/json"});res.end(JSON.stringify(payload.action==="position"?{ok:true}:{reader}));return;
    }
    if(path==="/api/history"&&historyFailure){historyFailure=false;res.writeHead(503,{"Content-Type":"application/json"}).end(JSON.stringify({error:"fixture unavailable"}));return}
    if(path==="/api/writer/draft/count"){res.writeHead(200,{"Content-Type":"application/json"}).end(JSON.stringify({pending:0,proposals:0,connected:false}));return}
    if(path==="/api/writer"){res.writeHead(200,{"Content-Type":"application/json"}).end(JSON.stringify({pending:0,published:14,attempts_today:2,daily_limit:20,published_chars:3600,page_chars:1800,target_pages:20,chapter_pages:20,chapter_progress:{chapter:14,parts:2,chars:3600,target_chars:36000},mode:"draft",interval:20,connected:false,model:"fixture",reason:"Ожидание",budget:"Бюджет не задан"}));return}
    if(path==="/api/proposals"){res.writeHead(200,{"Content-Type":"application/json"}).end(JSON.stringify({pending:null,recent:[],approved:0}));return}
    if(path==="/api/proposals/generate"){proposalCalls++;req.resume();res.writeHead(200,{"Content-Type":"application/json"}).end(JSON.stringify({pending:{id:1,revision:"fixture",kind:"character",idea:"Хочу добавить персонажа",title:"Новый герой",description:"Описание",impact:"Влияние",risks:"Риски"},recent:[],approved:0}));return}
    if(path==="/api/proposals/decision"){req.resume();res.writeHead(200,{"Content-Type":"application/json"}).end(JSON.stringify({pending:null,recent:[{title:"Новый герой",status:"approved"}],approved:1}));return}
    if(path==="/api/chat")chatCalls++;
    if(path==="/api/graph"||path==="/api/graph/network"){inFlightGraphs.set(path,(inFlightGraphs.get(path)||0)+1);maxGraphConcurrency=Math.max(maxGraphConcurrency,[...inFlightGraphs.values()].reduce((a,b)=>a+b,0));await delay(60);inFlightGraphs.set(path,inFlightGraphs.get(path)-1)}
    const data=path==="/api/graph/network"?neural:path==="/api/graph"?graph:path==="/api/history"?{messages:[],connected:false}:path==="/api/reader"?{reader:null}:path==="/api/chat"?{reply:"",reader,connected:false}:activity;
    req.resume();res.writeHead(200,{"Content-Type":"application/json"});res.end(JSON.stringify(data));return;
   }
   const file=resolve(dist,"."+ (path==="/"?"/index.html":path));
   if(!file.startsWith(resolve(dist)+sep)){res.writeHead(403).end();return}
   try{const content=await readFile(file);const mime={".html":"text/html",".js":"text/javascript",".css":"text/css",".svg":"image/svg+xml",".png":"image/png"}[extname(file)]||"application/octet-stream";res.writeHead(200,{"Content-Type":mime});res.end(content)}catch{res.writeHead(404).end()}
  });
  await new Promise(r=>server.listen(0,"127.0.0.1",r));
  const url="http://127.0.0.1:"+server.address().port+"/";
  const profile=join(dir,"profile");
  browser=spawn(chrome,["--headless=new","--no-sandbox","--disable-gpu","--disable-dev-shm-usage","--no-first-run","--no-default-browser-check","--disable-background-networking","--remote-debugging-port=0","--user-data-dir="+profile,"about:blank"],{stdio:"ignore"});
  browser.on("error",()=>{});
  const port=await waitFor(async()=>Number((await readFile(join(profile,"DevToolsActivePort"),"utf8")).split(/\r?\n/)[0]));
  const target=await waitFor(async()=> (await (await fetch("http://127.0.0.1:"+port+"/json/list")).json()).find(t=>t.type==="page"));
  ws=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r,j)=>{const timer=setTimeout(()=>j(Error("CDP connection timeout")),10000);ws.addEventListener("open",()=>{clearTimeout(timer);r()},{once:true});ws.addEventListener("error",()=>{clearTimeout(timer);j(Error("CDP connection failed"))},{once:true})});
  const send=connect(ws);
  await send("Page.enable");
  await send("Emulation.setEmulatedMedia",{features:[{name:"prefers-reduced-motion",value:"reduce"}]});
  const evaluate=async expression=>{
   const result=await send("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:true});
   if(result.exceptionDetails)throw Error(result.exceptionDetails.text);
   return result.result.value;
  };
  for(const [width,height] of [[1920,1080],[1366,768],[1280,720],[390,844]]){
   await send("Emulation.setDeviceMetricsOverride",{width,height,deviceScaleFactor:1,mobile:false});
   historyFailure=width===390;
   await send("Page.navigate",{url:url+"?width="+width});
   await waitFor(()=>evaluate("location.search==='?width="+width+"' && !!document.querySelector('#graph [data-key=\"immortal:root\"]')"));
   await evaluate("document.querySelector('#network-open').click()");
   await waitFor(()=>evaluate("document.querySelector('#network-open').getAttribute('aria-pressed')==='true' && document.querySelectorAll('#graph [data-key^=\"brain:\"]').length===10"));
   assert.ok(await evaluate("document.querySelector('#info').textContent.includes('10 мозгов')"));
   await evaluate("document.querySelector('#network-open').click()");
   await waitFor(()=>evaluate("document.querySelector('#network-open').getAttribute('aria-pressed')==='false' && !!document.querySelector('#graph [data-key=\"immortal:root\"]')"));
   await delay(150);
   const metrics=await evaluate("(()=>{const root=document.querySelector('#graph [data-key=\"root\"]'),circle=root.querySelector('circle[r=\"9\"]'),label=root.querySelector('text');return {width:document.querySelector('#graph').clientWidth,diameter:circle.getBoundingClientRect().width,font:parseFloat(getComputedStyle(label).fontSize)*label.getScreenCTM().a,labels:[...document.querySelectorAll('#graph .label')].filter(e=>e.getAttribute('visibility')!=='hidden').length}})()");
   assert.equal(metrics.width,width);
   assert.ok(metrics.diameter>=17.5&&metrics.diameter<=18.5,JSON.stringify(metrics));
   assert.ok(metrics.font>=13&&metrics.font<=16,JSON.stringify(metrics));
   assert.ok(metrics.labels>=1);
   const collisions=await evaluate("(()=>{const ids=['replay','atlas-open','network-open','stellar-cinema'];const nodes=ids.map(id=>[id,document.getElementById(id).getBoundingClientRect()]);nodes.push(['effects',document.querySelector('.genesis-settings').getBoundingClientRect()]);return nodes.flatMap(([id,a],i)=>nodes.slice(i+1).filter(([,b])=>a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top).map(([other])=>id+' / '+other))})()");
   assert.deepEqual(collisions,[]);
   assert.equal(await evaluate("document.querySelector('#graph [data-key=\\\"cloud:api\\\"] title').textContent"),"Cloud.ru");
   assert.ok(await evaluate("!!document.querySelector('#stellar-core') && !!document.querySelector('#stellar-chapter')"));
   await evaluate("document.querySelector('#stellar-cinema').click()");
   assert.ok(await evaluate("document.querySelector('#stage').classList.contains('stellar-cinema') && document.querySelector('#stellar-cinema').getAttribute('aria-pressed')==='true'"));
   await evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}))");
   assert.equal(await evaluate("document.querySelector('#stage').classList.contains('stellar-cinema')"),false);
   if(width===1920){
    activity={session:"test",revision:2,active:[{id:"fixture-writer",kind:"chronicle",source:"root",target:"root",stage:"streaming",response_chars:240,prose_chars:180,chunks:3,sources:["root"],events:[{seq:1,stage:"context",target:"root"},{seq:2,stage:"streaming",target:"root"}]}],recent:[]};
    await waitFor(()=>evaluate("!document.querySelector('.stellar-ledger').hidden && document.querySelector('.stellar-ledger .stellar-current')?.textContent.includes('поступает текст')"));
    assert.ok(await evaluate("document.querySelector('.stellar-ledger').textContent.includes('180 знаков прозы')"));
    activity={session:"test",revision:3,active:[],recent:[]};
    await waitFor(()=>evaluate("document.querySelector('.stellar-ledger').hidden"));
   }
   await evaluate("document.querySelector('#avatar').click()");
   await waitFor(()=>evaluate("!document.querySelector('#chat').hidden"));
   await delay(200);
   if(width===390){await waitFor(()=>evaluate("!document.querySelector('#chat-retry').hidden"));await evaluate("document.querySelector('#chat-retry').click()");await waitFor(()=>evaluate("document.querySelector('#chat-retry').hidden"))}
   assert.equal(await evaluate("document.querySelector('#chat-send').disabled"),true);
   await evaluate("document.querySelector('#chat-menu').click()");
   assert.equal(await evaluate("document.querySelector('#menu').hidden"),false);
   await evaluate("document.querySelector('#chat-menu').click()");
   assert.equal(await evaluate("document.querySelector('#menu').hidden"),true);
   assert.deepEqual(await evaluate("[...document.querySelectorAll('#chat-workspace button')].map(b=>b.id)"),["quick-read","writer-open","quick-draft","quick-proposals","universe-open"]);
   assert.equal(await evaluate("document.querySelectorAll('#composer button').length"),1);
   assert.equal(await evaluate("document.querySelector('#chat-connection').textContent"),"Локальный режим");
   assert.equal(await evaluate("document.querySelector('#menu #writer-open')===null && document.querySelector('#menu #universe-open')===null"),true);
   if(width===1920){
    await evaluate("document.querySelector('#writer-open').click()");
    await waitFor(()=>evaluate("document.querySelector('#writer-metrics').children.length===4 && !document.querySelector('#writer-save').disabled"));
    assert.deepEqual(await evaluate("[...document.querySelectorAll('#writer-metrics strong')].map(e=>e.textContent)"),["14","0","2 / 20","2.0 / 20 А4"]);
    assert.equal(await evaluate("document.querySelector('#writer-chapter-bar').value"),0.1);
    assert.equal(await evaluate("document.querySelector('#writer-technical').closest('details').open"),false);
    assert.equal(await evaluate("document.querySelector('#writer-status').textContent"),"Ожидание");
    await evaluate("document.querySelector('#writer-close').click()");
   }
   const chat=await evaluate("({width:document.querySelector('#chat').getBoundingClientRect().width,graph:document.querySelector('#graph').clientWidth,font:parseFloat(getComputedStyle(document.querySelector('#messages')).fontSize)})");
   assert.ok(chat.font>=16);
   if(width>=1050){assert.ok(chat.width>=640&&chat.width<=860);assert.ok(Math.abs(chat.width+chat.graph-width)<2)}else assert.equal(chat.width,width);
   await evaluate("document.querySelector('#chat-menu').click();document.querySelector('#command-plus').click()");
   assert.equal(await evaluate("document.querySelector('#command-dialog').open"),true);
   assert.equal(await evaluate("document.querySelectorAll('#command-dialog .command-tools button').length"),0);
   assert.equal(await evaluate("document.querySelector('#menu').hidden"),true);
   assert.ok(await evaluate("document.querySelectorAll('#command-results .command-item').length>0 && document.querySelectorAll('#command-results .command-item').length<30"));
   await evaluate("(()=>{const s=document.querySelector('#command-category');s.value='';s.dispatchEvent(new Event('change',{bubbles:true}))})()");
   assert.equal(await evaluate("document.querySelectorAll('#command-results .command-item').length"),186);
   const palette=await evaluate("(()=>{const r=document.querySelector('#command-dialog').getBoundingClientRect();return {w:r.width,h:r.height}})()");
   assert.ok(palette.w<=width&&palette.h<=height,JSON.stringify(palette));
   await evaluate("(()=>{const s=document.querySelector('#command-search');s.value='статус развития';s.dispatchEvent(new Event('input',{bubbles:true}));return true})()");
   assert.equal(await evaluate("document.querySelectorAll('#command-results .command-item').length"),1);
   await evaluate("document.querySelector('#command-results .command-item').click()");
   assert.equal(await evaluate("document.querySelector('#prompt').value"),"Статус развития");
   assert.equal(await evaluate("document.querySelector('#chat-send').disabled"),false);
   assert.equal(await evaluate("document.querySelector('#command-dialog').open"),false);
   assert.equal(await evaluate("document.querySelector('#messages').children.length"),0);
   await evaluate("document.querySelector('#prompt').value=''");
   await evaluate("document.querySelector('#chat-menu').click();document.querySelector('#command-plus').click()");
   await evaluate("(()=>{const s=document.querySelector('#command-search');s.value='открыть главу';s.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#command-results .command-item').click();return true})()");
   assert.equal(await evaluate("document.querySelector('#prompt').value"),"Летопись: читать 5");
   assert.equal(await evaluate("document.querySelector('#prompt').value.slice(document.querySelector('#prompt').selectionStart,document.querySelector('#prompt').selectionEnd)"),"5");
   assert.equal(await evaluate("document.querySelector('#messages').children.length"),0);
   if(width===1920){
    const previousCalls=chatCalls,previousProposals=proposalCalls;
    await evaluate("document.querySelector('#prompt').value='Хочу добавить персонажа';document.querySelector('#composer').dispatchEvent(new Event('submit',{cancelable:true,bubbles:true}));true");
    await waitFor(()=>evaluate("document.querySelector('#proposal-dialog').open && !document.querySelector('#proposal-create').hidden"));
    assert.equal(await evaluate("document.querySelector('#proposal-idea').value"),"Хочу добавить персонажа");
    assert.equal(await evaluate("document.querySelector('#proposal-generate').disabled"),true);
    assert.equal(chatCalls,previousCalls);
    await evaluate("document.querySelector('#proposal-consent').click();document.querySelector('#proposal-generate').click()");
    await waitFor(()=>evaluate("!document.querySelector('#proposal-review').hidden && !document.querySelector('#proposal-approve').disabled"));
    assert.equal(await evaluate("document.querySelector('#proposal-title').textContent"),"Новый герой");
    await evaluate("window.confirm=()=>true;document.querySelector('#proposal-approve').click()");
    await waitFor(()=>evaluate("document.querySelector('#proposal-history-list').textContent.includes('Утверждён')"));
    assert.equal(proposalCalls,previousProposals+1);
    assert.equal(chatCalls,previousCalls);
    await evaluate("document.querySelector('#proposal-close').click()");
   }
   const sentBefore=chatCalls;
   await evaluate("document.querySelector('#prompt').value='Читать книгу';document.querySelector('#composer').dispatchEvent(new Event('submit',{cancelable:true,bubbles:true}));document.querySelector('#prompt').value='Дубль';document.querySelector('#composer').dispatchEvent(new Event('submit',{cancelable:true,bubbles:true}));true");
   await waitFor(()=>evaluate("!document.querySelector('#book').hidden"));
   assert.equal(await evaluate("document.querySelector('#chat-workspace').hidden"),true);
   assert.equal(chatCalls,sentBefore+1);
   const book=await evaluate("({font:parseFloat(getComputedStyle(document.querySelector('#book-page')).fontSize),title:parseFloat(getComputedStyle(document.querySelector('#book-title')).fontSize),button:document.querySelector('#book-next').getBoundingClientRect().width})");
   assert.equal(book.font,21);
   assert.ok(book.title>=29);
   assert.ok(book.button>=50);
   await waitFor(()=>checkpoints.length>0);
   const fit=await evaluate("({page:document.querySelector('#book-page').getBoundingClientRect().height,available:document.querySelector('#book-scroll').clientHeight,position:document.querySelector('#book-position').textContent})");
   assert.ok(fit.page<=fit.available+2,JSON.stringify(fit));
   assert.match(fit.position,/Страница 1 из [2-9][0-9]*|Страница 1 из 1[0-9]+/);
   const before=checkpoints.length;
   await evaluate("document.querySelector('#book-next').click()");
   await waitFor(()=>checkpoints.length>before&&checkpoints.at(-1).start>0);
   assert.match(await evaluate("document.querySelector('#book-position').textContent"),/Страница 2 из /);
   assert.ok(await evaluate("document.querySelector('#book-title').hidden"));
   checkpoints.length=0;
   await evaluate("document.querySelector('#settings').click()");
   assert.ok(await evaluate("document.querySelector('#config').open && parseFloat(getComputedStyle(document.querySelector('#key')).fontSize)>=16"));
   await evaluate("document.querySelector('#config-close').click()");
   await evaluate("document.querySelector('#book-exit').click()");
   await waitFor(()=>evaluate("document.querySelector('#book').hidden && !document.querySelector('#chat-workspace').hidden"));
   const beforeRead=chatCalls;
   await evaluate("document.querySelector('#prompt').value='Моя незаконченная мысль';document.querySelector('#quick-read').click()");
   await waitFor(()=>evaluate("!document.querySelector('#book').hidden"));
   assert.equal(chatCalls,beforeRead);
   assert.equal(await evaluate("document.querySelector('#prompt').value"),"Моя незаконченная мысль");

  }
  assert.ok(maxGraphConcurrency<=1,"overlapping graph requests: "+maxGraphConcurrency);
 }finally{
  ws?.close();
  if(browser&&browser.exitCode===null){browser.kill();await Promise.race([new Promise(r=>browser.once("exit",r)),delay(2000)])}
  if(server){server.closeAllConnections?.();await new Promise(r=>server.close(r))}
  await rm(dir,{recursive:true,force:true,maxRetries:5,retryDelay:200}).catch(()=>{});
 }
});
