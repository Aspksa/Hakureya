import "./style.css";
import {mountGraph} from "./live-graph";
import {measuredPages,pageAt} from "./reader-pagination.mjs";
import {commandGroups,commandCount,searchCommands} from "./command-catalog.mjs";
const $=(id:string)=>document.getElementById(id)!;
let selectedVolume:number|null=null,selectedAtlas:string|null=null,networkView=false;
const atlasTrail:string[]=[];
let live:ReturnType<typeof mountGraph>|null=null;
function ensureGraph(){
 if(!live){try{$("graph").replaceChildren();live=mountGraph($("graph") as unknown as SVGSVGElement,$("info"),volume=>{networkView=false;if(selectedAtlas!==null)atlasTrail.push(selectedAtlas);selectedAtlas=null;selectedVolume=volume;void refreshGraph()},scope=>{networkView=false;if(selectedAtlas!==null)atlasTrail.push(selectedAtlas);selectedVolume=null;selectedAtlas=scope;void refreshGraph()})}catch(e){console.error("Hakureya graph initialization",e);$("graph").replaceChildren();$("info").textContent="Ошибка визуализации · ↻ повторить"}}
 return live;
}
let busy=false,historyReady=false,historyLoading=false;
$("replay").onclick=()=>{networkView=false;selectedVolume=null;selectedAtlas=null;atlasTrail.length=0;void refreshGraph().then(()=>live?.replay())};$("reset").onclick=()=>{networkView=false;selectedVolume=null;selectedAtlas=null;atlasTrail.length=0;void refreshGraph().then(()=>live?.replay());$("menu").hidden=true};
let graphRequest=0,graphInFlight=false,graphQueued=false;
function graphPath(){return networkView?"graph/network":selectedAtlas!==null?"graph/atlas"+(selectedAtlas?"/"+selectedAtlas:""):selectedVolume===null?"graph":"graph/volume/"+selectedVolume}
let graphPending:Promise<void>|null=null;
function refreshGraph():Promise<void>{
 graphQueued=true;
 if(graphInFlight)return graphPending!;
 graphInFlight=true;
 graphPending=(async()=>{
  try{
   while(graphQueued){
    graphQueued=false;const path=graphPath(),id=++graphRequest;
    try{
     const data=await api(path);
     if(path!==graphPath()||id!==graphRequest){graphQueued=true;continue}
     if(!Array.isArray(data.records)||!Array.isArray(data.edges))throw Error("Некорректная карта");
     ensureGraph()?.render(data);
     $("atlas-back").hidden=!atlasTrail.length;
     $("atlas-open").setAttribute("aria-pressed",String(selectedAtlas!==null));
     $("network-open").setAttribute("aria-pressed",String(networkView));
    }catch(e){if(path===graphPath())$("info").textContent="Карта недоступна · ↻ повторить";console.error("Hakureya graph refresh",e)}
   }
  }finally{graphInFlight=false;graphPending=null}
 })();
 return graphPending;
}
let writerPollBusy=false,previewPollBusy=false;
$("network-open").onclick=()=>{networkView=!networkView;selectedVolume=null;selectedAtlas=null;atlasTrail.length=0;void refreshGraph()};
$("atlas-open").onclick=()=>{networkView=false;selectedVolume=null;selectedAtlas="";atlasTrail.length=0;void refreshGraph()};
$("atlas-back").onclick=()=>{if(atlasTrail.length){selectedVolume=null;selectedAtlas=atlasTrail.pop()!;void refreshGraph()}};
let activityBusy=false,activityRevision="",activityTimer=0,activityActive=false,activityGraphSignature="";
async function refreshActivity(){
 if(document.hidden||activityBusy)return;
 activityBusy=true;
 try{
  const controller=new AbortController(),timeout=window.setTimeout(()=>controller.abort(),3000);
  let data;try{const response=await fetch("/api/activity",{cache:"no-store",signal:controller.signal});if(!response.ok)throw Error("activity");data=await response.json()}finally{clearTimeout(timeout)}
  if(document.hidden)return;
  activityActive=data.active.length>0;
  if(writerDialog.open&&writerPreviewOpt.checked&&!previewPollBusy){previewPollBusy=true;const session=writerSession;void api("writer/preview").then(st=>{if(session===writerSession&&writerDialog.open&&writerPreviewOpt.checked){const follow=writerPreviewText.scrollHeight-writerPreviewText.scrollTop-writerPreviewText.clientHeight<48;writerPreviewText.textContent=st.active?(st.story||"Ожидание художественного текста…"):(st.story?"Последний полученный фрагмент (не утверждён):\n"+st.story:"Нет поступающего текста");if(follow)writerPreviewText.scrollTop=writerPreviewText.scrollHeight}}).catch(()=>{}).finally(()=>{previewPollBusy=false})}
  if(writerDialog.open&&!writerPollBusy){writerPollBusy=true;const session=writerSession;void api("writer").then(st=>{if(session===writerSession&&writerDialog.open&&!writerSave.disabled)renderWriter(st)}).catch(()=>{}).finally(()=>{writerPollBusy=false})}
  live?.setActivity(data);
  const revision=data.session+":"+data.revision;
  if(revision!==activityRevision){activityRevision=revision;const signature=JSON.stringify([data.session,data.active.map((a:any)=>[a.id,a.stage,a.target]),data.recent.map((a:any)=>[a.id,a.stage,a.target])]);if(signature!==activityGraphSignature){activityGraphSignature=signature;if(!activityActive||selectedVolume===null)void refreshGraph()}}
 }catch{activityRevision="";activityGraphSignature="";activityActive=false;live?.clearActivity()}finally{activityBusy=false}
}
function scheduleActivity(){clearTimeout(activityTimer);if(document.hidden)return;activityTimer=window.setTimeout(async()=>{await refreshActivity();scheduleActivity()},activityActive||busy?400:1200)}
document.addEventListener("visibilitychange",()=>{clearTimeout(activityTimer);if(!document.hidden){void refreshGraph();void refreshActivity();scheduleActivity()}});
const avatar=$("avatar"),chat=$("chat"),prompt=$("prompt") as HTMLTextAreaElement,menu=$("menu"),config=$("config") as HTMLDialogElement;
let cinema=false;
function syncGraphViewport(){const stage=$("stage");stage.classList.toggle("stellar-cinema",cinema);stage.classList.toggle("chat-open",!chat.hidden);stage.classList.toggle("book-open",!chat.hidden&&!book.hidden);stage.classList.toggle("book-full",!chat.hidden&&!book.hidden&&focused);live?.setReader(!cinema&&!chat.hidden&&!book.hidden,!cinema&&!chat.hidden&&!book.hidden&&focused);live?.resize()}
function toggle(open=chat.hidden){menu.hidden=true;chat.hidden=!open;syncGraphViewport();avatar.setAttribute("aria-expanded",String(open));avatar.setAttribute("aria-label",open?"Свернуть чат":"Открыть чат Hakureya");if(open){if(!book.hidden){$("book-scroll").focus();scheduleReflow()}else{$("messages").scrollTop=$("messages").scrollHeight;prompt.focus()}}else avatar.focus()}
function setCinema(value:boolean){cinema=value;$("stellar-cinema").setAttribute("aria-pressed",String(value));$("stellar-cinema").setAttribute("aria-label",value?"Выйти из режима наблюдения":"Кинематографический режим");syncGraphViewport();}
$("stellar-cinema").onclick=()=>setCinema(!cinema);
avatar.onclick=()=>toggle();$("close").onclick=()=>toggle(false);avatar.oncontextmenu=e=>{e.preventDefault();toggleMenu()};
function toggleMenu(){menu.hidden=!menu.hidden;$("chat-menu").setAttribute("aria-expanded",String(!menu.hidden));if(!menu.hidden){menu.classList.toggle("from-chat",!chat.hidden);(menu.querySelector("button") as HTMLButtonElement|null)?.focus()}}
$("chat-menu").onclick=toggleMenu;document.addEventListener("keydown",e=>{if(e.key==="Escape"){if(config.open||writerDialog.open||commandDialog.open||universeDialog.open||note.open)return;if(cinema){setCinema(false);return}if(!menu.hidden)menu.hidden=true;else if(!chat.hidden&&!config.open&&!writerDialog.open&&!commandDialog.open&&!universeDialog.open&&!note.open)toggle(false)}});document.addEventListener("click",e=>{if(!menu.contains(e.target as Node)&&!avatar.contains(e.target as Node)&&!$("chat-menu").contains(e.target as Node))menu.hidden=true;if(menu.hidden)$("chat-menu").setAttribute("aria-expanded","false")});
function message(role:string,content:string,force=false){const box=$("messages"),follow=force||box.scrollHeight-box.scrollTop-box.clientHeight<80;const p=document.createElement("p");p.className="message "+role;p.textContent=content;box.append(p);if(follow)box.scrollTop=box.scrollHeight;return p}
async function api(path:string,data?:unknown){
 const controller=new AbortController(),timeout=window.setTimeout(()=>controller.abort(),path==="chat"?130000:15000);
 try{
  const response=await fetch("/api/"+path,{...(data===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)}),signal:controller.signal});
  const value=await response.json();if(!response.ok)throw Error(value.error||"Ошибка сервера");return value;
 }catch(e){if(controller.signal.aborted)throw Error("Истекло время ожидания. Запрос мог завершиться на сервере; проверьте историю.");throw e}finally{clearTimeout(timeout)}
}
const sendButton=$("chat-send") as HTMLButtonElement;
function syncComposer(){sendButton.disabled=busy||!historyReady||!prompt.value.trim();$("composer").setAttribute("aria-busy",String(busy))}
prompt.oninput=syncComposer;
async function init(){
 if(historyLoading||historyReady)return;historyLoading=true;syncComposer();
 try{
  const data=await api("history");$("messages").replaceChildren();
  for(const m of data.messages)message(m.role,m.content,true);
  historyReady=true;$("status").textContent=data.connected?"Cloud.ru подключён":"Локальный режим · Cloud.ru не подключён";
  $("chat-retry").hidden=true;
 }catch{$("status").textContent="История недоступна. Повторите подключение.";$("chat-retry").hidden=false}
 finally{historyLoading=false;syncComposer()}
 if(historyReady){const generation=readerGeneration;try{const page=await api("reader");if(page.reader&&!busy&&generation===readerGeneration&&!prompt.value.trim())showBook(page.reader)}catch{}}
}
$("chat-retry").onclick=()=>void init();
syncComposer();
const commandDialog=$("command-dialog") as HTMLDialogElement,commandPlus=$("command-plus") as HTMLButtonElement,commandSearch=$("command-search") as HTMLInputElement,commandCategory=$("command-category") as HTMLSelectElement,commandResults=$("command-results");
let commandInitialized=false;
function renderCommands(){
 const groups=searchCommands(commandSearch.value,commandCategory.value);
 commandResults.replaceChildren();
 let count=0;
 for(const [name,entries] of groups){
  const section=document.createElement("section"),title=document.createElement("h3");
  title.textContent=name;section.append(title);
  for(const [label,command,example] of entries){
   count++;
   const btn=document.createElement("button"),strong=document.createElement("strong"),small=document.createElement("small");
   btn.type="button";btn.className="command-item";strong.textContent=label;small.textContent=command+(example??"");
   btn.append(strong,small);
   btn.onclick=()=>{
    const value=command+(example??"");
    if(prompt.value.trim()&&prompt.value!==value&&!window.confirm("Заменить текущий текст выбранной командой?"))return;
    prompt.value=value;syncComposer();commandDialog.close();prompt.focus();
    if(example)prompt.setSelectionRange(command.length,value.length);
   };
   section.append(btn);
  }
  commandResults.append(section);
 }
 $("command-count").textContent=count+" из "+commandCount+" команд";
 if(!count){const empty=document.createElement("p");empty.textContent="Ничего не найдено. Попробуйте другое слово.";commandResults.append(empty)}
}
commandPlus.onclick=()=>{
 if(!commandInitialized){
  for(const [name] of commandGroups){const option=document.createElement("option");option.value=option.textContent=name;commandCategory.append(option)}
  commandInitialized=true;
 }
 if(commandDialog.open)return;commandSearch.value="";commandCategory.value="";renderCommands();commandResults.scrollTop=0;commandDialog.showModal();commandPlus.setAttribute("aria-expanded","true");commandSearch.focus();
};
commandDialog.onclose=()=>{commandPlus.setAttribute("aria-expanded","false")};
$("command-close").onclick=()=>commandDialog.close();
commandSearch.oninput=()=>{renderCommands();commandResults.scrollTop=0};commandCategory.onchange=()=>{renderCommands();commandResults.scrollTop=0};
$("command-writer").onclick=()=>{commandDialog.close();$("writer-open").click()};
$("command-cloud").onclick=()=>{commandDialog.close();$("settings").click()};
$("command-universe").onclick=()=>{commandDialog.close();$("universe-open").click()};
$("command-network").onclick=()=>{commandDialog.close();toggle(false);if(!networkView)$("network-open").click()};
const cloudModel=$("model") as HTMLInputElement,cloudKey=$("key") as HTMLInputElement;
const modelList=$("model-list") as HTMLSelectElement,modelListLabel=$("model-list-label");
const loadModels=$("load-models") as HTMLButtonElement,saveConfig=$("save") as HTMLButtonElement;
const configStatus=$("config-status"),cloudConsent=$("consent") as HTMLInputElement,rememberCloud=$("remember-cloud") as HTMLInputElement;
let configSession=0;
function setConfigPending(pending:boolean){loadModels.disabled=saveConfig.disabled=($("forget-cloud") as HTMLButtonElement).disabled=pending}
$("settings").onclick=()=>{
 menu.hidden=true;
 if(config.open)return;configSession++;setConfigPending(false);
 cloudConsent.checked=false;cloudKey.value="";
 configStatus.textContent="";
 modelListLabel.hidden=true;
 modelList.replaceChildren();
 config.showModal();
};
$("config-close").onclick=()=>config.close();
$("forget-cloud").onclick=async()=>{if(saveConfig.disabled)return;const session=configSession;setConfigPending(true);try{await api("config/forget",{});$("status").textContent="Cloud.ru отключён";if(session===configSession&&config.open){cloudKey.value="";rememberCloud.checked=false;configStatus.textContent="Ключ удалён, автономный писатель остановлен."}}catch(e){if(session===configSession&&config.open)configStatus.textContent=String(e)}finally{if(session===configSession)setConfigPending(false)}};
const writerDialog=$("writer-dialog") as HTMLDialogElement,writerMode=$("writer-mode") as HTMLSelectElement,writerInterval=$("writer-interval") as HTMLSelectElement,writerConsent=$("writer-consent") as HTMLInputElement,writerNow=$("writer-now") as HTMLInputElement;
const universeDialog=$("universe-dialog") as HTMLDialogElement;
let universePage=1,universeSerial=0;
async function renderUniverse(){
 const serial=++universeSerial;$("universe-retry").hidden=true;$("universe-summary").textContent="Загрузка…";
 ($("universe-prev") as HTMLButtonElement).disabled=true;($("universe-next") as HTMLButtonElement).disabled=true;
 try{
  const data=await api("universe/"+universePage);if(serial!==universeSerial||!universeDialog.open)return;
  $("universe-summary").textContent=data.chapters+" частей · "+data.scenes+" сцен · "+data.volumes+" томов · "+Math.round(data.chars/1800)+" усл. А4 · "+data.actors+" персонажей · "+data.pending+" черновиков";
  $("universe-page").textContent=universePage+" / "+data.pages;
  ($("universe-prev") as HTMLButtonElement).disabled=universePage<=1;($("universe-next") as HTMLButtonElement).disabled=universePage>=data.pages;
  const galaxies=$("universe-galaxies");galaxies.replaceChildren();
  for(const group of data.volume_groups){
   const b=document.createElement("button"),star=document.createElementNS("http://www.w3.org/2000/svg","svg");
   b.type="button";b.className="universe-volume";b.setAttribute("aria-label","Открыть карту тома "+group.volume);
   star.setAttribute("viewBox","0 0 64 64");star.setAttribute("aria-hidden","true");
   for(let j=0;j<group.count;j++){const point=document.createElementNS("http://www.w3.org/2000/svg","circle"),angle=j*Math.PI*2/Math.max(1,group.count);point.setAttribute("cx",String(32+22*Math.cos(angle)));point.setAttribute("cy",String(32+22*Math.sin(angle)));point.setAttribute("r","2");point.setAttribute("fill","#edcf89");star.append(point)}
   const core=document.createElementNS("http://www.w3.org/2000/svg","circle");core.setAttribute("cx","32");core.setAttribute("cy","32");core.setAttribute("r","5");core.setAttribute("fill","#fff2c6");star.append(core);
   const name=document.createElement("small");name.textContent="Том "+group.volume+" · "+group.count;b.append(star,name);
   b.onclick=()=>{universeDialog.close();networkView=false;selectedAtlas=null;atlasTrail.length=0;selectedVolume=group.volume;void refreshGraph()};galaxies.append(b)
  }
  const actors=$("universe-actors");actors.replaceChildren();
  for(const actor of data.actors_list){const b=document.createElement("button");b.type="button";b.textContent=actor.name+" · "+actor.count+" частей";b.onclick=()=>universeCommand("История персонажа "+actor.name);actors.append(b)}
  $("universe-family").textContent=data.family.length?data.family.map((r:any)=>r.a+" ↔ "+r.b+" · гл. "+r.first).join("\n"):"Подтверждённые доступные родственные связи пока не найдены.";
  const list=$("universe-list");list.replaceChildren();
  for(const item of data.items){
   const row=document.createElement("button"),title=document.createElement("strong"),small=document.createElement("small");
   row.type="button";title.textContent=item.number+". "+item.title;small.textContent="Том "+item.volume+" · "+item.chars+" знаков";
   row.append(title,small);row.onclick=()=>universeCommand("Летопись: читать "+item.number);list.append(row)
  }
 }catch(e){if(serial===universeSerial&&universeDialog.open){$("universe-summary").textContent=String(e);$("universe-list").replaceChildren();$("universe-galaxies").replaceChildren();$("universe-actors").replaceChildren();$("universe-family").textContent="";$("universe-page").textContent="";($("universe-prev") as HTMLButtonElement).disabled=universePage<=1;$("universe-retry").hidden=false}}
}
function universeCommand(value:string){if(busy||!historyReady){$("universe-summary").textContent="Дождитесь окончания запроса или загрузки истории.";return}if(prompt.value.trim()&&prompt.value!==value&&!window.confirm("Заменить текущий текст?"))return;universeDialog.close();if(!book.hidden)exitBook();toggle(true);prompt.value=value;syncComposer();prompt.focus();if(!value.endsWith(" ")){const form=$("composer") as HTMLFormElement;form.requestSubmit()}}
$("universe-open").onclick=()=>{menu.hidden=true;if(universeDialog.open)return;universePage=1;universeDialog.showModal();void renderUniverse()};
$("universe-close").onclick=()=>{universeSerial++;universeDialog.close()};
$("universe-prev").onclick=()=>{if(universePage>1){universePage--;void renderUniverse()}};
$("universe-next").onclick=()=>{universePage++;void renderUniverse()};
$("universe-retry").onclick=()=>void renderUniverse();
universeDialog.onclose=()=>{universeSerial++};
$("universe-dossier").onclick=()=>universeCommand("Реестр персонажей");
$("universe-knowledge").onclick=()=>universeCommand("Матрица знаний");
$("universe-search").onclick=()=>universeCommand("Поиск сцены ");
$("universe-atlas").onclick=()=>universeCommand("Атлас вселенной");
$("universe-timeline").onclick=()=>universeCommand("Хронология вселенной");
$("universe-audit").onclick=()=>universeCommand("Проверить индекс сцен");
const writerPreviewOpt=$("writer-preview-opt") as HTMLInputElement,writerPreviewText=$("writer-preview-text");
writerPreviewOpt.onchange=()=>{writerPreviewText.hidden=!writerPreviewOpt.checked;writerPreviewText.textContent="";if(writerPreviewOpt.checked)void refreshActivity()};
const writerStatus=$("writer-status"),writerSave=$("writer-save") as HTMLButtonElement;
const writerChapterPages=$("writer-chapter-pages") as HTMLSelectElement;
const writerTarget=$("writer-target") as HTMLSelectElement,writerBudget=$("writer-budget") as HTMLInputElement,writerInputRate=$("writer-input-rate") as HTMLInputElement,writerOutputRate=$("writer-output-rate") as HTMLInputElement;
let writerSession=0,writerJobActive=false;
const writerStop=$("writer-stop") as HTMLButtonElement,writerError=$("writer-error"),writerResume=$("writer-resume") as HTMLButtonElement;
function syncWriterMode(){const once=writerMode.value==="once";$("writer-target-label").textContent=once?"Объём разового задания":"Суточный объём";writerNow.disabled=once;if(once){writerNow.checked=true;if(!Number(writerTarget.value))writerTarget.value="5"}$("writer-save").textContent=once?"Начать задание":writerMode.value==="off"?"Выключить / сохранить":"Сохранить"}
writerMode.onchange=syncWriterMode;
writerTarget.onchange=()=>{if(writerMode.value==="off"&&Number(writerTarget.value))writerMode.value="once";syncWriterMode()};
function renderWriter(data:any){const active=data.job?.state==="active";if(writerJobActive&&!active&&writerMode.value==="once"){writerMode.value=data.mode;writerTarget.value=String(data.target_pages);syncWriterMode()}writerJobActive=active;writerStop.hidden=!active;writerResume.hidden=!data.resume_available;$("writer-resume-help").hidden=writerResume.hidden;writerStatus.textContent=[data.reason,...(data.job?["Разовое задание: "+(data.job.chars/data.page_chars).toFixed(1)+" / "+data.job.pages+" усл. А4 · "+data.job.attempts+"/"+data.job.limit+" запросов"]:[]),"Последняя глава: "+data.published+" · Черновики: "+data.pending,"Модель: "+(data.model||"не выбрана"),"Cloud.ru: "+(data.connected?"подключён":"не подключён")+(data.saved_connection?" · есть защищённое подключение":""),"Сегодня: "+(data.published_chars/data.page_chars).toFixed(1)+" усл. А4"+(data.target_pages?" / "+data.target_pages:"")+" · Запросов: "+data.attempts_today+"/"+data.daily_limit,data.budget].join("\n")}
$("writer-open").onclick=async()=>{menu.hidden=true;if(writerDialog.open)return;const session=++writerSession;writerConsent.checked=false;writerNow.checked=false;writerPreviewOpt.checked=false;writerPreviewText.hidden=true;writerPreviewText.textContent="";writerSave.disabled=true;writerJobActive=false;writerStop.hidden=true;writerResume.hidden=true;$("writer-resume-help").hidden=true;writerError.textContent="";$("writer-retry").hidden=true;writerStatus.textContent="Загрузка…";writerDialog.showModal();try{const data=await api("writer");if(session!==writerSession||!writerDialog.open)return;writerMode.value=data.job?.state==="active"?"once":data.mode;writerInterval.value=String(data.interval);writerTarget.value=String(data.job?.state==="active"?data.job.pages:data.target_pages);writerChapterPages.value=String(data.chapter_pages??0);writerBudget.value=String(data.budget_settings?.monthly??"");writerInputRate.value=String(data.budget_settings?.input??"");writerOutputRate.value=String(data.budget_settings?.output??"");renderWriter(data);syncWriterMode();writerSave.disabled=false}catch(e){if(session===writerSession&&writerDialog.open){writerStatus.textContent=String(e);$("writer-retry").hidden=false}}};
$("writer-retry").onclick=()=>{writerDialog.close();$("writer-open").click()};
writerDialog.onclose=()=>{if(!writerDialog.open)writerSession++};
writerResume.onclick=async()=>{if(writerSave.disabled||writerResume.disabled)return;if(!writerConsent.checked){writerError.textContent="Подтвердите согласие на новый платный запрос.";writerConsent.focus();return}writerSave.disabled=true;writerResume.disabled=true;writerError.textContent="";const session=++writerSession;try{const data=await api("writer/resume",{consent:true});if(session!==writerSession||!writerDialog.open)return;writerMode.value="once";writerTarget.value=String(data.job.pages);writerConsent.checked=false;renderWriter(data);syncWriterMode()}catch(e){if(session===writerSession)writerError.textContent=String(e)}finally{writerResume.disabled=false;if(session===writerSession)writerSave.disabled=false}};
$("writer-close").onclick=()=>{writerSession++;writerDialog.close()};
writerStop.onclick=async()=>{if(writerSave.disabled)return;writerSave.disabled=true;writerStop.disabled=true;const session=++writerSession;writerError.textContent="";try{const data=await api("writer",{mode:"off",interval:Number(writerInterval.value),target_pages:0});if(session!==writerSession||!writerDialog.open)return;writerMode.value="off";writerTarget.value="0";writerConsent.checked=false;writerNow.checked=false;renderWriter(data);syncWriterMode()}catch(e){if(session===writerSession)writerError.textContent=String(e)}finally{writerStop.disabled=false;if(session===writerSession)writerSave.disabled=false}};
$("writer-form").onsubmit=async e=>{e.preventDefault();if(writerSave.disabled)return;writerSave.disabled=true;writerError.textContent="";const session=++writerSession;try{const data=await api("writer",{mode:writerMode.value,interval:Number(writerInterval.value),consent:writerConsent.checked,start_now:writerNow.checked,target_pages:Number(writerTarget.value),chapter_pages:Number(writerChapterPages.value),...([writerBudget,writerInputRate,writerOutputRate].some(x=>x.value.trim())?{budget:{monthly:Number(writerBudget.value),input:Number(writerInputRate.value),output:Number(writerOutputRate.value)}}:{})});if(session!==writerSession||!writerDialog.open)return;renderWriter(data);writerMode.value=data.job?.state==="active"?"once":data.mode;writerNow.checked=false;writerConsent.checked=false;syncWriterMode()}catch(e){if(session===writerSession)writerError.textContent=String(e)}finally{if(session===writerSession)writerSave.disabled=false}};

config.onclose=()=>{if(!config.open){configSession++;cloudKey.value="";cloudConsent.checked=false;setConfigPending(false)}};
modelList.onchange=()=>{if(modelList.value)cloudModel.value=modelList.value};
cloudModel.oninput=()=>{if(!modelListLabel.hidden)modelList.value=cloudModel.value.trim()};
loadModels.onclick=async()=>{
 if(loadModels.disabled)return;
 const session=configSession;
 setConfigPending(true);
 modelListLabel.hidden=true;
 configStatus.textContent="Загрузка моделей…";
 try{
  const {models}=await api("config/models",{key:cloudKey.value}) as {models:string[]};
  if(session!==configSession||!config.open)return;
  const placeholder=document.createElement("option");
  placeholder.value="";
  placeholder.textContent="Выберите модель";
  modelList.replaceChildren(placeholder);
  for(const id of models){
   const option=document.createElement("option");
   option.value=option.textContent=id;
   modelList.append(option);
  }
  const currentModel=cloudModel.value.trim();
  modelList.value=models.includes(currentModel)?currentModel:"";
  modelListLabel.hidden=models.length===0;
  configStatus.textContent=models.length?"":"Cloud.ru вернул пустой список моделей.";
 }catch(e){
  if(session===configSession&&config.open)configStatus.textContent=e instanceof Error?e.message:String(e);
 }finally{
  if(session===configSession)setConfigPending(false);
 }
};
$("config-form").onsubmit=async e=>{
 e.preventDefault();
 if(saveConfig.disabled)return;
 const session=configSession;
 setConfigPending(true);
 configStatus.textContent="";
 try{
  await api("config",{model:cloudModel.value,key:cloudKey.value,consent:cloudConsent.checked,...(rememberCloud.checked?{remember:true}:{})});
  $("status").textContent="Cloud.ru подключён";
  if(session===configSession&&config.open)config.close();
 }catch(e){
  if(session===configSession&&config.open)configStatus.textContent=e instanceof Error?e.message:String(e);
 }finally{
  if(session===configSession)setConfigPending(false);
 }
};
$("composer").onsubmit=async e=>{e.preventDefault();const content=prompt.value.trim();if(!content||busy||!historyReady)return;busy=true;prompt.value="";syncComposer();message("user",content,true);$("status").textContent="Обработка запроса…";try{const result=await api("chat",{content});if(result.reader)showBook(result.reader);else message("assistant",result.reply);$("status").textContent=result.connected?"Cloud.ru · ответ получен":"Локальный режим · сообщение сохранено"}catch(e){message("error",String(e));$("status").textContent="Ошибка запроса"}finally{busy=false;syncComposer();void refreshGraph();if(!chat.hidden&&!config.open&&!writerDialog.open&&!commandDialog.open&&!universeDialog.open&&!note.open){if(book.hidden){if(!prompt.value.trim())prompt.focus()}else $("book-scroll").focus()}}};

const image=$("avatar-image") as HTMLImageElement;
function useAvatar(){image.src="/api/avatar?"+Date.now();image.onerror=()=>{image.onerror=null;image.src="/avatar.svg"}}
useAvatar();
$("avatar-picker").onclick=()=>{menu.hidden=true;($("avatar-file") as HTMLInputElement).click()};
($("avatar-file") as HTMLInputElement).onchange=async e=>{const input=e.target as HTMLInputElement,file=input.files?.[0];if(!file)return;try{if(file.type!=="image/png"||file.size>8000000)throw Error("Нужен PNG до 8 МБ");const data=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(",")[1]);reader.onerror=reject;reader.readAsDataURL(file)});await api("avatar",{png:data});useAvatar()}catch(err){$("info").textContent=String(err)}finally{input.value=""}};
const note=$("note-dialog") as HTMLDialogElement;
$("note-open").onclick=()=>{menu.hidden=true;$("note-status").textContent="";if(!note.open)note.showModal()};
$("note-save").onclick=async()=>{const btn=$("note-save") as HTMLButtonElement;if(btn.disabled)return;const field=$("note-text") as HTMLTextAreaElement,content=field.value.trim(),kind=Number(($("note-kind") as HTMLSelectElement).value);if(!content){$("note-status").textContent="Введите текст.";field.focus();return}btn.disabled=true;try{await api("note",{kind,content});field.value="";if(note.open)note.close();void refreshGraph()}catch(err){if(note.open)$("note-status").textContent=String(err)}finally{btn.disabled=false}};


// Reading is a separate local presentation of the same immutable SQLite bookmark.
type NovelDocument={chapter:number,last_chapter:number,title:string,volume:number,text:string,hash:string,offset:number,latest:number,volume_count:number,volume_ordinal:number,parts:number,epoch:number,segments:{number:number,start:number,end:number,hash:string}[]};
type BookPage={chapter:number,title:string,volume:number,page:number,pages:number,text:string,chapter_progress:number,volume_progress:number,can_back:boolean,can_next:boolean,last_published:boolean,document?:NovelDocument|null};
const book=$("book"),scroll=$("book-scroll");
let font=21,spacing=1.8,focused=false,reading=false;
let novelDoc:NovelDocument|null=null,novelPages:{start:number,end:number,text:string}[]=[],novelIndex=0,layoutKey="",reflowTimer=0,positionChain:Promise<unknown>=Promise.resolve();
let readerGeneration=0;
try{const saved=JSON.parse(localStorage.getItem("hakureya-reading-style")||"{}");if(Number.isFinite(saved.font))font=Math.min(32,Math.max(16,saved.font===18&&!saved.largeUI?21:saved.font));if(Number.isFinite(saved.spacing))spacing=Math.min(2.2,Math.max(1.5,saved.spacing))}catch{}
function readerStyle(){book.style.setProperty("--book-font",font+"px");book.style.setProperty("--book-spacing",String(spacing));try{localStorage.setItem("hakureya-reading-style",JSON.stringify({font,spacing,largeUI:true}))}catch{}scheduleReflow()}
readerStyle();
function renderProse(text:string){
 const body=$("book-text");body.replaceChildren();
 for(const paragraph of text.split(/\n\s*\n/)){
  if(!paragraph.trim())continue;
  const el=document.createElement("p");el.textContent=paragraph;body.append(el);
 }
}
function animatePage(){
 scroll.scrollTop=0;
 $("book-page").animate?.([{opacity:.38,transform:"translateY(4px)"},{opacity:1,transform:"none"}],{duration:window.matchMedia("(prefers-reduced-motion: reduce)").matches?0:180});
}
function heading(first:boolean){
 $("book-title").hidden=!first;
 $("book-ornament").hidden=!first;
}
function savePosition(){
 const d=novelDoc,p=novelPages[novelIndex],generation=readerGeneration;
 if(!d||!p||book.hidden||chat.hidden)return Promise.resolve();
 positionChain=positionChain.catch(()=>{}).then(async()=>{
  if(generation!==readerGeneration)return;
  await api("reader",{action:"position",hash:d.hash,start:p.start,end:p.end});
 }).catch(e=>{if(generation===readerGeneration&&!book.hidden)$("book-status").textContent="Закладка: "+String(e)});
 return positionChain;
}
function renderNovelPage(animate=false){
 const d=novelDoc,p=novelPages[novelIndex];if(!d||!p)return;
 heading(novelIndex===0);renderProse(p.text);
 const length=Array.from(d.text).length;
 const progress=length?p.end/length:1;
 $("book-position").textContent="Страница "+(novelIndex+1)+" из "+novelPages.length;
 ($("book-progress") as HTMLProgressElement).value=progress;
 ($("book-volume") as HTMLProgressElement).value=Math.min(1,(d.volume_ordinal-1+progress*d.parts)/Math.max(1,d.volume_count));
 ($("book-prev") as HTMLButtonElement).disabled=novelIndex===0&&d.chapter===1;
 ($("book-next") as HTMLButtonElement).disabled=novelIndex===novelPages.length-1&&d.last_chapter>=d.latest;
 $("book-end").hidden=!(novelIndex===novelPages.length-1&&d.last_chapter>=d.latest);
 $("book-status").textContent="";
 if(animate)animatePage();else scroll.scrollTop=0;
}
function reflowNovel(anchor?:number,animate=false){
 const d=novelDoc;if(!d||book.hidden||chat.hidden)return;
 const width=scroll.clientWidth,available=scroll.clientHeight;
 if(available<1||width<1)return;
 const pageWidth=Math.min(width,210*96/25.4,available*210/297),height=pageWidth*297/210;
 $("book-page").style.setProperty("--a4-width",pageWidth+"px");
 const offset=anchor??novelPages[novelIndex]?.start??d.offset;
 const key=[d.hash,width,height,font,spacing,offset].join(":");
 if(key===layoutKey&&novelPages.length)return;
 layoutKey=key;
 $("book-end").hidden=true;
 novelPages=measuredPages(d.text,(text,start)=>{
  heading(start===0);renderProse(text);
  return $("book-page").getBoundingClientRect().height<=height+1;
 },offset);
 novelIndex=pageAt(novelPages,offset);
 renderNovelPage(animate);
 void savePosition();
}
function scheduleReflow(){
 clearTimeout(reflowTimer);
 if(!novelDoc||book.hidden||chat.hidden)return;
 reflowTimer=window.setTimeout(()=>reflowNovel(),100);
}
function showBook(p:BookPage){
 readerGeneration++;
 book.hidden=false;chat.classList.add("reading");syncGraphViewport();$("messages").hidden=true;$("composer").hidden=true;$("chat-status-row").hidden=true;
 novelDoc=p.document||null;novelPages=[];novelIndex=0;layoutKey="";
 const d=novelDoc;
 $("book-kicker").textContent="ТОМ "+(d?.volume??p.volume)+" · ГЛАВА "+(d?.chapter??p.chapter);
 $("book-title").textContent=d?.title??p.title;
 heading(true);
 if(d&&!chat.hidden&&scroll.clientHeight>0){reflowNovel(d.offset,true);return}
 renderProse(p.text);
 $("book-position").textContent="Страница "+p.page+" из "+p.pages;
 ($("book-progress") as HTMLProgressElement).value=p.chapter_progress;
 ($("book-volume") as HTMLProgressElement).value=p.volume_progress;
 ($("book-prev") as HTMLButtonElement).disabled=!p.can_back;
 ($("book-next") as HTMLButtonElement).disabled=!p.can_next;
 $("book-end").hidden=!p.last_published;$("book-status").textContent="";
 animatePage();scheduleReflow();
}
function exitBook(){readerGeneration++;novelDoc=null;novelPages=[];layoutKey="";book.hidden=true;chat.classList.remove("reading","book-focus");focused=false;syncGraphViewport();$("book-focus").setAttribute("aria-pressed","false");$("messages").hidden=false;$("composer").hidden=false;$("chat-status-row").hidden=false;prompt.focus()}
async function turn(action:string){
 if(reading||busy)return;
 reading=true;
 try{
  if(novelDoc&&novelPages.length&&(action==="next"||action==="back")){
   const delta=action==="next"?1:-1,next=novelIndex+delta;
   if(next>=0&&next<novelPages.length){novelIndex=next;renderNovelPage(true);await savePosition();return}
   if(delta>0&&novelDoc.last_chapter>=novelDoc.latest)return;
   if(delta<0&&novelDoc.chapter===1)return;
   action=delta>0?"advance":"retreat";
  }
  await positionChain;
  const generation=readerGeneration;
  const result=await api("reader",{action});
  if(generation!==readerGeneration)return;
  if(action==="pause"){exitBook();return}
  if(result.reader)showBook(result.reader);
  else $("book-status").textContent=result.reply||"Страница недоступна";
 }catch(e){$("book-status").textContent=String(e)}finally{reading=false}
}
let presenceBusy=false;
async function readerPresence(){
 if(presenceBusy||reading||busy||book.hidden||chat.hidden||document.hidden)return;
 presenceBusy=true;
 const generation=readerGeneration;
 try{
  await positionChain;
  const result=await api("reader",{action:"presence"});
  if(generation!==readerGeneration||reading||book.hidden||chat.hidden)return;
  const incoming:NovelDocument|undefined=result.reader?.document;
  if(!incoming||!novelDoc)return;
  if(incoming.chapter!==novelDoc.chapter)return;
  if(incoming.hash!==novelDoc.hash){
   const anchor=novelPages[novelIndex]?.start??incoming.offset;
   novelDoc=incoming;layoutKey="";reflowNovel(anchor);
  }else if(incoming.latest!==novelDoc.latest||incoming.volume_count!==novelDoc.volume_count){
   novelDoc=incoming;renderNovelPage();
  }
 }catch{}finally{presenceBusy=false}
}
if(typeof ResizeObserver==="function"){const observer=new ResizeObserver(scheduleReflow);observer.observe(scroll)}
else window.addEventListener("resize",scheduleReflow);
setInterval(()=>void readerPresence(),10000);
$("book-prev").onclick=()=>void turn("back");$("book-next").onclick=()=>void turn("next");$("book-exit").onclick=()=>void turn("pause");
$("book-smaller").onclick=()=>{font=Math.max(16,font-1);readerStyle()};
$("book-larger").onclick=()=>{font=Math.min(32,font+1);readerStyle()};
$("book-spacing").onclick=()=>{spacing=spacing>=2.15?1.5:Math.min(2.2,Math.round((spacing+.15)*100)/100);readerStyle()};
$("book-focus").onclick=()=>{focused=!focused;chat.classList.toggle("book-focus",focused);syncGraphViewport();scheduleReflow();$("book-focus").setAttribute("aria-pressed",String(focused))};
document.addEventListener("keydown",e=>{if(book.hidden||chat.hidden||config.open||writerDialog.open||commandDialog.open||universeDialog.open||note.open||e.altKey||e.ctrlKey||e.metaKey||e.shiftKey||e.repeat||window.getSelection()?.toString())return;if(e.target instanceof HTMLInputElement||e.target instanceof HTMLTextAreaElement||e.target instanceof HTMLButtonElement)return;if(e.key==="ArrowRight"||e.key==="ArrowLeft"){e.preventDefault();void turn(e.key==="ArrowRight"?"next":"back")}});
let touch:{x:number,y:number}|null=null;
scroll.addEventListener("touchstart",e=>{touch=e.touches.length===1?{x:e.touches[0].clientX,y:e.touches[0].clientY}:null},{passive:true});
scroll.addEventListener("touchcancel",()=>{touch=null},{passive:true});
scroll.addEventListener("touchend",e=>{const start=touch;touch=null;if(!start||e.changedTouches.length!==1||window.getSelection()?.toString())return;const dx=e.changedTouches[0].clientX-start.x,dy=e.changedTouches[0].clientY-start.y;if(Math.abs(dx)>85&&Math.abs(dx)>Math.abs(dy)*2)void turn(dx<0?"next":"back")},{passive:true});
void init();
// Initialize optional visualization only after all chat and reader handlers are registered.
ensureGraph();void refreshGraph();void refreshActivity();scheduleActivity();
setInterval(()=>{if(!document.hidden)void refreshGraph()},12000);
