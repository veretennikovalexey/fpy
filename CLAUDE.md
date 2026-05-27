# Project notes for Claude

This folder is a Python sandbox for working with **Advantage Database Server (ADS)** table files (`.adt`). Below is the context needed to be useful here.

## Folder layout

- `freeadt.exe` — Advantage utility that detaches an `.adt` table from its Data Dictionary, turning it into a free table that can be opened without the dictionary.
- `R09.adt` / `R09.ADI` — the table file and its index file.
- `_4.py` — reference example: connects to the table **through a dictionary** (`DICT.ADD`) as the `AdsSys` user with an empty password. NOTE: it has `ServerTypes=3` which means "try ALS, then ADS"; that only worked because the ADS service used to be running. For the current deployment (no ADS service anywhere), use `ServerTypes=1`.
- `_5.py` — early working script: runs `freeadt.exe -y R09.adt`, then connects to the **free table** (no dictionary) and reads rows. Same caveat about `ServerTypes` (see below).
- `_7.py` — batch script: reads table names from `_7.txt`, runs `freeadt` on each, then copies rows from the local free `.adt` into the dictionary-bound table. Uses `ServerTypes=1` (ALS, no service) on both ends.

All work happens on Windows at `C:\Users\raide\Desktop\fpy\`. The scripts assume their own folder contains both the executable and the data files.

## freeadt.exe usage — important

```
freeadt.exe [-pPassword] [-y] [FileName | DirectoryName ...]
```

**Always pass `-y`** when calling from a script. Without it, freeadt prints a warning and waits on stdin for `y/n`, which causes `subprocess.run(...)` to hang forever. With `-y` the prompt is suppressed.

`-pPassword` is only needed if the table is encrypted. The tables in this project are not encrypted, so no password is required.

Note: freeadt makes no backup and the table loses its extended attributes from the dictionary. Running it on an already-free table is safe — freeadt just reports it and exits.

## pyodbc connection patterns

Driver name in the connection string is `{Advantage StreamlineSQL ODBC}`.

### ServerTypes — bitmask (very important)

Confirmed against the official Advantage docs and connectionstrings.com:

- `ServerTypes=1` → **ALS** (Advantage Local Server) — fully in-process, NO Windows service required, NO network traffic. Uses `ADSLOC32.DLL`.
- `ServerTypes=2` → **ADS** (Remote Database Server) — REQUIRES the Advantage Database Server Windows service running on the host machine. If the service is stopped, the driver fails with `Error 6420: 'discovery' process for the Advantage Database Server failed`.
- `ServerTypes=4` → **AIS** (Internet, Advantage Internet Server).
- Values can be ORed: `ServerTypes=3` (= 1+2) means "try ALS first, fall back to ADS".

In this project there is NO ADS service running on the user's machine or on any of the ~20 bakeries → **always use `ServerTypes=1`**. Earlier scripts (`_4.py`, `_5.py`) had `ServerTypes=2`/`3` documented as "ALS"; that was wrong, they only worked because the service used to be up.

### Two modes that matter

**Through a dictionary**:
- `DataDirectory` points at the `.ADD` dictionary file (e.g. `C:\fabius\ohc\REFLIS\DICT.ADD`).
- `ServerTypes=1` (ALS — no service required).
- `UID=AdsSys`, `PWD=` (empty).

**Free table, no dictionary** (after `freeadt`):
- `DataDirectory` points at the **folder** containing the `.adt` files.
- `ServerTypes=1` (ALS).
- `TableType=ADT`.
- `UID=AdsSys`, `PWD=` (empty).

SQL dialect supports `SELECT TOP N * FROM <table>` — the table name matches the file basename (e.g. `R09.adt` → `FROM R09`).

### autocommit and transactions

`pyodbc.connect(...)` by default tries to call `SQLSetConnectAttr(SQL_ATTR_AUTOCOMMIT, OFF)` so it can manage transactions itself.

- **Free-table mode** (`TableType=ADT`, no dictionary) does NOT support transactions. The driver responds with `Error 2110 'Driver not capable' (SQLSetConnectAttr)` and the `pyodbc.connect()` call fails before any SQL runs. Always open free-table connections with `pyodbc.connect(CONN_STR, autocommit=True)` — note that `autocommit` is a keyword argument to `pyodbc.connect()`, NOT part of the connection string.
- **Dictionary mode** does support transactions, but the safe pattern is still `autocommit=True` at the pyodbc level plus explicit SQL transaction commands: `BEGIN TRANSACTION` / `COMMIT WORK` / `ROLLBACK WORK`. This avoids any further surprises from the pyodbc/ODBC autocommit dance.

## Runtime environment

- Real execution happens on the user's **Windows** machine where the Advantage ODBC driver is installed. Inside the Cowork Linux sandbox the driver is not available — only `python3 -m py_compile` for syntax checks is meaningful; do not try to actually run the pyodbc code from the sandbox.
- Use `subprocess.run([..., "-y", ...], cwd=BASE_DIR, capture_output=True, text=True)` rather than shell strings — paths may contain spaces and we want stdout/stderr captured.
- Resolve paths from `os.path.dirname(os.path.abspath(__file__))` so the script works no matter where it's launched from.

## User preferences for this project

- The user prefers Russian for chat responses but wants `CLAUDE.md` written in English.
- Address the user informally (на «ты»). Their name is **alex**.
- They are in Russia.
- When asked to run freeadt repeatedly, run it every time and ignore "already free" feedback — don't try to be clever about skipping it.

## Custom collation `RUSSIAN2` (Fabius-specific) — error 5175

Fabius uses a **custom ALS collation called `RUSSIAN2`** (an alternate ANSI collation, baked into a custom `ANSI.CHR`). All `.adt` indexes (`.ADI`) in Fabius tables were built under this collation.

If ALS is started without that collation active, opening any table fails with:

```
Error 5175: The index file was created with a different collation sequence than is currently being used.
```

To make ALS pick up `RUSSIAN2`, **the following files must be in either the script's current working directory or `C:\Windows\System32`**:

- `ANSI.CHR` — ANSI character set table with Fabius's RUSSIAN2 sort order.
- `EXTEND.CHR` — OEM character set table (paired with ANSI.CHR).
- `adscollate.adt` — the dynamic-collation dictionary that defines `RUSSIAN2`.
- `adscollate.adm` — memo file for `adscollate.adt`.
- `adslocal.cfg` — ALS config; tells ALS which ANSI/OEM collation to activate (`ANSI_CHAR_SET=RUSSIAN2`).

All five come from the Fabius client installation (typically next to the application `.exe` or under `C:\fabius\...`). The same set must be present in the dictionary folder used by `DST_CONN_STR` (e.g. `C:\fabius\ohc\REFLIS\`).

No code change is needed in the pyodbc scripts — ALS reads `adslocal.cfg` from the cwd automatically.

## Required DLLs for ALS-only mode

The pyodbc scripts here talk to ADS through the Windows-registered ODBC driver `{Advantage StreamlineSQL ODBC}`. The driver itself ships with its own copy of the runtime DLLs, but for completeness, the minimal set of files for a stand-alone ALS application is:

- `ACE32.DLL` — Advantage Client Engine (core).
- `ADSLOC32.DLL` — Advantage Local Server engine. Required for `ServerTypes=1`.
- `AICU32.DLL` — ICU/Unicode support.
- Supporting data files when used: `adscollate.adm`, `adscollate.adt`, `ansi.chr`, `extend.chr`, `icudt40l.dat`, `adslocal.cfg`.

Files NOT needed for local-only operation (safe to remove if they were copied from the Fabius project):

- `AXCWS32.DLL` — AIS web-service client (only needed for `ServerTypes=4`).
- `libeay32.dll`, `ssleay32.dll` — OpenSSL, needed only for AIS/HTTPS.
- `midasx.dll` — Borland MIDAS / DataSnap, unrelated to ADS.
- `Quricol.Barcode.dll`, `quricol32.dll`, `quricol64.dll`, `dmtx.dll` — barcode libraries from the host app, unrelated to ADS.

## Common pitfalls

- Forgetting `-y` on freeadt → script hangs.
- Using `ServerTypes=2` (or `3`) when no ADS service is running → `Error 6420 discovery process failed`. Use `ServerTypes=1`.
- Mis-remembering that `ServerTypes=2` means ALS. It does NOT — 1 is ALS, 2 is remote ADS.
- Calling `pyodbc.connect(CONN_STR)` on a free table → `Error 2110 'Driver not capable' (SQLSetConnectAttr SQL_ATTR_AUTOCOMMIT)`. Add `autocommit=True` to the `pyodbc.connect()` call.
- `Error 5175 different collation sequence` → ALS is running without the Fabius `RUSSIAN2` collation. Drop `ANSI.CHR`, `EXTEND.CHR`, `adscollate.adt`, `adscollate.adm`, `adslocal.cfg` from the Fabius install into the script directory and the dictionary directory. See the "Custom collation `RUSSIAN2`" section above.
- Pointing `DataDirectory` at the `.adt` file instead of the containing folder when in free-table mode.
- Assuming the Linux sandbox can execute the script — it cannot; only the user's Windows box can.
