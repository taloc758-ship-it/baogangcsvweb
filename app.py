from __future__ import annotations

import csv
import io
import os
import sys
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

def get_runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = get_runtime_dir()
DEFAULT_CSV_ROOT = Path(r"D:\workspace\code\bin\工艺规程文件")
CSV_ROOT = Path(os.environ.get("CSVWEB_CSV_ROOT", str(DEFAULT_CSV_ROOT))).resolve()
STATIC_DIR = Path(os.environ.get("CSVWEB_STATIC_DIR", str(BASE_DIR / "static"))).resolve()

app = FastAPI(title="CSV Web Editor", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

FILE_LOCK = threading.Lock()
ENCODING_CANDIDATES = ("utf-8-sig", "utf-8", "gb18030", "gbk")


class SavePayload(BaseModel):
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    encoding: str | None = None
    delimiter: str = ","


def resolve_csv_path(rel_path: str) -> Path:
    if not rel_path:
        raise HTTPException(status_code=400, detail="path 不能为空")

    rel = Path(rel_path.replace("\\", "/"))
    if rel.is_absolute() or any(part == ".." for part in rel.parts):
        raise HTTPException(status_code=400, detail="非法路径")

    candidate = (CSV_ROOT / rel).resolve()
    if candidate != CSV_ROOT and CSV_ROOT not in candidate.parents:
        raise HTTPException(status_code=400, detail="非法路径")
    if candidate.suffix.lower() != ".csv":
        raise HTTPException(status_code=400, detail="只允许 CSV 文件")
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return candidate


def detect_encoding(raw: bytes) -> tuple[str, str]:
    last_error: Exception | None = None
    for encoding in ENCODING_CANDIDATES:
        try:
            return encoding, raw.decode(encoding)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    if last_error:
        _ = last_error
    return "gb18030", raw.decode("gb18030", errors="replace")


def sniff_dialect(text: str) -> csv.Dialect:
    sample = text[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except Exception:  # noqa: BLE001
        return csv.get_dialect("excel")


def trim_trailing_empty_rows(rows: list[list[str]]) -> list[list[str]]:
    trimmed = [list(row) for row in rows]
    while trimmed and not any(str(cell).strip() for cell in trimmed[-1]):
        trimmed.pop()
    return trimmed


def normalize_table(headers: list[str], rows: list[list[str]]) -> tuple[list[str], list[list[str]]]:
    headers = ["" if cell is None else str(cell) for cell in headers]
    rows = [[("" if cell is None else str(cell)) for cell in row] for row in rows]
    rows = trim_trailing_empty_rows(rows)

    width = max([len(headers), *(len(row) for row in rows)] or [0])
    if width == 0:
        return [], []

    normalized_headers = headers[:width]
    if len(normalized_headers) < width:
        normalized_headers.extend(f"列{index + 1}" for index in range(len(normalized_headers), width))
    normalized_rows: list[list[str]] = []
    for row in rows:
        normalized_rows.append(row[:width] + [""] * (width - len(row)))

    return normalized_headers, normalized_rows


def read_csv_table(path: Path) -> dict:
    raw = path.read_bytes()
    encoding, text = detect_encoding(raw)
    dialect = sniff_dialect(text)
    reader = csv.reader(io.StringIO(text), dialect)
    rows = [row for row in reader]
    rows = trim_trailing_empty_rows(rows)

    if not rows:
        headers, data_rows = [], []
    else:
        headers, data_rows = rows[0], rows[1:]

    headers, data_rows = normalize_table(headers, data_rows)
    try:
        display_path = path.relative_to(CSV_ROOT).as_posix()
    except ValueError:
        display_path = path.name

    return {
        "path": display_path,
        "encoding": encoding,
        "delimiter": getattr(dialect, "delimiter", ","),
        "headers": headers,
        "rows": data_rows,
        "rowCount": len(data_rows),
        "columnCount": len(headers),
    }


def write_csv_table(path: Path, headers: list[str], rows: list[list[str]], encoding: str, delimiter: str) -> None:
    headers, rows = normalize_table(headers, rows)
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter or ",", lineterminator="\r\n")
    if headers or rows:
        writer.writerow(headers)
        writer.writerows(rows)

    tmp_path = path.with_name(path.name + ".tmp")
    with tmp_path.open("w", encoding=encoding, newline="") as fh:
        fh.write(buffer.getvalue())
    os.replace(tmp_path, path)


@app.get("/", response_class=FileResponse)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/files")
def list_files() -> dict:
    files = []
    for path in sorted(CSV_ROOT.rglob("*.csv")):
        try:
            meta = read_csv_table(path)
            files.append(
                {
                    "path": meta["path"],
                    "rowCount": meta["rowCount"],
                    "columnCount": meta["columnCount"],
                    "encoding": meta["encoding"],
                }
            )
        except Exception as exc:  # noqa: BLE001
            files.append(
                {
                    "path": path.relative_to(CSV_ROOT).as_posix(),
                    "error": str(exc),
                }
            )
    return {"root": CSV_ROOT.as_posix(), "files": files}


@app.get("/api/file")
def get_file(path: str = Query(..., description="相对路径，例如 config.csv")) -> dict:
    file_path = resolve_csv_path(path)
    return read_csv_table(file_path)


@app.put("/api/file")
def save_file(path: str = Query(..., description="相对路径，例如 config.csv"), payload: SavePayload | None = None) -> JSONResponse:
    if payload is None:
        raise HTTPException(status_code=400, detail="缺少保存内容")

    file_path = resolve_csv_path(path)
    current = read_csv_table(file_path)
    encoding = payload.encoding or current["encoding"]
    delimiter = payload.delimiter or current["delimiter"] or ","

    with FILE_LOCK:
        write_csv_table(file_path, payload.headers, payload.rows, encoding, delimiter)

    updated = read_csv_table(file_path)
    return JSONResponse(
        {
            "ok": True,
            "path": updated["path"],
            "encoding": updated["encoding"],
            "rowCount": updated["rowCount"],
            "columnCount": updated["columnCount"],
        }
    )


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("CSVWEB_HOST", "0.0.0.0")
    port = int(os.environ.get("CSVWEB_PORT", "8765"))
    uvicorn.run(app, host=host, port=port)
