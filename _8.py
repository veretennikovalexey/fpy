"""
_8.py — без всякого ADS.

Для каждого имени из _8.txt:
  1. Удалить name.* в C:\\fabius\\ohc\\REFLIS\\ (заблокированные файлы пропустить).
  2. Если все целевые файлы удалились — скопировать name.* из текущей папки туда.
  3. Если что-то не удалилось (файл захвачен) — пропустить этого пациента целиком.

Все операции пишутся в _8.log рядом со скриптом. Когда лог переваливает за
LOG_MAX_BYTES, в файле оставляется только вторая (свежая) половина строк.
"""
import os
import sys
import glob
import shutil
from datetime import datetime

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
LIST_FILE = os.path.join(BASE_DIR, "_8.txt")
LOG_FILE  = os.path.join(BASE_DIR, "_8.log")
DST_DIR   = r"C:\fabius\ohc\REFLIS"

LOG_MAX_BYTES = 300 * 1024  # 300 KB


def rotate_log_if_needed():
    """Если _8.log перевалил за лимит — оставить только вторую половину строк."""
    try:
        if os.path.getsize(LOG_FILE) <= LOG_MAX_BYTES:
            return
    except OSError:
        return

    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        keep = lines[len(lines) // 2:]
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"--- лог обрезан {datetime.now():%Y-%m-%d %H:%M:%S} "
                    f"(оставлено {len(keep)} из {len(lines)} строк) ---\n")
            f.writelines(keep)
    except OSError as e:
        # Если что-то с правами/диском — молча продолжаем, без лога не помрём
        print(f"[warn] не удалось ротировать лог: {e}", file=sys.stderr)


def log(msg):
    """Печать в stdout + дозапись в _8.log с timestamp."""
    print(msg)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{ts}  {msg}\n")
    except OSError as e:
        print(f"[warn] не удалось дописать в лог: {e}", file=sys.stderr)


def read_names(path):
    names = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for raw in f:
            n = raw.strip()
            if n and not n.startswith("#"):
                names.append(n)
    return names


def delete_target(name):
    """Удаляет DST_DIR\\name.* . Возвращает (deleted, locked)."""
    deleted, locked = [], []
    for path in glob.glob(os.path.join(DST_DIR, f"{name}.*")):
        try:
            os.remove(path)
            deleted.append(path)
        except PermissionError:
            locked.append(path)
        except OSError as e:
            locked.append(f"{path} ({e})")
    return deleted, locked


def copy_source(name):
    """Копирует BASE_DIR\\name.* в DST_DIR. Возвращает список скопированных."""
    copied = []
    for path in glob.glob(os.path.join(BASE_DIR, f"{name}.*")):
        dst = os.path.join(DST_DIR, os.path.basename(path))
        shutil.copy2(path, dst)
        copied.append(dst)
    return copied


def main():
    rotate_log_if_needed()
    log("=" * 60)
    log(f"СТАРТ _8.py (cwd={BASE_DIR}, dst={DST_DIR})")

    if not os.path.isdir(DST_DIR):
        log(f"FATAL: целевая папка не найдена: {DST_DIR}")
        sys.exit(1)
    if not os.path.exists(LIST_FILE):
        log(f"FATAL: нет файла со списком: {LIST_FILE}")
        sys.exit(1)

    names = read_names(LIST_FILE)
    log(f"К переносу: {len(names)} -> {names}")

    ok, skipped = [], []
    for i, name in enumerate(names, 1):
        log(f"[{i}/{len(names)}] {name}")

        deleted, locked = delete_target(name)
        for p in deleted:
            log(f"  del  {p}")
        for p in locked:
            log(f"  LOCK {p}")

        if locked:
            log(f"  -> пропуск (есть захваченные файлы)")
            skipped.append((name, locked))
        else:
            copied = copy_source(name)
            for p in copied:
                log(f"  cp   {p}")
            if not copied:
                log(f"  WARN: в {BASE_DIR} нет файлов {name}.*")
            ok.append(name)

    log(f"ИТОГО: ok={len(ok)}, пропущено={len(skipped)}")
    if skipped:
        for name, locked in skipped:
            log(f"  SKIP {name}: {locked}")
    log("ФИНИШ _8.py")


if __name__ == "__main__":
    main()
