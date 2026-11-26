"""Opt-in Windows user-bound DPAPI storage; never plaintext or cross-machine fallback."""
import ctypes
import json
import os
import sys
import tempfile
from pathlib import Path
from ctypes import wintypes

class Blob(ctypes.Structure):
    _fields_=[("cbData",wintypes.DWORD),("pbData",ctypes.POINTER(ctypes.c_ubyte))]

def supported():
    return sys.platform=="win32"

def transform(raw,protect):
    if not supported():raise OSError("DPAPI unavailable")
    if not 0<len(raw)<=65536:raise ValueError("invalid credential blob")
    buf=(ctypes.c_ubyte*len(raw)).from_buffer_copy(raw)
    src=Blob(len(raw),buf)
    dst=Blob()
    crypt=ctypes.WinDLL("crypt32",use_last_error=True)
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    fn=crypt.CryptProtectData if protect else crypt.CryptUnprotectData
    fn.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    fn.restype=wintypes.BOOL
    kernel.LocalFree.argtypes=[ctypes.c_void_p]
    kernel.LocalFree.restype=ctypes.c_void_p
    try:
        if not fn(ctypes.byref(src),None,None,None,None,1,ctypes.byref(dst)):
            raise OSError("DPAPI operation failed")
        if not 0<dst.cbData<=65536:raise ValueError("invalid credential blob")
        return ctypes.string_at(dst.pbData,dst.cbData)
    finally:
        ctypes.memset(buf,0,len(raw))
        if dst.pbData:
            if not protect:ctypes.memset(dst.pbData,0,dst.cbData)
            kernel.LocalFree(ctypes.cast(dst.pbData,ctypes.c_void_p))

def save(path,key,model):
    path=Path(path)
    raw=transform(json.dumps({"key":key,"model":model}).encode(),True)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=".cloud-",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as file:
            file.write(raw)
            file.flush()
            os.fsync(file.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

def load(path):
    path=Path(path)
    if not path.is_file():return None
    with path.open("rb") as file:raw=file.read(65537)
    result=json.loads(transform(raw,False))
    if not isinstance(result,dict) or not isinstance(result.get("key"),str) or not isinstance(result.get("model"),str):
        raise ValueError("invalid saved connection")
    return result

def forget(path):
    Path(path).unlink(missing_ok=True)
