import "./style.css";
import {mountGraph} from "./live-graph";
const $=(id:string)=>document.getElementById(id)!;
let selectedVolume:number|null=null;
const live=mountGraph($("graph") as unknown as SVGSVGElement,$("info"),volume=>{selectedVolume=volume;void refreshGraph()});
let busy=false;
$("replay").onclick=()=>{selectedVolume=null;void refreshGraph().then(()=>live.replay())};$("reset").onclick=()=>{selectedVolume=null;void refreshGraph().then(()=>live.replay());$("menu").hidden=true};
let graphRequest=0;
async function refreshGraph(){const id=++graphRequest;try{const data=await api(selectedVolume===null?"graph":"graph/volume/"+selectedVolume);if(id===graphRequest)live.render(data)}catch{if(id===graphRequest)$("info").textContent="Область недоступна · ↻ для общей карты"}}
let activityBusy=false,activityRevision="",activityTimer=0,activityActive=false;
async function refreshActivity(){
 if(document.hidden||activityBusy)return;
 activityBusy=true;
 try{
  const controller=new AbortController(),timeout=window.setTimeout(()=>controller.abort(),3000);
  let data;try{const response=await fetch("/api/activity",{cache:"no-store",signal:controller.signal});if(!response.ok)throw Error("activity");data=await response.json()}finally{clearTimeout(timeout)}
  if(document.hidden)return;
  activityActive=data.active.length>0;
  live.setActivity(data);
  const revision=data.session+":"+data.revision;
  if(revision!==activityRevision){activityRevision=revision;void refreshGraph()}
 }catch{activityRevision="";activityActive=false;live.clearActivity()}finally{activityBusy=false}
}
function scheduleActivity(){clearTimeout(activityTimer);if(document.hidden)return;activityTimer=window.setTimeout(async()=>{await refreshActivity();scheduleActivity()},activityActive||busy?400:1200)}
document.addEventListener("visibilitychange",()=>{clearTimeout(activityTimer);if(!document.hidden){void refreshGraph();void refreshActivity();scheduleActivity()}});
void refreshActivity();scheduleActivity();
const avatar=$("avatar"),chat=$("chat"),prompt=$("prompt") as HTMLTextAreaElement,menu=$("menu"),config=$("config") as HTMLDialogElement;
function toggle(open=chat.hidden){chat.hidden=!open;avatar.setAttribute("aria-expanded",String(open));avatar.setAttribute("aria-label",open?"Свернуть чат":"Открыть чат Hakureya");if(open){if(!book.hidden)$("book-scroll").focus();else prompt.focus()}else avatar.focus()}
avatar.onclick=()=>toggle();$("close").onclick=()=>toggle(false);avatar.oncontextmenu=e=>{e.preventDefault();menu.hidden=!menu.hidden};document.addEventListener("keydown",e=>{if(e.key==="Escape"){if(!menu.hidden)menu.hidden=true;else if(!chat.hidden&&!config.open)toggle(false)}});document.addEventListener("click",e=>{if(!menu.contains(e.target as Node)&&!avatar.contains(e.target as Node))menu.hidden=true});
function message(role:string,content:string){const p=document.createElement("p");p.className="message "+role;p.textContent=content;$("messages").append(p);p.scrollIntoView({block:"end"});return p}
async function api(path:string,data?:unknown){const response=await fetch("/api/"+path,data===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});const value=await response.json();if(!response.ok)throw Error(value.error||"Ошибка сервера");return value}
async function init(){try{const data=await api("history");for(const m of data.messages)message(m.role,m.content);$("status").textContent=data.connected?"Cloud.ru подключён":"Локальный режим · Cloud.ru не подключён";const page=await api("reader");if(page.reader&&!busy)showBook(page.reader)}catch{$("status").textContent="Сервер недоступен"}}void refreshGraph();setInterval(()=>{if(!document.hidden)void refreshGraph()},12000);
$("settings").onclick=()=>{menu.hidden=true;config.showModal()};$("save").onclick=async()=>{const model=($("model") as HTMLInputElement).value.trim(),key=$("key") as HTMLInputElement,consent=($("consent") as HTMLInputElement).checked;try{await api("config",{model,key:key.value,consent});key.value="";$("status").textContent="Cloud.ru подключён";$("config-status").textContent="Настройки сохранены";config.close()}catch(e){$("config-status").textContent=String(e)}};
$("composer").onsubmit=async e=>{e.preventDefault();const content=prompt.value.trim();if(!content||busy)return;busy=true;prompt.value="";message("user",content);$("status").textContent="Обработка запроса…";try{const result=await api("chat",{content});if(result.reader)showBook(result.reader);else message("assistant",result.reply);$("status").textContent=result.connected?"Cloud.ru · ответ получен":"Локальный режим · сообщение сохранено"}catch(e){message("error",String(e));$("status").textContent="Ошибка запроса"}finally{busy=false;await refreshGraph();if(book.hidden)prompt.focus();else $("book-scroll").focus()}};

const image=$("avatar-image") as HTMLImageElement;
function useAvatar(){image.src="/api/avatar?"+Date.now();image.onerror=()=>{image.onerror=null;image.src="/avatar.svg"}}
useAvatar();
$("avatar-picker").onclick=()=>{menu.hidden=true;($("avatar-file") as HTMLInputElement).click()};
($("avatar-file") as HTMLInputElement).onchange=async e=>{const input=e.target as HTMLInputElement,file=input.files?.[0];if(!file)return;try{if(file.type!=="image/png"||file.size>8000000)throw Error("Нужен PNG до 8 МБ");const data=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(",")[1]);reader.onerror=reject;reader.readAsDataURL(file)});await api("avatar",{png:data});useAvatar()}catch(err){$("info").textContent=String(err)}finally{input.value=""}};
const note=$("note-dialog") as HTMLDialogElement;
$("note-open").onclick=()=>{menu.hidden=true;note.showModal()};
$("note-save").onclick=async()=>{const content=($("note-text") as HTMLTextAreaElement).value,kind=Number(($("note-kind") as HTMLSelectElement).value);try{await api("note",{kind,content});($("note-text") as HTMLTextAreaElement).value="";note.close();await refreshGraph()}catch(err){$("note-status").textContent=String(err)}};


// Reading is a separate local presentation of the same immutable SQLite bookmark.
type BookPage={chapter:number,title:string,volume:number,page:number,pages:number,text:string,chapter_progress:number,volume_progress:number,can_back:boolean,can_next:boolean,last_published:boolean};
const book=$("book"),scroll=$("book-scroll");
let font=18,spacing=1.8,focused=false,reading=false;
try{const saved=JSON.parse(localStorage.getItem("hakureya-reading-style")||"{}");if(Number.isFinite(saved.font))font=Math.min(26,Math.max(15,saved.font));if(Number.isFinite(saved.spacing))spacing=Math.min(2.2,Math.max(1.5,saved.spacing))}catch{}
function readerStyle(){book.style.setProperty("--book-font",font+"px");book.style.setProperty("--book-spacing",String(spacing));try{localStorage.setItem("hakureya-reading-style",JSON.stringify({font,spacing}))}catch{}}
readerStyle();
function showBook(p:BookPage){
 book.hidden=false;chat.classList.add("reading");$("messages").hidden=true;$("composer").hidden=true;$("status").hidden=true;
 $("book-kicker").textContent="ТОМ "+p.volume+" · ГЛАВА "+p.chapter;
 $("book-title").textContent=p.title;
 // Never interpret model output as HTML. Keep paragraph and dialogue boundaries.
 const body=$("book-text");body.replaceChildren();
 for(const paragraph of p.text.split(/\n\s*\n/)){
  const el=document.createElement("p");el.textContent=paragraph;body.append(el);
 }
 $("book-position").textContent="Страница "+p.page+" из "+p.pages;
 ($("book-progress") as HTMLProgressElement).value=p.chapter_progress;
 ($("book-volume") as HTMLProgressElement).value=p.volume_progress;
 ($("book-prev") as HTMLButtonElement).disabled=!p.can_back;
 ($("book-next") as HTMLButtonElement).disabled=!p.can_next;
 $("book-end").hidden=!p.last_published;
 $("book-status").textContent="";
 scroll.scrollTop=0;
 $("book-page").animate([{opacity:.3,transform:"translateY(5px)"},{opacity:1,transform:"none"}],{duration:window.matchMedia("(prefers-reduced-motion: reduce)").matches?0:180});
}
function exitBook(){book.hidden=true;chat.classList.remove("reading","book-focus");focused=false;$("book-focus").setAttribute("aria-pressed","false");$("messages").hidden=false;$("composer").hidden=false;$("status").hidden=false;prompt.focus()}
async function turn(action:string){
 if(reading||busy)return;
 reading=true;
 try{const result=await api("reader",{action});if(action==="pause"){exitBook();return}if(result.reader){showBook(result.reader);if(!String(result.reply).includes(" · Страница "))$("book-status").textContent=result.reply}else $("book-status").textContent=result.reply||"Страница недоступна"}catch(e){$("book-status").textContent=String(e)}finally{reading=false}
}
$("book-prev").onclick=()=>void turn("back");$("book-next").onclick=()=>void turn("next");$("book-exit").onclick=()=>void turn("pause");
$("book-smaller").onclick=()=>{font=Math.max(15,font-1);readerStyle()};
$("book-larger").onclick=()=>{font=Math.min(26,font+1);readerStyle()};
$("book-spacing").onclick=()=>{spacing=spacing>=2.15?1.5:Math.min(2.2,Math.round((spacing+.15)*100)/100);readerStyle()};
$("book-focus").onclick=()=>{focused=!focused;chat.classList.toggle("book-focus",focused);$("book-focus").setAttribute("aria-pressed",String(focused))};
document.addEventListener("keydown",e=>{if(book.hidden||chat.hidden||config.open||e.altKey||e.ctrlKey||e.metaKey||e.shiftKey||e.repeat||window.getSelection()?.toString())return;if(e.target instanceof HTMLInputElement||e.target instanceof HTMLTextAreaElement||e.target instanceof HTMLButtonElement)return;if(e.key==="ArrowRight"||e.key==="ArrowLeft"){e.preventDefault();void turn(e.key==="ArrowRight"?"next":"back")}});
let touch:{x:number,y:number}|null=null;
scroll.addEventListener("touchstart",e=>{touch=e.touches.length===1?{x:e.touches[0].clientX,y:e.touches[0].clientY}:null},{passive:true});
scroll.addEventListener("touchcancel",()=>{touch=null},{passive:true});
scroll.addEventListener("touchend",e=>{const start=touch;touch=null;if(!start||e.changedTouches.length!==1||window.getSelection()?.toString())return;const dx=e.changedTouches[0].clientX-start.x,dy=e.changedTouches[0].clientY-start.y;if(Math.abs(dx)>85&&Math.abs(dx)>Math.abs(dy)*2)void turn(dx<0?"next":"back")},{passive:true});
void init();
