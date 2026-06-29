"""Export a SQLite database to neutral Markdown notes.

This script is intentionally schema-agnostic. It skips SQLite internal tables
and writes generated Markdown to a caller-provided directory. Generated output
should stay out of Git unless it is deliberately curated.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sqlite3
from pathlib import Path
from typing import Any


INTERNAL_TABLE_PREFIX = "sqlite_"


def safe_filename(value: Any, fallback: str = "row") -> str:
    text = str(value if value is not None else fallback)
    text = re.sub(r'[\\/:*?"<>|&#;\[\]\n\r\t]', " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return (text or fallback)[:80]


def quote_yaml(value: Any) -> str:
    text = str(value).replace("\n", " ").replace('"', "'")
    return f'"{text[:200]}"'


def list_user_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    return [row[0] for row in rows if not row[0].startswith(INTERNAL_TABLE_PREFIX)]


def choose_name_column(columns: list[str]) -> str:
    preferred = ("name", "title", "id", "key", "code")
    lowered = {col.lower(): col for col in columns}
    for candidate in preferred:
        if candidate in lowered:
            return lowered[candidate]
    return columns[0]


def render_row(table: str, columns: list[str], row: sqlite3.Row, name_column: str) -> str:
    row_dict = {col: row[col] for col in columns}
    title = str(row_dict.get(name_column) or "Untitled")
    lines = ["---", f"type: {quote_yaml(table)}"]
    for col, value in row_dict.items():
        if value is not None and str(value).strip():
            lines.append(f"{col}: {quote_yaml(value)}")
    lines.extend(["---", "", f"# {title}", "", "| Field | Value |", "|---|---|"])
    for col, value in row_dict.items():
        if value is not None and str(value).strip():
            clean = str(value).replace("\n", "<br>")[:1000]
            lines.append(f"| {col} | {clean} |")
    lines.append("")
    return "\n".join(lines)


def export_db(db_path: Path, output_dir: Path, clean: bool = False) -> dict[str, int]:
    if not db_path.exists():
        raise FileNotFoundError(db_path)
    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    stats: dict[str, int] = {}
    try:
        for table in list_user_tables(conn):
            columns = [row[1] for row in conn.execute(f"PRAGMA table_info([{table}])").fetchall()]
            if not columns:
                continue
            name_column = choose_name_column(columns)
            table_dir = output_dir / safe_filename(table, "table")
            table_dir.mkdir(parents=True, exist_ok=True)
            count = 0
            for row in conn.execute(f"SELECT * FROM [{table}]"):
                base_name = safe_filename(row[name_column], f"{table}_{count + 1}")
                target = table_dir / f"{base_name}.md"
                if target.exists():
                    target = table_dir / f"{base_name}_{count + 1}.md"
                target.write_text(render_row(table, columns, row, name_column), encoding="utf-8")
                count += 1
            stats[table] = count
    finally:
        conn.close()

    index = ["# Export Index", ""]
    for table, count in stats.items():
        table_name = safe_filename(table, "table")
        index.append(f"- [{table}](./{table_name}/) - {count} rows")
    (output_dir / "INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Export SQLite tables to Markdown notes.")
    parser.add_argument("db", type=Path, help="SQLite database path.")
    parser.add_argument("output", type=Path, help="Output directory.")
    parser.add_argument("--clean", action="store_true", help="Delete output directory before export.")
    args = parser.parse_args()
    stats = export_db(args.db, args.output, args.clean)
    print(f"exported {sum(stats.values())} rows from {len(stats)} tables to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
