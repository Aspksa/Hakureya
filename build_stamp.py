"""Portable frontend source fingerprint; standard library only."""
from pathlib import Path
import hashlib
import sys

ROOT=Path(__file__).resolve().parent
STAMP=ROOT/"dist"/".source-sha256"

def fingerprint():
    paths=[p for p in (ROOT/"web").rglob("*") if p.is_file()]
    paths += [p for p in ROOT.glob("vite.config.*") if p.is_file()]
    paths += [ROOT/"index.html",ROOT/"package.json"]
    lock=ROOT/"package-lock.json"
    if lock.is_file():
        paths.append(lock)
    public=ROOT/"public"
    if public.is_dir():
        paths += [p for p in public.rglob("*") if p.is_file()]
    h=hashlib.sha256()
    for p in sorted(paths,key=lambda p:p.relative_to(ROOT).as_posix()):
        h.update(p.relative_to(ROOT).as_posix().encode("utf-8"))
        h.update(b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()

def main():
    try:
        if not (ROOT/"dist"/"index.html").is_file():
            return 1
        digest=fingerprint()
        if sys.argv[1:]==["--write"]:
            STAMP.write_text(digest,encoding="ascii")
            return 0
        return 0 if STAMP.read_text(encoding="ascii")==digest else 1
    except OSError:
        return 1

if __name__=="__main__":
    raise SystemExit(main())
