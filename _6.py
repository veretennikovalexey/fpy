import os
import sys
import pyodbc

# Папка со скриптом (рядом лежит локальная свободная R09.adt — её освобождал _5.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Источник: свободная таблица R09.adt в нашей папке (без словаря, ALS)
src_conn_str = (
    "Driver={Advantage StreamlineSQL ODBC};"
    f"DataDirectory={BASE_DIR};"
    "ServerTypes=2;"      # 2 = Advantage Local Server, без словаря
    "TableType=ADT;"
    "UID=AdsSys;"
    "PWD=;"
)

# Назначение: таблица R09 в словаре C:\fabius\ohc\REFLIS\DICT.ADD
# ServerTypes=2 — ALS (Advantage Local Server), встроенный в ODBC-драйвер.
# Не требует установленного ADS server: только adsodbc.exe на машине.
dst_conn_str = (
    "Driver={Advantage StreamlineSQL ODBC};"
    "DataDirectory=C:\\fabius\\ohc\\REFLIS\\DICT.ADD;"
    "ServerTypes=2;"
    "UID=AdsSys;"
    "PWD=;"
)

# 1) Читаем все строки из локальной R09.adt
src = pyodbc.connect(src_conn_str)
src_cur = src.cursor()
src_cur.execute("SELECT * FROM R09")
columns = [d[0] for d in src_cur.description]
rows = [tuple(r) for r in src_cur.fetchall()]
src_cur.close()
src.close()

print(f"Из локальной R09.adt прочитано строк: {len(rows)}")
print(f"Колонки ({len(columns)}): {columns}")

if not rows:
    print("Источник пуст — нечего вставлять. Выходим.")
    sys.exit(0)

# 2) Подключаемся к словарной R09: DELETE + INSERT в одной транзакции
dst = pyodbc.connect(dst_conn_str)
dst.autocommit = False
dst_cur = dst.cursor()

col_list     = ", ".join(f'"{c}"' for c in columns)
placeholders = ", ".join("?" for _ in columns)
insert_sql   = f'INSERT INTO R09 ({col_list}) VALUES ({placeholders})'

try:
    dst_cur.execute("DELETE FROM R09")
    deleted = dst_cur.rowcount
    print(f"DELETE FROM R09 — затронуто строк: {deleted}")

    dst_cur.executemany(insert_sql, rows)
    print(f"INSERT INTO R09 — вставлено строк: {len(rows)}")

    dst.commit()
    print("Транзакция закоммичена.")
except Exception as e:
    dst.rollback()
    print(f"Ошибка, откат транзакции: {e}", file=sys.stderr)
    raise
finally:
    dst_cur.close()
    dst.close()
