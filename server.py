from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from http.client import HTTPException
import argparse, json, sqlite3, threading, webbrowser, os
from contextlib import closing
import memory_graph
import soul_core
import soul_chronicle
import soul_saga
import soul_omega
import soul_genesis
import soul_romance
import soul_heart
import soul_shadow
import soul_reader
import soul_guardians
import soul_destiny
import soul_living
import cloud_writer
import soul_evolution
import soul_immortal
import soul_novel
import graph_activity
import time, re
import base64, binascii

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "hakureya.sqlite3"
API = "https://foundation-models.api.cloud.ru/v1/chat/completions"
LOCK = threading.Lock()
CONFIG = {"key": "", "model": ""}
CHRONICLE = {"enabled": False, "last_activity": time.monotonic(), "epoch": 0, "reader_seen": -1e9}


def normalize_cloud_key(value):
    if not isinstance(value,str):
        return None
    key=value.strip()
    if len(key)>4096 or any(not 33<=ord(char)<=126 for char in key):
        return None
    return key


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=10)
    db.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, role TEXT NOT NULL, content TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP)")
    memory_graph.init(db)
    soul_core.init(db)
    db.commit()
    return db

def history(limit=200):
    with closing(connect()) as db:
        rows = db.execute("SELECT role,content FROM messages ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [{"role": r, "content": c} for r,c in reversed(rows)]

def store(role, content):
    with closing(connect()) as db, db:
        cursor = db.execute("INSERT INTO messages(role,content) VALUES(?,?)", (role,content))
        message_id = cursor.lastrowid
        if role == "user":
            soul_core.observe_user(db,message_id,content)
        elif role == "assistant":
            soul_core.review_response(db,message_id,content)
            soul_chronicle.collect(db)
        return message_id

def reading_window(db):
    """Only explicitly enabled persistent writer mode, recent actual reading, near the published end."""
    if soul_living.mode(db)=="off" or time.monotonic()-CHRONICLE.get("reader_seen",-1e9)>100:
        return False
    row=soul_reader.bookmark(db)
    return bool(row and row[3] and row[0]>=soul_reader.latest(db)-1)

def generate_chronicle(background=False, arc=None, alternative=False, shadow=False, guardians=False, destiny=False):
    # Reserve quota and snapshot under lock; do not block chat during network I/O.
    with LOCK:
        if not CONFIG["key"]:
            return "Cloud.ru не подключён или фоновый сон не разрешён."
        with closing(connect()) as db, db:
            if background and not reading_window(db) and time.monotonic()-CHRONICLE["last_activity"]<soul_immortal.preferences(db)[1]:return "Ожидание фонового интервала."
            if background and not CHRONICLE["enabled"] and soul_living.mode(db)=="off":return "Автономное развитие выключено."
            soul_chronicle.collect(db)
            cycle=soul_romance.current_cycle(db)
            if (shadow or guardians or destiny) and cycle:
                return "Сначала завершите открытый литературный цикл. Сага о защитнике продолжится после этого."
            if cycle and arc and arc!=cycle["arc"]:
                return "Сначала завершите открытый художественный цикл или продолжите его сюжетную линию."
            if cycle: arc=cycle["arc"]
            shadow_plan=soul_shadow.plan(db) if not cycle and not alternative and (shadow or arc is None) and not soul_shadow.audit(db) else None
            guardian_plan=soul_guardians.plan(db) if not cycle and not alternative and (guardians or shadow or arc is None) else None
            destiny_plan=soul_destiny.plan(db) if not cycle and not alternative and (destiny or shadow or arc is None) else None
            if destiny and not destiny_plan:return soul_destiny.status(db)
            if guardians and not guardian_plan:return soul_guardians.status(db)
            if guardian_plan:shadow_plan=None
            if shadow and not (shadow_plan or guardian_plan or destiny_plan) and (soul_destiny.audit(db) or len(soul_destiny.published(db))!=len(soul_destiny.ORDER)):return "Сюжетные данные повреждены или продолжение недоступно."
            if shadow_plan or guardian_plan or destiny_plan:arc="future"
            elif arc is None and not alternative and not soul_destiny.audit(db) and len(soul_destiny.published(db))==len(soul_destiny.ORDER):arc="future"
            reservation=soul_chronicle.reserve(db,allow_story=True) if not (soul_genesis.audit(db)+soul_heart.audit(db)+soul_shadow.audit(db)+soul_guardians.audit(db)+soul_destiny.audit(db)+soul_living.audit(db)+soul_evolution.audit(db)+soul_immortal.audit(db)+soul_novel.audit(db)) else None
            traits=soul_chronicle.profile(db)
            plan=soul_genesis.enrich(db,soul_omega.enrich_plan(db,soul_saga.plan(db,arc))) if reservation else None
            if plan:
                soul_romance.enrich(db,plan)
                soul_heart.enrich(db,plan)
                plan["alternative"]=alternative
                if shadow_plan:plan["shadow"]=shadow_plan
                if destiny_plan:plan["destiny"]=destiny_plan
                if guardian_plan:plan["guardians"]=guardian_plan
                else:plan["guardian_guard"]=soul_guardians.guard(db,plan["arc"])
                if not shadow_plan:plan["shadow_guard"]=soul_shadow.guard(db,plan["arc"])
                if not alternative:
                    soul_living.enrich(db,plan,background)
                    soul_evolution.enrich(db,plan)
                    soul_immortal.enrich(db,plan)
                    soul_novel.enrich(db,plan)
            previous=[]
            if plan:
                previous=[{"number":n,"title":t,"story":s[-2200:]} for n,t,s in reversed(db.execute("SELECT number,title,story FROM omega_index WHERE arc=? AND number>13 ORDER BY number DESC LIMIT 2",(plan["arc"],)).fetchall())]
                previous.append({"published_titles":[t for t, in db.execute("SELECT title FROM omega_index ORDER BY number DESC LIMIT 12")]})
            writer=cloud_writer.selected(db)
            if reservation:
                model=writer or CONFIG["model"]
                allowed,cost=soul_evolution.budget_check(db,model,soul_chronicle.prompt(reservation,traits,previous,plan),cloud_writer.LIMIT,reservation[0])
                if not allowed:
                    db.execute("DELETE FROM chronicle_attempts WHERE day=? AND status='reserved'",(reservation[0],))
                    return "Литературный запрос остановлен: проверьте денежный лимит или тариф модели."
                soul_evolution.reserve_cost(db,reservation[0],model,cost)
        if not reservation:
            return "Есть незавершённая попытка или ожидающий черновик, нарушена целостность канона либо исчерпан дневной лимит."
        key, model, epoch=CONFIG["key"],writer or CONFIG["model"],CHRONICLE["epoch"]
    with graph_activity.track("chronicle",("destiny:root" if destiny_plan else "guardians:root" if guardian_plan else "shadow:root" if shadow_plan else (f"d:{reservation[1]}" if reservation[1]>0 else ("heart:root" if plan["arc"]=="love" else "living:root" if plan.get("living") and plan["arc"]=="future" else "arc:"+plan["arc"])))) as activity:
        return execute_chronicle(reservation,traits,previous,key,model,epoch,activity,plan)

def execute_chronicle(reservation,traits,previous,key,model,epoch,activity,plan):
    try:
        payload={"model":model,"messages":soul_chronicle.prompt(reservation,traits,previous,plan),"max_tokens":cloud_writer.LIMIT,"stream":False}
        req=Request(API,data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
        graph_activity.update(activity,"waiting")
        with urlopen(req,timeout=60) as res:
            result=json.loads(res.read(1_000_000))
        graph_activity.update(activity,"validating","hub:4")
        with LOCK, closing(connect()) as db, db:
            cloud_writer.usage(db,reservation[0],model,result)
            soul_evolution.settle_cost(db,reservation[0],result)
        if result["choices"][0].get("finish_reason")=="length":raise ValueError("incomplete literary response")
        raw=result["choices"][0]["message"]["content"]
        if not isinstance(raw,str) or len(raw)>24000:
            raise ValueError("invalid draft")
        value=json.loads(raw)
        with LOCK, closing(connect()) as db, db:
            if CHRONICLE["epoch"]!=epoch:
                soul_chronicle.fail(db,reservation)
                graph_activity.update(activity,"discarded")
                return "Настройки изменились; черновик отброшен."
            soul_chronicle.finish(db,reservation,value,plan)
            pending=soul_chronicle.latest_pending(db)
            editorial=soul_omega.metadata(db,pending["id"])
            scene_report=soul_romance.report(db,pending["id"])
            shadow_saved=soul_shadow.read(db,pending["id"])
            guardian_saved=soul_guardians.read(db,pending["id"])
            destiny_saved=soul_destiny.read(db,pending["id"])
            variants=db.execute("SELECT COUNT(*) FROM genesis_variants WHERE draft_id=?",(pending["id"],)).fetchone()[0]
            auto_published=False
            if plan.get("living",{}).get("background") and soul_living.mode(db)=="auto":
                auto_published=soul_living.publish_if_allowed(db,pending["id"])
            if auto_published:
                number=db.execute("SELECT number FROM saga_arcs WHERE draft_id=?",(pending["id"],)).fetchone()[0]
        graph_activity.update(activity,"done",f"c:{pending['id']}" if auto_published else f"draft:{pending['id']}" if pending else "hub:4")
        if auto_published:return f"Глава {number} опубликована: "+pending["title"]
        if plan.get("destiny"):
            return "Черновик создан.\n\n"+pending["title"]+"\n\n"+pending["story"]+"\n\n"+("Принять главу / Отклонить главу." if destiny_saved else "Этап ещё не завершён. Принять главу / Отклонить главу.")
        if plan.get("guardians"):
            return "Черновик создан.\n\n"+pending["title"]+"\n\n"+pending["story"]+"\n\n"+("Этап хранительниц отмечен цитатой." if guardian_saved else "Следующий этап пока не открыт.")+"\nПринять главу / Отклонить главу."
        if plan.get("shadow"):
            return "Черновик создан.\n\n"+pending["title"]+"\n\n"+pending["story"]+"\n\n"+("Этап сюжета подтверждён цитатой." if shadow_saved else "Этап ещё не завершён; следующий пока не откроется.")+"\nПринять главу / Отклонить главу. Оценки: летопись: качество."
        return "Черновик создан. "+soul_saga.ARC_LABELS[plan["arc"]]+".\n\n"+pending["title"]+"\n\n"+pending["story"]+("\n\nЕсть варианты: летопись: варианты" if variants else "")+"\n\nПринять главу / Отклонить главу. Оценки: летопись: качество / летопись: оригинальность."
    except (URLError,TimeoutError,ValueError,KeyError,IndexError,TypeError,OSError,sqlite3.Error):
        with LOCK, closing(connect()) as db, db:
            soul_chronicle.fail(db,reservation)
            soul_living.log(db,"generation_failed","Неудачная попытка учтена; повтор не раньше следующего дня UTC")
        graph_activity.update(activity,"error")
        return "Черновик не создан: ответ модели не прошёл проверку или запрос завершился ошибкой. Дневная попытка учтена."

def independent_editor():
    """Explicit request shares the writer's daily quota; no implicit extra model calls."""
    with LOCK:
        if not CONFIG["key"]:return "Сначала подключите Cloud.ru."
        with closing(connect()) as db, db:
            if not soul_chronicle.canon_ok(db) or soul_genesis.audit(db) or soul_immortal.audit(db):return "Проверка остановлена: повреждён канон или история."
            draft=soul_chronicle.latest_pending(db)
            if not draft:return "Нет черновика для редактора."
            did=draft["id"]
            source=db.execute("SELECT checksum FROM chronicle_drafts WHERE id=?",(did,)).fetchone()[0]
            model=cloud_writer.selected(db) or CONFIG["model"]
            day=datetime.now(timezone.utc).date().isoformat()
            if db.execute("SELECT 1 FROM chronicle_attempts WHERE day=? OR status='reserved'",(day,)).fetchone():return "Суточная попытка уже использована. Редактор не запускался."
            messages=soul_immortal.editor_prompt(db,draft)
            allowed,cost=soul_evolution.budget_check(db,model,messages,cloud_writer.LIMIT,day)
            if not allowed:return "Редактор остановлен: проверьте бюджет или тариф модели."
            seed=db.execute("SELECT MIN(diary_id) FROM chronicle_attempts").fetchone()[0]
            db.execute("INSERT INTO chronicle_attempts(day,diary_id,status) VALUES(?,?,'reserved')",(day,min(0,seed or 0)-1))
            soul_evolution.reserve_cost(db,day,model,cost)
        key,epoch=CONFIG["key"],CHRONICLE["epoch"]
    try:
        req=Request(API,data=json.dumps({"model":model,"messages":messages,"max_tokens":cloud_writer.LIMIT,"stream":False}).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
        with urlopen(req,timeout=60) as res:
            result=json.loads(res.read(1_000_000))
        with LOCK, closing(connect()) as db, db:
            cloud_writer.usage(db,day,model,result)
            soul_evolution.settle_cost(db,day,result)
        choice=result["choices"][0]
        raw=choice["message"]["content"]
        if choice.get("finish_reason")=="length" or not isinstance(raw,str) or len(raw)>24000:raise ValueError("incomplete report")
        value=json.loads(raw)
        with LOCK, closing(connect()) as db, db:
            if CHRONICLE["epoch"]!=epoch:raise ValueError("settings changed")
            soul_immortal.editor_save(db,did,model,value,source)
            db.execute("UPDATE chronicle_attempts SET status='reviewed' WHERE day=? AND status='reserved'",(day,))
            return soul_immortal.editor_text(db,did)
    except (URLError,TimeoutError,ValueError,KeyError,IndexError,TypeError,OSError,sqlite3.Error):
        with LOCK, closing(connect()) as db, db:
            db.execute("UPDATE chronicle_attempts SET status='failed' WHERE day=? AND status='reserved'",(day,))
        return "Редактор не завершил проверку. Черновик сохранён, дневная попытка учтена."

def chronicle_command(content):
    q=" ".join(content.strip().casefold().split()).rstrip(".!?")
    aliases={"оглавление":"летопись: содержание","покажи оглавление":"летопись: содержание","прочитать последнюю главу":"летопись: последняя","покажи последнюю главу":"летопись: последняя","создай новую главу":"летопись: создать","продолжи нашу историю любви":"летопись: создать любовь"}
    aliases.update({"летопись":"летопись: помощь","что дальше по сюжету":"летопись: сага","план саги":"летопись: сага план","продолжи сагу":"летопись: создать сагу","напиши следующую главу":"летопись: создать","покажи черновик":"летопись: черновик","продолжить чтение":"летопись: продолжить чтение","история любви":"летопись: сердце","принять главу":"летопись: принять текущую","отклонить главу":"летопись: отклонить текущую"})
    aliases.update({"девять хранительниц":"летопись: хранительницы","хранительницы":"летопись: хранительницы","продолжи историю хранительниц":"летопись: создать хранительниц","план хранительниц":"летопись: план хранительниц"})
    aliases.update({"за пределами девяти небес":"летопись: судьба","план судьбы":"летопись: план судьбы","новые герои":"летопись: новые герои","продолжи судьбу":"летопись: создать судьбу","история силы":"летопись: судьба сила","путешествия":"летопись: судьба путешествия","развитие императрицы":"летопись: судьба развитие"})
    q=aliases.get(q,q)
    if q in ("модель писателя","расход писателя","модели cloud.ru","подключи писателя","модель писателя как в чате") or q.startswith("модель писателя "):
        if q in ("модель писателя","расход писателя","модель писателя как в чате"):
            with LOCK, closing(connect()) as db, db:
                if q=="расход писателя":return cloud_writer.usage_text(db)
                if q=="модель писателя как в чате":
                    cloud_writer.choose(db,"")
                    CHRONICLE["epoch"]+=1
                    return "Писатель использует модель обычного чата."
                return "Модель писателя: "+(cloud_writer.selected(db) or CONFIG["model"] or "не выбрана")+". Рекомендация: GLM-5.3. Подключение: «Подключи писателя»."
        with LOCK:
            key,epoch=CONFIG["key"],CHRONICLE["epoch"]
        if not key:return "Сначала подключите API-ключ Cloud.ru в существующих настройках аватара."
        try:ids=cloud_writer.list_models(key,urlopen)
        except (URLError,ValueError,KeyError,TypeError,OSError):return "Не удалось получить список моделей Cloud.ru. Проверьте ключ и доступ к Foundation Models."
        if q=="модели cloud.ru":return "Модели, доступные по API:\n"+"\n".join(ids[:150]) if ids else "Список моделей пуст."
        requested=cloud_writer.PREFERRED if q=="подключи писателя" else q[len("модель писателя "):].strip()
        model=cloud_writer.match(ids,requested)
        if not model:return "Модель не найдена однозначно. Напишите «Модели Cloud.ru», затем укажите точный идентификатор: «Модель писателя ID». Прежняя модель сохранена."
        with LOCK, closing(connect()) as db, db:
            if CONFIG["key"]!=key or CHRONICLE["epoch"]!=epoch:return "Настройки изменились; повторите выбор модели."
            cloud_writer.choose(db,model)
            CHRONICLE["epoch"]+=1
        return "Модель писателя выбрана: "+model+". Платный запрос не выполнялся. Модель чата не изменена."
    evolution_style=re.fullmatch(r"стиль романа (баланс|романтика|приключения|интриги)",q)
    evolution_preference=re.fullmatch(r"больше (любви|хранительниц|магии|миров|интриг|загадок|развития|героев)",q)
    evolution_profile=re.fullmatch(r"судьба персонажа (.{2,60})",q)
    evolution_archive=re.fullmatch(r"архив судеб ([1-9][0-9]{0,5})",q)
    evolution_volume=re.fullmatch(r"аннотация тома ([1-9][0-9]{0,5})",q)
    evolution_format=re.fullmatch(r"формат главы (короткая|обычная|большая|романтическая)",q)
    evolution_budget=re.fullmatch(r"бюджет писателя ([1-9][0-9]{0,5}) тариф ([1-9][0-9]{0,5}) ([1-9][0-9]{0,5})",q)
    if evolution_style or evolution_preference or evolution_profile or evolution_volume or evolution_archive or evolution_format or evolution_budget or q in ("бюджет писателя","спойлеры выключить","спойлеры включить","новые сюжеты","сравнение писателей"):
        with LOCK, closing(connect()) as db, db:
            if evolution_style:
                soul_evolution.style(db,evolution_style[1])
                return "Стиль романа: "+evolution_style[1]+"."
            if evolution_preference:
                themes=dict(zip(("любви","хранительниц","магии","миров","интриг","загадок","развития","героев"),soul_evolution.THEMES))
                soul_evolution.preference(db,themes[evolution_preference[1]])
                return "Предпочтение сохранено для новых сюжетов после обязательных саг."
            if q=="сравнение писателей":return soul_evolution.model_report(db)
            if evolution_archive:return soul_evolution.archive(db,(int(evolution_archive[1])-1)*20)
            if evolution_profile:return soul_evolution.profile(db,evolution_profile[1])
            if evolution_volume:return soul_evolution.annotation(db,int(evolution_volume[1]))
            if evolution_format:
                fmt=evolution_format[1]
                if not soul_romance.start_cycle(db,fmt,"future",soul_evolution.FORMATS[fmt]):return "Сначала завершите открытый цикл или обработайте черновик."
                return "Открыт литературный цикл: "+fmt+". Цель "+str(soul_evolution.FORMATS[fmt])+" слов, последовательными частями. Суточный лимит не изменён."
            if evolution_budget:
                model=cloud_writer.selected(db) or CONFIG["model"]
                if not model:return "Сначала выберите модель писателя."
                cap,inp,out=map(int,evolution_budget.groups())
                soul_evolution.set_budget(db,model,inp*100,out*100,cap*100)
                CHRONICLE["epoch"]+=1
                return soul_evolution.budget_text(db,datetime.now(timezone.utc).strftime("%Y-%m"))
            if q=="бюджет писателя":return soul_evolution.budget_text(db,datetime.now(timezone.utc).strftime("%Y-%m"))
            if q in ("спойлеры выключить","спойлеры включить"):
                db.execute("UPDATE evolution_settings SET spoilers=? WHERE id=1",(int(q=="спойлеры выключить"),))
                return "Защита новых карточек от спойлеров "+("включена." if q=="спойлеры выключить" else "отключена.")
            return "Новые сюжетные замыслы (спойлеры):\n"+"\n".join(f"{n}. {title}" for n,_,title,_ in soul_evolution.SCENES)
    living_commands={"развивай историю сама":"draft","включи автопубликацию глав":"auto","останови развитие":"off","что нового написала":"news","статус развития":"status","план развития романа":"queue"}
    if q in living_commands:
        with LOCK, closing(connect()) as db, db:
            action=living_commands[q]
            if action in ("off","draft","auto"):
                if action!="off" and not soul_chronicle.canon_ok(db):return "Канон повреждён. Развитие не включено."
                soul_living.set_mode(db,action)
                CHRONICLE.update(enabled=False,epoch=CHRONICLE["epoch"]+1)
                if action=="off":return "Развитие остановлено. Уже начатый запрос может быть платным, его результат не сохранится."
                return soul_living.status(db)+(" Публикация только после вашего утверждения." if action=="draft" else " Автопубликация только новых фоновых глав, прошедших локальные эвристики; сомнительные остаются черновиками. Это не смысловая гарантия.")
            if action=="status":return soul_living.status(db)
            if not soul_chronicle.canon_ok(db):return "Канон повреждён."
            if action=="news":return soul_living.news(db)
            if soul_living.audit(db) or soul_shadow.audit(db) or soul_guardians.audit(db) or soul_destiny.audit(db) or soul_evolution.audit(db) or soul_immortal.audit(db) or soul_novel.audit(db):return "Сюжетные данные повреждены."
            qplan=soul_novel.forecast(db)
            return "План (пересматриваемый прогноз, со спойлерами):\n"+"\n".join(f"{p['number']}. {p['title']}" for p in qplan["items"])
    if q=="статус романа":
        with LOCK, closing(connect()) as db:
            return soul_novel.status(db) if not soul_novel.audit(db) else "Части романа повреждены."
    if q=="проверить черновик редактором":return independent_editor()
    if q=="отчёт редактора":
        with LOCK, closing(connect()) as db:
            p=soul_chronicle.latest_pending(db)
            if not p:return "Нет черновика."
            try:return soul_immortal.editor_text(db,p["id"])
            except ValueError:return "Отчёт повреждён или устарел."
    immortal_length=re.fullmatch(r"длина сцены (короткая|обычная|большая)",q)
    immortal_idle=re.fullmatch(r"интервал писателя (20|30|60|120)",q)
    immortal_volume=re.fullmatch(r"качество тома ([1-9][0-9]{0,5})",q)
    if immortal_length or immortal_idle or immortal_volume or q in ("бессмертная летопись","качество прозы","новые саги"):
        with LOCK, closing(connect()) as db, db:
            if immortal_length:
                db.execute("UPDATE immortal_preferences SET length=? WHERE id=1",(immortal_length[1],))
                return "Длина сцены: "+immortal_length[1]+". Лимит токенов сохранён."
            if immortal_idle:
                db.execute("UPDATE immortal_preferences SET idle=? WHERE id=1",(int(immortal_idle[1])*60,))
                return "Интервал бездействия: "+immortal_idle[1]+" минут. Одна попытка в сутки."
            if soul_immortal.audit(db):return "Литературные записи повреждены."
            if immortal_volume:return soul_immortal.quality_text(db,int(immortal_volume[1]))
            if q=="качество прозы":return soul_immortal.quality_text(db)
            if q=="новые саги":return "Новые саги (замыслы, спойлеры):\n"+"\n".join(x[1] for x in soul_immortal.SAGAS)
            return soul_immortal.status(db)
    reader_commands={"читать книгу":"resume","начать чтение":"resume","читать с начала":"start","начать с начала":"start","следующая страница":"next","предыдущая страница":"back","где остановился":"where","где я остановился":"where","остановить чтение":"pause","пауза чтения":"pause","летопись: продолжить чтение":"resume"}
    if q in reader_commands or q in ("дальше","назад","листай дальше"):
        with LOCK, closing(connect()) as db, db:
            if q in reader_commands:return soul_reader.move(db,reader_commands[q])
            if soul_reader.active(db):return soul_reader.move(db,"back" if q=="назад" else "next")
        # Short ambiguous commands remain ordinary chat outside reader mode.
        return None
    destiny_topics={"сила":"power","путешествия":"travel","пророчества":"prophecy","союзы":"alliance","развитие":"growth","последствия":"consequence","царства":"realm"}
    destiny_read=re.fullmatch(r"летопись: судьба (сила|путешествия|пророчества|союзы|развитие|последствия|царства)",q)
    destiny_commands=("летопись: судьба","летопись: план судьбы","летопись: новые герои")
    guardian_profile=re.fullmatch(r"(?:летопись: хранительница|расскажи о хранительнице) (.{2,60})",q)
    guardian_commands=("летопись: хранительницы","летопись: план хранительниц","летопись: статус хранительниц")
    simple_commands=("летопись: помощь","летопись: сага","летопись: сага план","летопись: принять текущую","летопись: отклонить текущую")
    read_match=re.fullmatch(r"(?:летопись: читать|прочитай главу|читать главу) ([1-9][0-9]{0,8})",q)
    create_match=re.fullmatch(r"летопись: создать(?: (прошлое|встреча|любовь|будущее|варианты|сагу|хранительниц|судьбу))?",q)
    genesis_read=re.fullmatch(r"летопись: (письмо|другой взгляд|вариант) ([1-9][0-9]{0,8})",q)
    genesis_arc=re.fullmatch(r"летопись: эпоха (прошлое|встреча|любовь|будущее)(?: ([1-9][0-9]{0,5}))?",q)
    genesis_commands=("летопись: атлас","летопись: законы","летопись: энциклопедия","летопись: судьбы","летопись: аудит","летопись: варианты","летопись: план 100","летопись: любовь","летопись: прошлое","летопись: персонажи")
    omega_read=re.fullmatch(r"летопись: (том|читать том|дневник героини) ([1-9][0-9]{0,8})",q)
    omega_search=re.fullmatch(r"летопись: (поиск|персонаж) (.{2,200})",q)
    omega_commands=("летопись: книги","летопись: продолжить чтение","летопись: план","летопись: загадки","летопись: качество","летопись: дневник героини","летопись: хронология")
    romance_start=re.fullmatch(r"летопись: цикл (обычная|большая|романтическая)(?: (прошлое|встреча|любовь|будущее))?",q)
    romance_read=re.fullmatch(r"летопись: читать цикл ([1-9][0-9]{0,8})",q)
    romance_commands=("летопись: циклы","летопись: завершить цикл","летопись: оригинальность","летопись: замысел")
    heart_topics={"знакомство":"meeting","нежность":"tenderness","доверие":"trust","воспоминания":"memory","письма":"letters","приключения":"adventure"}
    heart_read=re.fullmatch(r"летопись: сердце(?: (знакомство|нежность|доверие|воспоминания|письма|приключения))?",q)
    heart_commands=("летопись: линии любви","летопись: замысел любви")
    decision=re.fullmatch(r"летопись: (принять|отклонить) ([1-9][0-9]{0,8})",q)
    if not destiny_read and q not in destiny_commands and not guardian_profile and q not in guardian_commands and q not in simple_commands and q not in soul_chronicle.COMMANDS and not decision and not read_match and not create_match and not omega_read and not omega_search and not genesis_read and not genesis_arc and not romance_start and not romance_read and not heart_read and q not in heart_commands and q not in romance_commands and q not in genesis_commands and q not in omega_commands and q not in ("летопись: главы","летопись: содержание","летопись: последняя"):
        return None
    if create_match:
        with LOCK, closing(connect()) as db, db:
            soul_chronicle.control(db,"manual_request")
        return generate_chronicle(arc=soul_saga.ALIASES.get(create_match[1]),alternative=create_match[1]=="варианты",shadow=create_match[1]=="сагу",guardians=create_match[1]=="хранительниц",destiny=create_match[1]=="судьбу")
    with LOCK, closing(connect()) as db, db:
        if q=="летопись: аудит":
            issues=soul_genesis.audit(db)+soul_heart.audit(db)+soul_shadow.audit(db)+soul_guardians.audit(db)+soul_destiny.audit(db)+soul_living.audit(db)+soul_evolution.audit(db)+soul_immortal.audit(db)
            return "Проверка целостности (не семантическая проверка): "+("\n"+"\n".join(issues) if issues else "нарушений не найдено.")
        if (destiny_read or q in destiny_commands or guardian_profile or q in guardian_commands or q in simple_commands or heart_read or q in heart_commands or romance_start or romance_read or q in romance_commands or genesis_read or genesis_arc or q in genesis_commands or omega_read or omega_search or q in omega_commands or read_match or q in ("летопись: содержание","летопись: последняя","летопись: главы")) and not soul_chronicle.canon_ok(db):
            return "Целостность исходной летописи нарушена; чтение заблокировано."
        if destiny_read:return soul_destiny.timeline(db,destiny_topics[destiny_read[1]])
        if q=="летопись: новые герои":return soul_destiny.characters(db)
        if q in ("летопись: судьба","летопись: план судьбы"):return soul_destiny.status(db,q=="летопись: план судьбы")
        if guardian_profile:return soul_guardians.profiles(db,guardian_profile[1])
        if q=="летопись: хранительницы":return soul_guardians.profiles(db)
        if q in ("летопись: план хранительниц","летопись: статус хранительниц"):return soul_guardians.status(db,q=="летопись: план хранительниц")
        if q=="летопись: помощь":
            return "Летопись\n\nЧитать книгу · Дальше · Назад · Продолжить чтение\nГде остановился · Остановить чтение · Оглавление\nПродолжи сагу · Продолжи нашу историю любви\nПокажи черновик · Принять главу · Отклонить главу\nЧто дальше по сюжету · История любви · Девять хранительниц · Новые герои\nРазвивай историю сама · Останови развитие · Что нового написала · Статус развития\nМодель писателя · Подключи писателя · Расход писателя\nСтиль романа романтика · Формат главы большая · Судьба персонажа Хакурэя\n\nПодробности при необходимости: «план саги» (со спойлерами), «летопись: качество»."
        if q in ("летопись: сага","летопись: сага план"):
            if q.endswith(" план"):return soul_shadow.status(db,True)+"\n\n"+soul_guardians.status(db,True)+"\n\n"+soul_destiny.status(db,True)
            if soul_destiny.ready(db):return soul_destiny.status(db)
            return soul_guardians.status(db)+"\n\n"+soul_shadow.status(db) if soul_guardians.plan(db) else soul_shadow.status(db)+"\n\n"+soul_guardians.status(db)
        if q in ("летопись: принять текущую","летопись: отклонить текущую"):
            pending=db.execute("SELECT id FROM chronicle_drafts WHERE status='pending'").fetchone()
            if not pending:return "Нет ожидающей главы."
            approve=q=="летопись: принять текущую"
            try: ok=soul_chronicle.decide(db,pending[0],approve)
            except ValueError:ok=False
            if not ok:return "Не удалось сохранить решение: проверьте черновик."
            if not approve:return "Черновик отклонён."
            n=db.execute("SELECT number FROM saga_arcs WHERE draft_id=?",(pending[0],)).fetchone()[0]
            return f"Глава {n} сохранена. Граф обновлён. Читать: прочитай главу {n}."
        if heart_read: return soul_heart.timeline(db,heart_topics.get(heart_read[1]))
        if q=="летопись: линии любви": return soul_heart.thread_text(db)
        if q=="летопись: замысел любви":
            plan=soul_heart.choose(db,"love")
            return "Предварительный художественный замысел: "+plan["lens"]
        if romance_start:
            arc=soul_saga.ALIASES.get(romance_start[2],"love")
            ok=soul_romance.start_cycle(db,romance_start[1],arc)
            return "Цикл открыт. Цель: "+str(soul_romance.FORMATS[romance_start[1]])+" слов в утверждённых частях. Создавайте части командой «летопись: создать». Действует прежний дневной лимит." if ok else "Сначала обработайте текущий черновик, запрос или открытый цикл."
        if romance_read: return soul_romance.read_cycle(db,int(romance_read[1]))
        if q=="летопись: циклы": return soul_romance.cycles_text(db)
        if q=="летопись: завершить цикл": return "Цикл закрыт досрочно; опубликованные части сохранены." if soul_romance.close_cycle(db) else "Нет доступного для закрытия цикла или ещё есть черновик/запрос."
        if q=="летопись: оригинальность": return soul_romance.report_text(db)
        if q=="летопись: замысел":
            cycle=soul_romance.current_cycle(db)
            arc=cycle["arc"] if cycle else soul_saga.plan(db)["arc"]
            p=soul_romance.choose(db,arc)
            return "Предварительный художественный замысел, не канон:\n"+"\n".join(f"{k}: {v}" for k,v in p.items())
        if genesis_read:
            kind,n=genesis_read[1],int(genesis_read[2])
            if kind=="вариант":
                try: ok=n in (1,2) and soul_genesis.select_variant(db,n)
                except (ValueError,TypeError): ok=False
                return "Вариант выбран. Прочитайте черновик перед утверждением." if ok else "Вариант не доступен."
            return soul_genesis.extras(db,n,"letter" if kind=="письмо" else "perspective")
        if genesis_arc: return soul_genesis.read_arc(db,soul_saga.ALIASES[genesis_arc[1]],int(genesis_arc[2] or 1))
        if q in ("летопись: любовь","летопись: прошлое"):
            return soul_genesis.read_arc(db,"love" if q.endswith("любовь") else "past")
        if q=="летопись: атлас": return soul_genesis.atlas(db)
        if q=="летопись: законы": return "Правила художественного канона:\n"+"\n".join(f"Глава {n}: {rule}" for _,n,rule in soul_genesis.RULES)
        if q=="летопись: варианты": return soul_genesis.variants(db)
        if q=="летопись: план 100":
            return "Предварительный план, не канон:\n"+"\n".join(f"{p['number']}. Том {p['book']} · {soul_saga.ARC_LABELS[p['arc']]} — {p['beat']}" for p in soul_genesis.roadmap(db))
        if q in ("летопись: энциклопедия","летопись: судьбы","летопись: персонажи"):
            state=soul_genesis.state(db)
            if q=="летопись: судьбы":
                return "Причины и последствия:\n"+"\n".join(f"Глава {p['from']} → {p['to']}: {p['event']}" for p in state["consequences"][-50:]) if state["consequences"] else "Новые связи причин и последствий ещё не записаны."
            actors="\n".join(f"{a['name']}: главы {a['first']}–{a['last']}, событий {a['count']}"+(" — "+a["portrait"]+"; мотив: "+a["motive"]+"; родство: "+a["lineage"]+" (гл. "+str(a["source"])+")" if "portrait" in a else "") for a in state["actors"][-50:])
            if q=="летопись: персонажи": return "Персонажи новых глав:\n"+(actors or "Ещё нет новых карточек.")
            return soul_genesis.atlas(db)+"\n\nПерсонажи:\n"+actors+"\n\nОткрытые загадки:\n"+"\n".join(p["question"] for p in state["open"][:30])
        if read_match: return soul_reader.move(db,"chapter",int(read_match[1]))
        if omega_read:
            n=int(omega_read[2])
            if omega_read[1]=="читать том": return soul_omega.read_volume(db,n)
            return soul_omega.book(db,n) if omega_read[1]=="том" else soul_omega.diary(db,n)
        if omega_search:
            term=omega_search[2]
            if omega_search[1]=="персонаж": return soul_omega.character(db,term)
            rows=soul_genesis.recall(db,term,12)
            return "Найденные главы (локальный тематический индекс):\n"+"\n".join(f"{p['number']}. {p['title']}" for p in rows) if rows else "Ничего не найдено."
        if q=="летопись: книги": return soul_omega.books(db)
        if q=="летопись: дневник героини": return soul_omega.diary(db)
        if q=="летопись: качество": return soul_omega.quality(db)
        if q=="летопись: план":
            return "Предварительный план (не канон):\n"+"\n".join(f"{i}. {soul_saga.ARC_LABELS[p['arc']]} — {p['beat']}" for i,p in enumerate(soul_omega.roadmap(db),1))
        if q=="летопись: загадки":
            return "Загадки художественного мира:\n"+"\n".join(f"{v['question']} — глава {v['opened']}; "+(f"раскрыта в главе {v['closed']}" if v['closed'] else "открыта") for v in soul_omega.mysteries(db).values())
        if q=="летопись: хронология":
            return "Художественные эпохи (главы в порядке публикации внутри эпохи):\n"+"\n\n".join(soul_omega.ERA[a]+":\n"+"\n".join(f"{n}. {t}" for n,t in db.execute("SELECT number,title FROM omega_index WHERE arc=? ORDER BY number",(a,))) for a in soul_omega.ARCS)
        if q=="летопись: содержание": return soul_saga.contents(db)
        if q=="летопись: последняя": return soul_reader.move(db,"latest")
        if q=="летопись: включить сон":
            if not CONFIG["key"]:
                return "Сначала подключите Cloud.ru. Сон не включён."
            CHRONICLE.update(enabled=True,epoch=CHRONICLE["epoch"]+1)
            soul_chronicle.control(db,"background_enabled")
            return "Сон включён до закрытия сервера: не чаще одной попытки UTC в сутки, после 20 минут тишины, даже без новой записи дневника, по этапам саги о хранительницах и Тени либо открытого цикла; после завершения — по очереди веток. В Cloud.ru передаются канон, утверждённые художественные главы и счётчики (если есть), не текст чата. Отключение: летопись: выключить сон."
        if q=="летопись: выключить сон":
            CHRONICLE.update(enabled=False,epoch=CHRONICLE["epoch"]+1)
            soul_living.set_mode(db,"off")
            soul_chronicle.control(db,"background_disabled")
            return "Сон отключён. Уже начатый сетевой запрос может завершиться, но его черновик будет отброшен."
        if decision:
            i=int(decision[2])
            try:
                ok=soul_chronicle.decide(db,i,decision[1]=="принять")
            except ValueError:
                ok=False
            if ok and decision[1]=="принять":
                n=db.execute("SELECT number FROM saga_arcs WHERE draft_id=?",(i,)).fetchone()[0]
                return f"Решение сохранено. Глава {n} добавлена в летопись и граф. Читать: летопись: читать {n}."
            return "Решение сохранено." if ok else "Черновик не найден, повреждён или уже обработан."
        if q=="летопись: дневник":
            return soul_chronicle.diary_text(db)
        if q=="летопись: черновик":
            try:
                p=soul_chronicle.latest_pending(db)
            except ValueError:
                return "Черновик повреждён; публикация заблокирована."
            if not p:
                return "Нет ожидающего черновика."
            return f"Художественный черновик: {p['title']}\n\n{p['story']}\n\nПринять главу / Отклонить главу. Оценки: летопись: качество."
        if q=="летопись: главы":
            rows=soul_saga.reading_rows(db)[-5:]
            return "\n\n".join(f"Вымышленная глава №{p['number']}: {p['title']}\n{p['story']}" for p in rows) or "Новых утверждённых глав пока нет."
        st=soul_chronicle.status(db)
        return f"Канон: {st['canon_chapters']} глав, целостность: {st['canon_ok']}. Дневник: {st['diary_entries']}. Новые главы: {st['approved']}. Черновики: {st['pending']}. Сон: {'включён' if CHRONICLE['enabled'] else 'выключен'}. Параметры персонажа: {st['traits']}."

def chronicle_worker(stop):
    while not stop.wait(60):
        try:
            with LOCK, closing(connect()) as db, db:
                soul_chronicle.collect(db)
                if soul_chronicle.canon_ok(db):
                    soul_genesis.consolidate(db)
                    if not (soul_genesis.audit(db)+soul_heart.audit(db)+soul_shadow.audit(db)+soul_guardians.audit(db)+soul_destiny.audit(db)+soul_living.audit(db)+soul_evolution.audit(db)+soul_immortal.audit(db)+soul_novel.audit(db)):soul_novel.forecast(db)
                enabled=CHRONICLE["enabled"] or soul_living.mode(db)!="off"
            with LOCK, closing(connect()) as db:
                backed_up=db.execute("SELECT 1 FROM living_backups WHERE day=date('now')").fetchone()
            if not backed_up:
                with LOCK:
                    filename=soul_living.backup(DB,DB.parent/"backups")
                    with closing(connect()) as db, db:
                        db.execute("INSERT OR IGNORE INTO living_backups VALUES(date('now'),?)",(filename,))
            if enabled:
                generate_chronicle(background=True)
        except (sqlite3.Error,ValueError,OSError):
            # Keep foreground server available; no secret or prompt logging.
            continue

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "dist"), **kwargs)

    def log_message(self, fmt, *args):
        # No request body or secret is logged.
        super().log_message(fmt, *args)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()

    def respond(self, data, status=200):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def local(self):
        port = self.server.server_address[1]
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        return host in (f"127.0.0.1:{port}", f"localhost:{port}") and (origin is None or origin == f"http://{host}") and self.headers.get("Sec-Fetch-Site") not in ("cross-site", "same-site")

    def do_GET(self):
        if not self.local():
            return self.respond({"error":"Доступ только локально"},403)
        if self.path == "/api/activity":
            return self.respond(graph_activity.snapshot())
        if self.path == "/api/chronicle":
            with closing(connect()) as db:
                return self.respond({"status":soul_chronicle.status(db),"graph":soul_chronicle.biography_graph(db)})
        volume_match=re.fullmatch(r"/api/graph/volume/([1-9][0-9]{0,5})",self.path)
        if volume_match:
            try:
                with closing(connect()) as db:
                    return self.respond(soul_immortal.volume_graph(db,int(volume_match[1])))
            except (ValueError,TypeError,KeyError):return self.respond({"error":"Том недоступен или повреждён"},400)
        if self.path == "/api/graph":
            with closing(connect()) as db, db:
                data=memory_graph.snapshot(db)
            return self.respond(data)
        if self.path.split("?",1)[0] == "/api/avatar":
            path = ROOT / "data" / "avatar.png"
            if not path.is_file():
                return self.respond({"error":"Аватар не выбран"},404)
            raw = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type","image/png")
            self.send_header("Content-Length",str(len(raw)))
            self.send_header("Cache-Control","no-store")
            self.end_headers()
            self.wfile.write(raw)
            return
        if self.path == "/api/reader":
            with LOCK, closing(connect()) as db:
                return self.respond({"reader":soul_reader.view(db)})
        if self.path == "/api/history":
            with LOCK:
                return self.respond({"messages":history(), "connected":bool(CONFIG["key"])})
        if self.path.startswith("/api/"):
            return self.respond({"error":"Не найдено"},404)
        super().do_GET()

    def do_POST(self):
        if not self.local():
            return self.respond({"error":"Доступ только локально"},403)
        try:
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Требуется JSON")
            length = int(self.headers.get("Content-Length","0"))
            if not 0 < length <= (12_000_000 if self.path == "/api/avatar" else 100000):
                raise ValueError("Недопустимый размер запроса")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Некорректный JSON")
            if self.path == "/api/reader":
                action=data.get("action")
                if not isinstance(action,str) or action not in ("resume","next","back","pause","start","advance","retreat","position","presence"):raise ValueError("Недопустимое действие чтения")
                with LOCK, closing(connect()) as db, db:
                    CHRONICLE["last_activity"]=time.monotonic()
                    if action=="pause":
                        CHRONICLE["reader_seen"]=-1e9
                    elif action!="presence" or soul_reader.active(db):
                        CHRONICLE["reader_seen"]=time.monotonic()
                    if action=="position":
                        soul_reader.position(db,data.get("hash"),data.get("start"),data.get("end"))
                        return self.respond({"ok":True})
                    if action=="presence":return self.respond({"reader":soul_reader.view(db)})
                    reply=soul_reader.adjacent(db,action) if action in ("advance","retreat") else soul_reader.move(db,action)
                    return self.respond({"reply":reply,"reader":soul_reader.view(db)})
            if self.path == "/api/avatar":
                raw = base64.b64decode(data.get("png",""),validate=True)
                if not 33 <= len(raw) <= 8_000_000 or raw[:8] != b"\x89PNG\r\n\x1a\n" or raw[12:16] != b"IHDR":
                    raise ValueError("PNG required")
                width,height = int.from_bytes(raw[16:20],"big"),int.from_bytes(raw[20:24],"big")
                if not 0 < width <= 4096 or not 0 < height <= 4096:
                    raise ValueError("Invalid dimensions")
                with LOCK:
                    target = ROOT / "data" / "avatar.png"
                    target.parent.mkdir(parents=True,exist_ok=True)
                    tmp = target.with_suffix(".tmp")
                    tmp.write_bytes(raw)
                    tmp.replace(target)
                return self.respond({"ok":True})
            if self.path == "/api/note":
                with closing(connect()) as db, db:
                    memory_graph.add_note(db,data.get("kind"),data.get("content"))
                return self.respond({"ok":True})
            if self.path in ("/api/config", "/api/config/models"):
                key=normalize_cloud_key(data.get("key", ""))
                if key is None:
                    return self.respond({"error":"Проверьте формат API-ключа Cloud.ru."},400)
                if self.path == "/api/config/models":
                    try:
                        models=cloud_writer.list_models(key,urlopen,chat_only=True)
                    except HTTPError as error:
                        error.close()
                        if error.code in (401,403):
                            return self.respond({"error":"Cloud.ru отклонил запрос. Проверьте API-ключ и доступ к Foundation Models."},error.code)
                        if error.code == 429:
                            return self.respond({"error":"Cloud.ru ограничил число запросов. Повторите позже."},429)
                    except (OSError,HTTPException,ValueError,KeyError,TypeError):
                        pass
                    else:
                        return self.respond({"models":models})
                    return self.respond({"error":"Не удалось загрузить модели Cloud.ru. Повторите попытку или введите модель вручную."},502)
                model=data.get("model")
                if not key:
                    return self.respond({"error":"Введите API-ключ Cloud.ru."},400)
                if not isinstance(model,str) or not 0<len(model.strip())<=200:
                    return self.respond({"error":"Выберите модель из списка или введите её идентификатор."},400)
                if data.get("consent") is not True:
                    return self.respond({"error":"Подтвердите согласие на отправку сообщений и платные запросы."},400)
                model=model.strip()
                with LOCK:
                    with closing(connect()) as db, db:
                        soul_core.record_model(db,model)
                    CONFIG.update(key=key, model=model)
                    CHRONICLE.update(enabled=False,epoch=CHRONICLE["epoch"]+1)
                return self.respond({"connected":True})
            if self.path != "/api/chat":
                return self.respond({"error":"Не найдено"},404)
            content = data.get("content")
            if not isinstance(content,str) or not content.strip() or len(content)>12000:
                raise ValueError("Введите сообщение до 12000 символов")
            with LOCK:
                CHRONICLE["last_activity"]=time.monotonic()
            command=chronicle_command(content)
            if command is not None:
                with LOCK, closing(connect()) as db:
                    reader=soul_reader.view(db) if command.startswith("Глава ") and " · Страница " in command.split("\n",1)[0] else None
                return self.respond({"reply":command,"connected":bool(CONFIG["key"]),"reader":reader})
            with LOCK:
                user_id=store("user",content.strip())
                if not CONFIG["key"]:
                    reply = "Сообщение сохранено локально. Для ответа подключите Cloud.ru через меню аватара."
                    return self.respond({"reply":reply,"connected":False})
                with closing(connect()) as db:
                    persona = soul_core.system_prompt(db, CONFIG["model"], content.strip())
                payload = {"model":CONFIG["model"],"messages":[{"role":"system","content":persona}]+history(24),"max_tokens":1200,"stream":False}
                req = Request(API, data=json.dumps(payload).encode(), headers={"Authorization":"Bearer "+CONFIG["key"],"Content-Type":"application/json"}, method="POST")
                with graph_activity.track("chat",f"m:{user_id}") as activity:
                    try:
                        graph_activity.update(activity,"waiting")
                        with urlopen(req,timeout=60) as res:
                            body = json.loads(res.read(4_000_000))
                        graph_activity.update(activity,"received")
                        reply = body["choices"][0]["message"]["content"]
                        if not isinstance(reply,str) or not reply.strip():
                            raise ValueError("empty response")
                    except (URLError, TimeoutError, ValueError, KeyError, IndexError, TypeError, OSError):
                        graph_activity.update(activity,"error")
                        return self.respond({"error":"Cloud.ru не вернул ответ. Сообщение сохранено; проверьте модель и ключ."},502)
                    answer_id=store("assistant",reply)
                    graph_activity.update(activity,"done",f"m:{answer_id}")
                    CHRONICLE["last_activity"]=time.monotonic()
                    return self.respond({"reply":reply,"connected":True})
        except (ValueError, UnicodeError, TypeError, binascii.Error) as e:
            return self.respond({"error":"Некорректные данные запроса"},400)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if not (ROOT / "dist" / "index.html").is_file():
        raise SystemExit("Frontend not built: npm install && npm run build")
    with closing(connect()) as db, db:
        soul_chronicle.recover(db)
        soul_chronicle.collect(db)
    stop=threading.Event()
    worker=threading.Thread(target=chronicle_worker,args=(stop,),daemon=True)
    worker.start()
    with ThreadingHTTPServer(("127.0.0.1",args.port),Handler) as server:
        url = f"http://127.0.0.1:{server.server_address[1]}"
        print("Hakureya: "+url,flush=True)
        if not args.no_browser:
            threading.Timer(.3,lambda:webbrowser.open(url)).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()

if __name__ == "__main__":
    main()
