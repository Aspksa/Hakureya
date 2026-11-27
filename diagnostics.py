"""Local support journal: metadata only, never raw request/response or exception text."""
import json
import logging
import platform
import re
import traceback
from pathlib import Path
from urllib.error import HTTPError, URLError
from uuid import uuid4

LOG = logging.getLogger("hakureya.diagnostics")
SESSION = uuid4().hex
SAFE_ID = re.compile(r"[a-zA-Z0-9:_#.-]{1,100}")
ROUTES = frozenset(("chat","history","graph","writer","config","activity","avatar","universe","notes","reader","chronicle","commands","health","diagnostics"))
FINISH = frozenset(("stop","length","content_filter","tool_calls","function_call"))

def identifier(value):
    return value if isinstance(value,str) and SAFE_ID.fullmatch(value) else "unknown"

def route(path):
    parts=path.split("?",1)[0].split("/")
    return "/api/"+parts[2] if len(parts)>2 and parts[1]=="api" and parts[2] in ROUTES else "other"

def finish(value):
    return value if isinstance(value,str) and value in FINISH else "unknown"

def emit(event, **fields):
    # Call sites supply only explicitly selected metadata; do not pass payloads.
    try:
        LOG.info("%s",json.dumps({"session":SESSION,"event":event,**fields},ensure_ascii=False),stacklevel=2)
    except Exception:
        # Diagnostics must not change the result of a paid request.
        pass

def failure(event,error,**fields):
    # Stack locations only: no source lines, local variables, exception messages or paths.
    try:
        frames=[{"file":Path(f.filename).name,"line":f.lineno,"function":f.name}
                for f in traceback.extract_tb(error.__traceback__)[-24:]]
        info={"error_type":type(error).__name__,"frames":frames}
        if isinstance(error,HTTPError):info["http_status"]=error.code
        if isinstance(error,URLError):info["reason_type"]=type(error.reason).__name__
        if isinstance(error,OSError) and type(error.errno) is int:info["errno"]=error.errno
        if isinstance(error,json.JSONDecodeError):
            info.update(json_line=error.lineno,json_column=error.colno,json_position=error.pos)
        # Match known internal messages exactly; unknown provider text is never included.
        import writer_response
        if isinstance(error,ValueError) and str(error) in writer_response.ERRORS:
            info["error_code"]=str(error)
        LOG.warning("%s",json.dumps({"session":SESSION,"event":event,**fields,**info},ensure_ascii=False),stacklevel=2)
    except Exception:
        pass

def environment():
    return {"python":platform.python_version(),"os":platform.system(),"sqlite":__import__("sqlite3").sqlite_version}
