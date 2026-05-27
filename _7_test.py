"""
Диагностика _7.py — без DELETE/INSERT, только проверка.
Запусти из той же папки, где лежит _7.py:
    python .\_7_test.py
"""
import os
import sys
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TARGET_TABLE = "R09"  # таблица, на которой проверяем

SRC_CONN_STR = (
    "Driver={Advantage StreamlineSQL ODBC};"
    f"DataDirectory={BASE_DIR};"
    "ServerTypes=1;"
    "TableType=ADT;"
    "UID=AdsSys;"
    "PWD=;"
)

DST_CONN_STR = (
    "Driver={Advantage StreamlineSQL ODBC};"
    "DataDirectory=C:\\fabius\\ohc\\REFLIS\\DICT.ADD;"
    "ServerTypes=1;"
    "UID=AdsSys;"
    "PWD=;"
)


def hr(title):
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def step(num, msg):
    print(f"\n[Шаг {num}] {msg}")


def ok(msg):
    print(f"  [OK]   {msg}")


def fail(msg, exc=None):
    print(f"  [FAIL] {msg}", file=sys.stderr)
    if exc is not None:
        traceback.print_exc()


# ---------------------------------------------------------------------------
hr("ОКРУЖЕНИЕ")
print(f"  Python:    {sys.version.split()[0]}")
print(f"  Платформа: {sys.platform}")
print(f"  BASE_DIR:  {BASE_DIR}")
print(f"  cwd:       {os.getcwd()}")

# ---------------------------------------------------------------------------
hr("ФАЙЛЫ COLLATION В РАБОЧЕЙ ПАПКЕ")
# ALS читает adslocal.cfg + collation files из cwd или System32.
# Если хоть один из 5 файлов отсутствует — будет 5175 или похожая ошибка.
required = ["ANSI.CHR", "extend.chr", "adscollate.adt", "adscollate.adm", "adslocal.cfg"]
missing = []
for fname in required:
    full = os.path.join(BASE_DIR, fname)
    # Файловая система Windows регистронезависимая, но проверим оба варианта
    found = None
    for cand in (fname, fname.lower(), fname.upper()):
        p = os.path.join(BASE_DIR, cand)
        if os.path.exists(p):
            found = p
            break
    if found:
        size = os.path.getsize(found)
        print(f"  [OK]   {os.path.basename(found):<18} {size:>10} bytes")
    else:
        print(f"  [MISS] {fname}")
        missing.append(fname)

if missing:
    print()
    print(f"  ВНИМАНИЕ: не хватает файлов: {missing}")
    print(f"  ALS может упасть с ошибкой 5175 или 7077 / collation mismatch.")

# Показать ключевые строки adslocal.cfg
cfg_path = os.path.join(BASE_DIR, "adslocal.cfg")
if os.path.exists(cfg_path):
    print()
    print(f"  Из adslocal.cfg:")
    with open(cfg_path, "r", encoding="ascii", errors="replace") as f:
        for line in f:
            ls = line.strip()
            if ls and not ls.startswith(";") and "=" in ls and any(
                k in ls.upper() for k in ("ANSI_CHAR_SET", "OEM_CHAR_SET", "LOCALE")
            ):
                print(f"    {ls}")

# ---------------------------------------------------------------------------
hr("ИМПОРТ pyodbc")
try:
    import pyodbc
    ok(f"pyodbc версии {pyodbc.version}")
    drivers = [d for d in pyodbc.drivers() if "advantage" in d.lower()]
    if drivers:
        ok(f"Advantage ODBC драйверы в системе: {drivers}")
    else:
        print(f"  [WARN] Среди установленных ODBC драйверов нет ничего с 'Advantage'.")
        print(f"         Всё, что есть: {pyodbc.drivers()}")
except Exception as e:
    fail("pyodbc не импортируется", e)
    sys.exit(1)

# ---------------------------------------------------------------------------
hr("SOURCE: свободная таблица (без словаря)")

step(1, "pyodbc.connect(SRC, autocommit=True)")
src = None
try:
    src = pyodbc.connect(SRC_CONN_STR, autocommit=True)
    ok("соединение открыто")
except Exception as e:
    fail("не удалось подключиться к свободной таблице", e)
    sys.exit(2)

step(2, f"SELECT TOP 1 * FROM {TARGET_TABLE}")
try:
    cur = src.cursor()
    cur.execute(f"SELECT TOP 1 * FROM {TARGET_TABLE}")
    desc = cur.description
    row = cur.fetchone()
    ok(f"колонок: {len(desc)}")
    print(f"         имена: {[d[0] for d in desc]}")
    if row is not None:
        # repr на случай странных символов
        print(f"         первая строка: {tuple(repr(v)[:40] for v in row)}")
    else:
        print(f"         таблица пустая")
    cur.close()
except Exception as e:
    fail(f"SELECT по таблице {TARGET_TABLE} упал — скорее всего проблема с collation/индексом", e)
    src.close()
    sys.exit(3)

step(3, f"COUNT(*) FROM {TARGET_TABLE}")
try:
    cur = src.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {TARGET_TABLE}")
    n = cur.fetchone()[0]
    ok(f"в источнике строк: {n}")
    cur.close()
except Exception as e:
    fail("COUNT(*) упал", e)

src.close()
ok("src соединение закрыто")

# ---------------------------------------------------------------------------
hr("DESTINATION: через словарь DICT.ADD")

step(4, "pyodbc.connect(DST, autocommit=True)")
dst = None
try:
    dst = pyodbc.connect(DST_CONN_STR, autocommit=True)
    ok("соединение открыто")
except Exception as e:
    fail("не удалось подключиться к словарю", e)
    sys.exit(4)

step(5, f"SELECT TOP 1 * FROM {TARGET_TABLE} (через словарь)")
try:
    cur = dst.cursor()
    cur.execute(f"SELECT TOP 1 * FROM {TARGET_TABLE}")
    desc = cur.description
    row = cur.fetchone()
    ok(f"колонок: {len(desc)}")
    print(f"         имена: {[d[0] for d in desc]}")
    if row is not None:
        print(f"         первая строка: {tuple(repr(v)[:40] for v in row)}")
    else:
        print(f"         таблица пустая")
    cur.close()
except Exception as e:
    fail(f"SELECT через словарь упал. ВЕРОЯТНО — нужны collation-файлы и в {os.path.dirname(DST_CONN_STR.split('DataDirectory=')[1].split(';')[0])}", e)

step(6, f"COUNT(*) FROM {TARGET_TABLE} (через словарь)")
try:
    cur = dst.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {TARGET_TABLE}")
    n = cur.fetchone()[0]
    ok(f"в приёмнике сейчас строк: {n}")
    cur.close()
except Exception as e:
    fail("COUNT(*) на приёмнике упал", e)

step(7, "BEGIN TRANSACTION / ROLLBACK WORK (проверка, что транзакции работают)")
try:
    cur = dst.cursor()
    cur.execute("BEGIN TRANSACTION")
    cur.execute("ROLLBACK WORK")
    ok("транзакции на словаре работают")
    cur.close()
except Exception as e:
    fail("транзакции на словаре не работают — но это не критично, можно перенос делать без них", e)

dst.close()
ok("dst соединение закрыто")

# ---------------------------------------------------------------------------
hr("ИТОГ")
print("  Если выше все шаги [OK] — значит _7.py должен пройти боевой прогон.")
print("  Запускай: python .\\_7.py")
