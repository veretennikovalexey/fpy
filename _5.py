import os
import subprocess
import sys
import pyodbc

# Папка, где лежит сам скрипт (и рядом freeadt.exe, R09.adt)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FREEADT  = os.path.join(BASE_DIR, "freeadt.exe")
ADT_FILE = os.path.join(BASE_DIR, "R09.adt")

# 1) Отвязываем R09.adt от словаря — запускаем freeadt.exe
#    (вызываем всегда; если файл уже свободен, freeadt просто сообщит об этом)
result = subprocess.run(
    [FREEADT, "-y", ADT_FILE],
    cwd=BASE_DIR,
    capture_output=True,
    text=True,
)
print("freeadt stdout:", result.stdout.strip())
if result.stderr:
    print("freeadt stderr:", result.stderr.strip(), file=sys.stderr)
print("freeadt returncode:", result.returncode)

# 2) Подключаемся к свободной таблице (без словаря) и читаем 2 строки
conn_str = (
    "Driver={Advantage StreamlineSQL ODBC};"
    f"DataDirectory={BASE_DIR};"
    "ServerTypes=2;"      # 2 = ALS (Advantage Local Server), без словаря
    "TableType=ADT;"
    "UID=AdsSys;"
    "PWD=;"
)

conn = pyodbc.connect(conn_str)
cursor = conn.cursor()
cursor.execute("SELECT TOP 2 * FROM R09")
for row in cursor.fetchall():
    print(row)
cursor.close()
conn.close()
