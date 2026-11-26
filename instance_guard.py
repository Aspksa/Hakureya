"""Hold a process-owned lock on a persistent sibling file; no stale PID deletion."""
from contextlib import contextmanager
from pathlib import Path
import os

@contextmanager
def exclusive(db):
    path=Path(db).with_suffix(".lock")
    path.parent.mkdir(parents=True,exist_ok=True)
    handle=path.open("a+b")
    locked=False
    try:
        handle.seek(0,os.SEEK_END)
        if handle.tell()==0:
            handle.write(b"0");handle.flush()
        handle.seek(0)
        try:
            if os.name=="nt":
                import msvcrt
                msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            locked=True
        except OSError as error:
            raise RuntimeError("Hakureya is already running or the database lock is unavailable.") from error
        yield
    finally:
        if locked:
            handle.seek(0)
            if os.name=="nt":
                import msvcrt
                msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
        handle.close()
