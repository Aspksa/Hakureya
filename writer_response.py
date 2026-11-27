"""Conservative adaptation of a complete model response. No invented prose or facts."""
import json
import re

OPTIONAL=("literary","world","alternative","heart","shadow","guardians","destiny","living","evolution","immortal","infinite","intelligence","dynasty")
CORE=("title","story","tags","emotions","traits")
def unique(pairs):
    result={}
    for k,v in pairs:
        if k in result:raise ValueError("duplicate JSON field")
        result[k]=v
    return result

def parse(raw):
    if not isinstance(raw,str) or len(raw)>24000:raise ValueError("invalid draft")
    text=raw.strip().lstrip("\ufeff")
    fenced=re.fullmatch(r"\x60{3}(?:json)?[ \t]*\r?\n(.*?)\r?\n\x60{3}[ \t]*",text,re.S|re.I)
    if fenced:text=fenced[1].strip()
    value=json.loads(text,object_pairs_hook=unique)
    if not isinstance(value,dict):raise ValueError("invalid draft fields")
    return value

def normalize(value):
    import soul_chronicle as ch
    out={k:v for k,v in value.items() if k in CORE+OPTIONAL}
    warnings=[]
    if set(value)-set(out):warnings.append("Лишние поля ответа не приняты.")
    for key in ("title","story"):
        if isinstance(out.get(key),str):
            out[key]=out[key].replace("\r\n","\n").replace("\r","\n")
    # These are fictional counters, not literary facts. Invalid counters are not applied.
    tags=out.get("tags")
    if not isinstance(tags,list):tags=[]
    tags2=list(dict.fromkeys(t.strip().casefold() for t in tags if isinstance(t,str) and t.strip().casefold() in ch.TAGS))[:4]
    if not tags2:tags2=["познание"]
    if tags2!=out.get("tags"):warnings.append("Некорректные теги заменены допустимыми.")
    out["tags"]=tags2
    for name,keys,default,low,high in (("emotions",("wonder","calm","joy"),50,0,100),("traits",ch.TRAITS,0,-2,2)):
        current=out.get(name)
        valid=isinstance(current,dict) and set(current)==set(keys) and all(type(v) is int and low<=v<=high for v in current.values())
        if not valid:
            out[name]={k:default for k in keys}
            warnings.append("Некорректные "+("эмоции" if name=="emotions" else "изменения характера")+" заменены нейтральными значениями.")
    # Do not repair missing, too short, too long or duplicated prose by inventing/truncating it.
    ch.validate({k:out.get(k) for k in CORE})
    return out,warnings

ERRORS={
    "invalid draft fields":"Ответ не содержит обязательную структуру главы",
    "invalid text":"Заголовок или текст вне допустимых границ (3–100 / 100–5000 знаков), либо содержит управляющие символы",
    "invalid tags":"Некорректные теги",
    "invalid fictional emotions":"Некорректные показатели эмоций",
    "invalid trait change":"Некорректные изменения характера",
    "duplicate JSON field":"Повторяющийся ключ в JSON",
    "duplicate published chapter":"Повтор заголовка или текста опубликованной главы",
    "near duplicate chapter":"Слишком большое совпадение с опубликованным текстом",
    "novel boundary repeated":"Начало сцены повторяет конец предыдущей",
    "mixed story milestones":"Несовместимые сюжетные этапы",
    "incomplete writer stream":"Поток оборвался или не содержит завершённого художественного ответа",
    "writer stream error":"Cloud.ru вернул ошибку внутри потока",
    "writer response too large":"Ответ превышает безопасный предел",
    "writer stream too large":"Поток превышает безопасный предел",
    "invalid draft":"Ответ отсутствует или превышает безопасный предел",
    "canon changed":"Изменился исходный канон",
    "no reservation":"Потеряна резервация запроса",
}
def detail(error):
    # Never expose arbitrary provider error text, keys, reasoning or manuscript in diagnostics.
    return ERRORS.get(str(error),"Ошибка проверки структуры или сохранения ("+type(error).__name__+")")
