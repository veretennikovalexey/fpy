"""
Диагностика 5175: где ALS реально берёт collation.
Запусти:  python .\_7_test2.py
"""
import os
import sys
import glob
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SRC_CONN_STR = (
    "Driver={Advantage StreamlineSQL ODBC};"
    f"DataDirectory={BASE_DIR};"
    "ServerTypes=1;"
    "TableType=ADT;"
    "UID=AdsSys;"
    "PWD=;"
)


def hr(title):
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def listing(path, pattern_list):
    """Печатает найденные файлы из pattern_list в path."""
    found = []
    if not os.path.isdir(path):
        return found
    for entry in os.listdir(path):
        if entry.lower() in [p.lower() for p in pattern_list]:
            full = os.path.join(path, entry)
            try:
                size = os.path.getsize(full)
                mt = os.path.getmtime(full)
                import datetime
                mt_s = datetime.datetime.fromtimestamp(mt).strftime("%Y-%m-%d")
                found.append((full, size, mt_s))
            except OSError:
                pass
    return found


# ---------------------------------------------------------------------------
hr("1. ПОИСК adslocal.cfg / adscollate.adt НА ДИСКЕ")

# Файлы, которые нам важны
PATTERNS = ["adslocal.cfg", "adscollate.adt", "adscollate.adm",
            "ANSI.CHR", "EXTEND.CHR"]

# Стандартные места, куда они могут попасть
candidates = [
    BASE_DIR,
    os.getcwd(),
    r"C:\Windows",
    r"C:\Windows\System32",
    r"C:\Windows\SysWOW64",
]

# Найдём путь к Advantage ODBC через реестр
try:
    import winreg
    odbc_keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\ODBC\ODBCINST.INI\Advantage StreamlineSQL ODBC"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\ODBC\ODBCINST.INI\Advantage StreamlineSQL ODBC"),
    ]
    for root, sub in odbc_keys:
        try:
            with winreg.OpenKey(root, sub) as k:
                driver_dll, _ = winreg.QueryValueEx(k, "Driver")
                print(f"  ODBC реестр: {sub}")
                print(f"    Driver = {driver_dll}")
                driver_dir = os.path.dirname(driver_dll)
                if driver_dir not in candidates:
                    candidates.append(driver_dir)
        except FileNotFoundError:
            pass
except Exception as e:
    print(f"  [warn] не удалось залезть в реестр: {e}")

# Найдём путь к Python install
candidates.append(os.path.dirname(sys.executable))

# Расширяемся ещё на типовые Advantage-папки
for ev in ("ProgramFiles", "ProgramFiles(x86)"):
    pf = os.environ.get(ev)
    if pf:
        for d in glob.glob(os.path.join(pf, "Advantage*")):
            candidates.append(d)

print()
print(f"  Проверяем {len(candidates)} директорий:")
all_found = []
for d in candidates:
    rows = listing(d, PATTERNS)
    if rows:
        print(f"\n  {d}")
        for full, size, mt in rows:
            print(f"    {os.path.basename(full):<18} {size:>10} bytes  ({mt})")
            all_found.append(full)

if not all_found:
    print("  Никаких файлов collation не найдено нигде — это странно.")

# ---------------------------------------------------------------------------
hr("2. ИТОГО: РАЗНЫЕ adslocal.cfg")
cfgs = [p for p in all_found if os.path.basename(p).lower() == "adslocal.cfg"]
if len(cfgs) <= 1:
    print(f"  adslocal.cfg найден в одном месте: {cfgs}")
else:
    print(f"  ВНИМАНИЕ: adslocal.cfg найден в {len(cfgs)} местах:")
    for c in cfgs:
        print(f"    {c}")
        try:
            with open(c, "r", encoding="ascii", errors="replace") as f:
                for line in f:
                    ls = line.strip()
                    if ls and not ls.startswith(";") and "=" in ls and any(
                        k in ls.upper() for k in ("ANSI_CHAR_SET", "OEM_CHAR_SET")
                    ):
                        print(f"      {ls}")
        except Exception as e:
            print(f"      (не удалось прочитать: {e})")

# ---------------------------------------------------------------------------
hr("3. ALS: КАКИЕ COLLATION РЕАЛЬНО ЗАГРУЖЕНЫ")

try:
    import pyodbc
except Exception as e:
    print(f"  pyodbc не загружается: {e}")
    sys.exit(1)

print(f"  cwd процесса перед connect(): {os.getcwd()}")
try:
    src = pyodbc.connect(SRC_CONN_STR, autocommit=True)
    print(f"  [OK] соединение открыто")
except Exception as e:
    print(f"  [FAIL] connect: {e}")
    sys.exit(2)

# sp_GetCollations — официальная процедура Advantage
print()
print("  sp_GetCollations() — список collation, который ALS знает прямо сейчас:")
try:
    cur = src.cursor()
    cur.execute("EXECUTE PROCEDURE sp_GetCollations()")
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    print(f"    колонки: {cols}")
    found_russian2 = False
    for r in rows:
        rec = dict(zip(cols, r))
        name = rec.get("CollationName") or rec.get("Name") or list(rec.values())[0]
        active = rec.get("Active") or rec.get("IsActive")
        marker = "  <-- АКТИВНАЯ" if active in (1, True, "T", "Y") else ""
        if name and "russian2" in str(name).lower():
            found_russian2 = True
            marker += "  *** RUSSIAN2 здесь!"
        print(f"      {rec}{marker}")
    print()
    if found_russian2:
        print("  [OK] Russian2 в списке есть. Если он не активен — поправь adslocal.cfg или")
        print("       проверь, что наш adslocal.cfg именно тот, который читает ALS.")
    else:
        print("  [FAIL] Russian2 в списке НЕТ.")
        print("         Значит ALS читает не наш adscollate.adt, а какой-то другой")
        print("         (скорее всего из C:\\Windows\\System32 или из папки ODBC-драйвера).")
        print("         Решение: положить наши 5 файлов туда тоже.")
    cur.close()
except Exception as e:
    print(f"  [warn] sp_GetCollations не сработал: {e}")
    print(f"         Это может быть нормально на старых версиях ALS, не критично.")

# ---------------------------------------------------------------------------
hr("4. ОТКРЫТЬ ТАБЛИЦУ R09 БЕЗ ИНДЕКСА (только для понимания)")
# Свободная R09.adt + R09.ADI — индекс мы и не используем в SELECT *
# но ADS всё равно валидирует ADI при открытии таблицы.
# Если временно убрать R09.ADI — SELECT пройдёт. Это диагностический трюк.
adi = os.path.join(BASE_DIR, "R09.ADI")
print(f"  Файл индекса: {adi} существует: {os.path.exists(adi)}")
print(f"  (Если хочешь убедиться, что проблема именно в индексе, можно ВРЕМЕННО")
print(f"   переименовать R09.ADI в R09.ADI.bak и повторить SELECT — он пройдёт.")
print(f"   Но это только для теста, не для боевой работы.)")

src.close()
print()
print("Готово.")
