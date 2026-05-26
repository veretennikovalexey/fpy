import pyodbc

conn_str = (
    "Driver={Advantage StreamlineSQL ODBC};"
    "DataDirectory=C:\\fabius\\ohc\\REFLIS\\DICT.ADD;"  
    "ServerTypes=3;"       
    "UID=AdsSys;"
    "PWD=;"
)

conn = pyodbc.connect(conn_str)
cursor = conn.cursor()
cursor.execute("SELECT TOP 5 * FROM R09")
for row in cursor.fetchall():
    print(row)
cursor.close()
conn.close()