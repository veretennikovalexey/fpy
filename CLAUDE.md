# Project notes for Claude

This folder is a Python sandbox for working with **Advantage Database Server (ADS)** table files (`.adt`). Below is the context needed to be useful here.

## Folder layout

- `freeadt.exe` — Advantage utility that detaches an `.adt` table from its Data Dictionary, turning it into a free table that can be opened without the dictionary.
- `R09.adt` / `R09.ADI` — the table file and its index file.
- `_4.py` — reference example: connects to the table **through a dictionary** (`DICT.ADD`) using `ServerTypes=3` (remote/AIS) and the `AdsSys` user with an empty password.
- `_5.py` — current working script: runs `freeadt.exe -y R09.adt`, then connects to the **free table** (no dictionary) and reads rows.

All work happens on Windows at `C:\Users\raide\Desktop\fpy\`. The scripts assume their own folder contains both the executable and the data files.

## freeadt.exe usage — important

```
freeadt.exe [-pPassword] [-y] [FileName | DirectoryName ...]
```

**Always pass `-y`** when calling from a script. Without it, freeadt prints a warning and waits on stdin for `y/n`, which causes `subprocess.run(...)` to hang forever. With `-y` the prompt is suppressed.

`-pPassword` is only needed if the table is encrypted. The tables in this project are not encrypted, so no password is required.

Note: freeadt makes no backup and the table loses its extended attributes from the dictionary. Running it on an already-free table is safe — freeadt just reports it and exits.

## pyodbc connection patterns

Driver name in the connection string is `{Advantage StreamlineSQL ODBC}`. Two modes matter:

**Through a dictionary** (as in `_4.py`):
- `DataDirectory` points at the `.ADD` dictionary file (e.g. `C:\fabius\ohc\REFLIS\DICT.ADD`).
- `ServerTypes=3` (remote/AIS).
- `UID=AdsSys`, `PWD=` (empty).

**Free table, no dictionary** (as in `_5.py`, after `freeadt`):
- `DataDirectory` points at the **folder** containing the `.adt` files.
- `ServerTypes=2` (Advantage Local Server / ALS).
- `TableType=ADT`.
- `UID=AdsSys`, `PWD=` (empty).

SQL dialect supports `SELECT TOP N * FROM <table>` — the table name matches the file basename (e.g. `R09.adt` → `FROM R09`).

## Runtime environment

- Real execution happens on the user's **Windows** machine where the Advantage ODBC driver is installed. Inside the Cowork Linux sandbox the driver is not available — only `python3 -m py_compile` for syntax checks is meaningful; do not try to actually run the pyodbc code from the sandbox.
- Use `subprocess.run([..., "-y", ...], cwd=BASE_DIR, capture_output=True, text=True)` rather than shell strings — paths may contain spaces and we want stdout/stderr captured.
- Resolve paths from `os.path.dirname(os.path.abspath(__file__))` so the script works no matter where it's launched from.

## User preferences for this project

- The user prefers Russian for chat responses but wants `CLAUDE.md` written in English.
- Address the user informally (на «ты»). Their name is **alex**.
- They are in Russia.
- When asked to run freeadt repeatedly, run it every time and ignore "already free" feedback — don't try to be clever about skipping it.

## Common pitfalls

- Forgetting `-y` on freeadt → script hangs.
- Using `ServerTypes=3` after freeing the table → driver still expects a dictionary; switch to `ServerTypes=2` + `TableType=ADT`.
- Pointing `DataDirectory` at the `.adt` file instead of the containing folder when in free-table mode.
- Assuming the Linux sandbox can execute the script — it cannot; only the user's Windows box can.
