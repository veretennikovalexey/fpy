# Project notes for Claude

Small Python sandbox on Windows at `C:\Users\raide\Desktop\fpy\`.

## What `_8.py` does

For each name listed in `_8.txt` (one per line, `#`-comments ignored):

1. Try to delete `<name>.*` in `C:\fabius\ohc\REFLIS\`.
2. If any of those files is locked (held by another process), **skip this name** — don't copy anything.
3. Otherwise copy `<name>.*` from the script's folder to `C:\fabius\ohc\REFLIS\`.

No ADS, no ODBC, no `freeadt`. Pure file replacement.

Every operation is also appended to `_8.log` with a timestamp. When the log
grows past 300 KB, the older half of the lines is dropped on the next run.

## User preferences

- Russian for chat, English for `CLAUDE.md`.
- Address the user informally (на «ты»). Name: **alex**.
- Located in Russia.
- Keep answers short.
