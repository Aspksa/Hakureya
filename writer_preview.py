"""Volatile opt-in preview of received fictional prose, never raw JSON or reasoning."""
import json
from threading import Lock
from time import monotonic

LOCK=Lock()
ACTIVE={}
LAST=None
LIMIT=24000

def story_prefix(raw):
    """Read only a top-level 'story' string, tolerating an unfinished JSON response."""
    decoder=json.JSONDecoder()
    text=raw.lstrip().lstrip("\ufeff")
    if text.startswith("```"):
        newline=text.find("\n")
        if newline<0 or text[:newline].strip().casefold() not in ("```","```json"):return ""
        text=text[newline+1:].lstrip()
    if not text.startswith("{"):return ""
    pos=1
    while pos<len(text):
        while pos<len(text) and text[pos].isspace():pos+=1
        try:key,end=decoder.raw_decode(text,pos)
        except ValueError:return ""
        if not isinstance(key,str):return ""
        pos=end
        while pos<len(text) and text[pos].isspace():pos+=1
        if pos>=len(text) or text[pos]!=":":return ""
        pos+=1
        while pos<len(text) and text[pos].isspace():pos+=1
        if key=="story":
            if pos>=len(text) or text[pos]!='"':return ""
            try:
                value,_=decoder.raw_decode(text,pos)
                if isinstance(value,str):return value.encode("utf-8","replace").decode("utf-8")
                return ""
            except ValueError:pass
            # Find the longest complete sequence of JSON string tokens.
            i=pos+1;last=i
            while i<len(text):
                if text[i]=='"':break
                if text[i]=='\\':
                    if i+1>=len(text):break
                    width=6 if text[i+1]=="u" else 2
                    if i+width>len(text):break
                    i+=width
                else:
                    if ord(text[i])<32:break
                    i+=1
                last=i
            try:
                value=json.loads(text[pos:last]+'"')
                return value.encode("utf-8","replace").decode("utf-8")
            except ValueError:return ""
        try:_,pos=decoder.raw_decode(text,pos)
        except ValueError:return ""
        while pos<len(text) and text[pos].isspace():pos+=1
        if pos>=len(text) or text[pos]!=",":return ""
        pos+=1
    return ""

def push(key,raw):
    if not isinstance(raw,str) or len(raw)>LIMIT:return
    prose=story_prefix(raw)
    with LOCK:
        ACTIVE[key]=(monotonic(),prose)

def fragment(key):
    with LOCK:
        return ACTIVE.get(key,(0,""))[1]

def clear(key):
    global LAST
    with LOCK:
        item=ACTIVE.pop(key,None)
        if item and item[1]:LAST=(monotonic(),item[1])

def snapshot():
    with LOCK:
        if not ACTIVE:return {"active":False,"story":LAST[1] if LAST and monotonic()-LAST[0]<120 else ""}
        _,(when,story)=max(ACTIVE.items(),key=lambda x:x[1][0])
        if monotonic()-when>120:return {"active":False,"story":""}
        return {"active":True,"story":story}
