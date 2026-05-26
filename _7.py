import os
import sys
import subprocess
import pyodbc

# Папка со скриптом (рядом — freeadt.exe, .adt-файлы, _7.txt)
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
FREEADT   = os.path.join(BASE_DIR, "freeadt.exe")
LIST_FILE = os.path.join(BASE_DIR, "_7.txt")

# Connection strings — один раз, переиспользуем
SRC_CONN_STR = (
    "Driver={Advantage StreamlineSQL ODBC};"
    f"DataDirectory={BASE_DIR};"
    "ServerTypes=2;"      # 2 = ALS, без словаря
    "TableType=ADT;"
    "UID=AdsSys;"
    "PWD=;"
)

# ServerTypes=2 — ALS (Advantage Local Server), встроенный в ODBC-драйвер.
# Не требует установленного ADS server: только adsodbc.exe на машине.
DST_CONN_STR = (
    "Driver={Advantage StreamlineSQL ODBC};"
    "DataDirectory=C:\\fabius\\ohc\\REFLIS\\DICT.ADD;"
    "ServerTypes=2;"
    "UID=AdsSys;"
    "PWD=;"
)


def read_table_list(path):
    """Читаем _7.txt: по одному имени справочника на строку.
    Пустые строки и строки, начинающиеся с '#', игнорируем."""
    names = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for raw in f:
            name = raw.strip()
            if not name or name.startswith("#"):
                continue
            names.append(name)
    return names


def free_adt(name):
    """freeadt.exe -y <name>.adt — отвязываем таблицу от словаря."""
    adt_path = os.path.join(BASE_DIR, f"{name}.adt")
    if not os.path.exists(adt_path):
        raise FileNotFoundError(f"Не найден файл {adt_path}")

    result = subprocess.run(
        [FREEADT, "-y", adt_path],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    print(f"  freeadt rc={result.returncode}  stdout={result.stdout.strip()!r}")
    if result.stderr:
        print(f"  freeadt stderr={result.stderr.strip()!r}", file=sys.stderr)


def copy_table(name):
    """Читаем все строки из локальной свободной N.adt и переносим в словарную N:
    DELETE FROM N; INSERT ... — всё в одной транзакции на стороне приёмника."""
    # Источник
    src = pyodbc.connect(SRC_CONN_STR)
    try:
        src_cur = src.cursor()
        src_cur.execute(f"SELECT * FROM {name}")
        columns = [d[0] for d in src_cur.description]
        rows = [tuple(r) for r in src_cur.fetchall()]
        src_cur.close()
    finally:
        src.close()

    print(f"  источник: строк={len(rows)}, колонок={len(columns)}")

    col_list     = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join("?" for _ in columns)
    insert_sql   = f'INSERT INTO {name} ({col_list}) VALUES ({placeholders})'

    # Приёмник — транзакция на одну таблицу
    dst = pyodbc.connect(DST_CONN_STR)
    dst.autocommit = False
    try:
        dst_cur = dst.cursor()
        dst_cur.execute(f"DELETE FROM {name}")
        deleted = dst_cur.rowcount
        print(f"  DELETE FROM {name}: затронуто {deleted}")

        if rows:
            dst_cur.executemany(insert_sql, rows)
            print(f"  INSERT INTO {name}: вставлено {len(rows)}")
        else:
            print(f"  источник пуст, INSERT пропущен")

        dst.commit()
        print(f"  commit OK")
    except Exception:
        dst.rollback()
        print(f"  rollback (ошибка при переносе)", file=sys.stderr)
        raise
    finally:
        dst.close()


def main():
    if not os.path.exists(LIST_FILE):
        print(f"Файл со списком справочников не найден: {LIST_FILE}", file=sys.stderr)
        sys.exit(1)

    names = read_table_list(LIST_FILE)
    if not names:
        print(f"В {LIST_FILE} нет ни одного имени справочника. Выходим.")
        return

    print(f"К переносу: {len(names)} таблиц(ы) → {names}")
    print("-" * 60)

    ok, failed = [], []
    for i, name in enumerate(names, 1):
        print(f"[{i}/{len(names)}] {name}")
        try:
            free_adt(name)
            copy_table(name)
            ok.append(name)
            print(f"  ✓ {name} перенесён")
        except Exception as e:
            failed.append((name, e))
            print(f"  ✗ {name}: {e}", file=sys.stderr)
        print("-" * 60)

    print(f"ИТОГО: успешно={len(ok)}, с ошибками={len(failed)}")
    if ok:
        print(f"  OK : {ok}")
    if failed:
        print(f"  FAIL:")
        for name, e in failed:
            print(f"    {name}: {e}")


if __name__ == "__main__":
    main()
