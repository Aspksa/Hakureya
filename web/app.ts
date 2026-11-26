import "./style.css";
import {mountGraph} from "./live-graph";
const $=(id:string)=>document.getElementById(id)!;
const live=mountGraph($("graph") as unknown as SVGSVGElement,$("info"));
let busy=false;
$("replay").onclick=()=>live.replay();$("reset").onclick=()=>{live.replay();$("menu").hidden=true};
let graphRequest=0;
async function refreshGraph(){const id=++graphRequest;try{const data=await api("graph");if(id===graphRequest)live.render(data)}catch{if(id===graphRequest)$("info").textContent="Память недоступна"}}
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
function toggle(open=chat.hidden){chat.hidden=!open;avatar.setAttribute("aria-expanded",String(open));avatar.setAttribute("aria-label",open?"Свернуть чат":"Открыть чат Hakureya");if(open)prompt.focus();else avatar.focus()}
avatar.onclick=()=>toggle();$("close").onclick=()=>toggle(false);avatar.oncontextmenu=e=>{e.preventDefault();menu.hidden=!menu.hidden};document.addEventListener("keydown",e=>{if(e.key==="Escape"){if(!menu.hidden)menu.hidden=true;else if(!chat.hidden&&!config.open)toggle(false)}});document.addEventListener("click",e=>{if(!menu.contains(e.target as Node)&&!avatar.contains(e.target as Node))menu.hidden=true});
function message(role:string,content:string){const p=document.createElement("p");p.className="message "+role;p.textContent=content;$("messages").append(p);p.scrollIntoView({block:"end"});return p}
async function api(path:string,data?:unknown){const response=await fetch("/api/"+path,data===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});const value=await response.json();if(!response.ok)throw Error(value.error||"Ошибка сервера");return value}
async function init(){try{const data=await api("history");for(const m of data.messages)message(m.role,m.content);$("status").textContent=data.connected?"Cloud.ru подключён":"Локальный режим · Cloud.ru не подключён"}catch{$("status").textContent="Сервер недоступен"}}void init();void refreshGraph();setInterval(()=>{if(!document.hidden)void refreshGraph()},12000);
$("settings").onclick=()=>{menu.hidden=true;config.showModal()};$("save").onclick=async()=>{const model=($("model") as HTMLInputElement).value.trim(),key=$("key") as HTMLInputElement,consent=($("consent") as HTMLInputElement).checked;try{await api("config",{model,key:key.value,consent});key.value="";$("status").textContent="Cloud.ru подключён";$("config-status").textContent="Настройки сохранены";config.close()}catch(e){$("config-status").textContent=String(e)}};
$("composer").onsubmit=async e=>{e.preventDefault();const content=prompt.value.trim();if(!content||busy)return;busy=true;prompt.value="";message("user",content);$("status").textContent="Обработка запроса…";try{const result=await api("chat",{content});message("assistant",result.reply);$("status").textContent=result.connected?"Cloud.ru · ответ получен":"Локальный режим · сообщение сохранено"}catch(e){message("error",String(e));$("status").textContent="Ошибка запроса"}finally{busy=false;await refreshGraph();prompt.focus()}};

const image=$("avatar-image") as HTMLImageElement;
function useAvatar(){image.src="/api/avatar?"+Date.now();image.onerror=()=>{image.onerror=null;image.src="/avatar.svg"}}
useAvatar();
$("avatar-picker").onclick=()=>{menu.hidden=true;($("avatar-file") as HTMLInputElement).click()};
($("avatar-file") as HTMLInputElement).onchange=async e=>{const input=e.target as HTMLInputElement,file=input.files?.[0];if(!file)return;try{if(file.type!=="image/png"||file.size>8000000)throw Error("Нужен PNG до 8 МБ");const data=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(",")[1]);reader.onerror=reject;reader.readAsDataURL(file)});await api("avatar",{png:data});useAvatar()}catch(err){$("info").textContent=String(err)}finally{input.value=""}};
const note=$("note-dialog") as HTMLDialogElement;
$("note-open").onclick=()=>{menu.hidden=true;note.showModal()};
$("note-save").onclick=async()=>{const content=($("note-text") as HTMLTextAreaElement).value,kind=Number(($("note-kind") as HTMLSelectElement).value);try{await api("note",{kind,content});($("note-text") as HTMLTextAreaElement).value="";note.close();await refreshGraph()}catch(err){$("note-status").textContent=String(err)}};
