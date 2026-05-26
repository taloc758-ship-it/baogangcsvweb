from __future__ import annotations

import csv
import io
import os
import sys
import threading
from datetime import datetime
from difflib import SequenceMatcher
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
LOG_DIR = BASE_DIR / "logs"

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


def pad_row(row: list[str], width: int) -> list[str]:
    return row[:width] + [""] * (width - len(row))


def build_change_record(
    display_path: str,
    old_headers: list[str],
    old_rows: list[list[str]],
    new_headers: list[str],
    new_rows: list[list[str]],
    old_encoding: str,
    new_encoding: str,
    old_delimiter: str,
    new_delimiter: str,
) -> dict:
    old_headers, old_rows = normalize_table(old_headers, old_rows)
    new_headers, new_rows = normalize_table(new_headers, new_rows)

    width = max(
        [len(old_headers), len(new_headers), *(len(row) for row in old_rows), *(len(row) for row in new_rows)] or [0]
    )
    old_headers = old_headers[:width] + [""] * (width - len(old_headers))
    new_headers = new_headers[:width] + [""] * (width - len(new_headers))
    old_rows = [pad_row(row, width) for row in old_rows]
    new_rows = [pad_row(row, width) for row in new_rows]

    header_changes = []
    for index in range(width):
        old_value = old_headers[index]
        new_value = new_headers[index]
        if old_value != new_value:
            header_changes.append(
                {
                    "column": index + 1,
                    "old": old_value,
                    "new": new_value,
                }
            )

    added_rows = []
    deleted_rows = []
    cell_changes = []
    matcher = SequenceMatcher(a=[tuple(row) for row in old_rows], b=[tuple(row) for row in new_rows], autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "insert":
            for row_index in range(j1, j2):
                added_rows.append({"row": row_index + 1, "values": new_rows[row_index]})
            continue
        if tag == "delete":
            for row_index in range(i1, i2):
                deleted_rows.append({"row": row_index + 1, "values": old_rows[row_index]})
            continue

        old_block = old_rows[i1:i2]
        new_block = new_rows[j1:j2]
        overlap = min(len(old_block), len(new_block))
        for offset in range(overlap):
            old_row_number = i1 + offset + 1
            new_row_number = j1 + offset + 1
            old_row = old_block[offset]
            new_row = new_block[offset]
            for column_index, (old_cell, new_cell) in enumerate(zip(old_row, new_row), start=1):
                if old_cell == new_cell:
                    continue
                header_name = new_headers[column_index - 1] or old_headers[column_index - 1] or f"列{column_index}"
                cell_changes.append(
                    {
                        "row": new_row_number,
                        "oldRow": old_row_number,
                        "newRow": new_row_number,
                        "column": column_index,
                        "header": header_name,
                        "old": old_cell,
                        "new": new_cell,
                    }
                )

        for offset in range(overlap, len(old_block)):
            row_number = i1 + offset + 1
            deleted_rows.append({"row": row_number, "values": old_block[offset]})

        for offset in range(overlap, len(new_block)):
            row_number = j1 + offset + 1
            added_rows.append({"row": row_number, "values": new_block[offset]})

    format_changes = []
    if old_encoding != new_encoding:
        format_changes.append({"field": "encoding", "old": old_encoding, "new": new_encoding})
    if old_delimiter != new_delimiter:
        format_changes.append({"field": "delimiter", "old": old_delimiter, "new": new_delimiter})

    summary = {
        "headerChanges": len(header_changes),
        "cellChanges": len(cell_changes),
        "addedRows": len(added_rows),
        "deletedRows": len(deleted_rows),
        "formatChanges": len(format_changes),
    }
    has_changes = any(summary.values())

    return {
        "file": display_path,
        "oldHeaders": old_headers,
        "newHeaders": new_headers,
        "summary": summary,
        "headerChanges": header_changes,
        "cellChanges": cell_changes,
        "addedRows": added_rows,
        "deletedRows": deleted_rows,
        "formatChanges": format_changes,
        "hasChanges": has_changes,
    }


def format_log_value(value: str) -> str:
    text = str(value).replace("\r\n", " / ").replace("\n", " / ").replace("\r", " / ").strip()
    return text if text else "（空）"


def group_cell_changes_by_row(cell_changes: list[dict]) -> list[tuple[int, list[dict]]]:
    grouped: dict[int, list[dict]] = {}
    row_order: list[int] = []
    for item in cell_changes:
        row_number = item["row"]
        if row_number not in grouped:
            grouped[row_number] = []
            row_order.append(row_number)
        grouped[row_number].append(item)
    return [(row_number, grouped[row_number]) for row_number in row_order]


def build_row_text_lines(headers: list[str], values: list[str]) -> list[str]:
    lines = []
    for index, value in enumerate(values, start=1):
        header = headers[index - 1] if index - 1 < len(headers) else ""
        title = header or f"第{index}列"
        if header or str(value).strip():
            lines.append(f"    {title}：{format_log_value(value)}")
    if not lines:
        lines.append("    （整行为空）")
    return lines


def format_change_log_entry(change_record: dict, timestamp: datetime) -> str:
    modified_row_count = len(group_cell_changes_by_row(change_record["cellChanges"]))
    lines = [
        f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] 文件：{change_record['file']}",
    ]

    for item in change_record["formatChanges"]:
        label = "编码" if item["field"] == "encoding" else "分隔符"
        if "格式调整：" not in lines:
            lines.append("格式调整：")
        lines.append(f"  {label}：{format_log_value(item['old'])} -> {format_log_value(item['new'])}")

    if change_record["headerChanges"]:
        lines.append("列标题调整：")
        for item in change_record["headerChanges"]:
            lines.append(
                f"  第{item['column']}列：{format_log_value(item['old'])} -> {format_log_value(item['new'])}"
            )

    if change_record["cellChanges"]:
        lines.append("修改内容：")
        for row_number, items in group_cell_changes_by_row(change_record["cellChanges"]):
            lines.append(f"  第{row_number}行：")
            for item in items:
                lines.append(
                    f"    {item['header']}：{format_log_value(item['old'])} -> {format_log_value(item['new'])}"
                )

    if change_record["addedRows"]:
        lines.append("新增行：")
        for item in change_record["addedRows"]:
            lines.append(f"  第{item['row']}行：")
            lines.extend(build_row_text_lines(change_record["newHeaders"], item["values"]))

    if change_record["deletedRows"]:
        lines.append("删除行：")
        for item in change_record["deletedRows"]:
            lines.append(f"  第{item['row']}行：")
            lines.extend(build_row_text_lines(change_record["oldHeaders"], item["values"]))

    summary = change_record["summary"]
    summary_parts = [
        f"修改{modified_row_count}行",
        f"新增{summary['addedRows']}行",
        f"删除{summary['deletedRows']}行",
    ]
    lines.append("摘要：" + "，".join(summary_parts))
    lines.append("-" * 72)
    return "\n".join(lines) + "\n"


def append_change_log(change_record: dict) -> str | None:
    if not change_record["hasChanges"]:
        return None

    timestamp = datetime.now()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"csv-change-{timestamp:%Y-%m-%d}.log"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(format_change_log_entry(change_record, timestamp))
    return log_path.name


@app.get("/", response_class=FileResponse)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "runtimeDir": str(BASE_DIR),
        "csvRoot": str(CSV_ROOT),
        "logDir": str(LOG_DIR),
    }


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
    log_file_name = None
    with FILE_LOCK:
        current = read_csv_table(file_path)
        headers, rows = normalize_table(payload.headers, payload.rows)
        encoding = payload.encoding or current["encoding"]
        delimiter = payload.delimiter or current["delimiter"] or ","
        change_record = build_change_record(
            display_path=current["path"],
            old_headers=current["headers"],
            old_rows=current["rows"],
            new_headers=headers,
            new_rows=rows,
            old_encoding=current["encoding"],
            new_encoding=encoding,
            old_delimiter=current["delimiter"],
            new_delimiter=delimiter,
        )

        if change_record["hasChanges"]:
            write_csv_table(file_path, headers, rows, encoding, delimiter)
            updated = read_csv_table(file_path)
            log_file_name = append_change_log(change_record)
        else:
            updated = current

    return JSONResponse(
        {
            "ok": True,
            "path": updated["path"],
            "encoding": updated["encoding"],
            "rowCount": updated["rowCount"],
            "columnCount": updated["columnCount"],
            "changed": change_record["hasChanges"],
            "logFile": log_file_name,
            "logPath": str((LOG_DIR / log_file_name).resolve()) if log_file_name else "",
        }
    )


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("CSVWEB_HOST", "0.0.0.0")
    port = int(os.environ.get("CSVWEB_PORT", "8765"))
    uvicorn.run(app, host=host, port=port)
