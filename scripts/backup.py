"""Consistent, offline backup of the SQLite database, including active WAL pages.

Usage: python -m scripts.backup --output backups/chronos-2026-10-27.sqlite3
Runs without an application server. NEVER overwrites an existing backup.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import os
import sqlite3
import tempfile
from pathlib import Path
from urllib.parse import quote

from app.main import DEFAULT_DB


def make_backup(source: Path, destination: Path) -> Path:
    source = Path(source).expanduser().resolve()
    destination = Path(destination).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"База данных не найдена: {source}")
    if source == destination:
        raise ValueError("Исходная база и резервная копия не должны совпадать")
    if destination.exists():
        raise FileExistsError(f"Резервная копия уже существует: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = None
    try:
        # Must not create an empty database if the path is misspelled.
        with closing(sqlite3.connect(f"file:{quote(source.as_posix(), safe='/:')}?mode=ro", uri=True, timeout=10.0)) as src:
            with tempfile.NamedTemporaryFile(prefix=".chronos-", suffix=".sqlite3",
                                             dir=destination.parent, delete=False) as tmp:
                tmp_path = Path(tmp.name)
            if os.name != "nt":
                os.chmod(tmp_path, 0o600)
            with closing(sqlite3.connect(tmp_path, timeout=10.0)) as dst:
                src.backup(dst)
                result = dst.execute("PRAGMA integrity_check").fetchone()[0]
                if result != "ok":
                    raise sqlite3.DatabaseError(f"Резервная копия повреждена: {result}")
            # Fail if the destination appeared during backup; never overwrite.
            # Hard-link is atomic and raises FileExistsError on conflicts.
            os.link(tmp_path, destination)
            return destination
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Создать целостную резервную копию Chronos Team")
    parser.add_argument("--database", type=Path, default=DEFAULT_DB, help="Путь к SQLite-базе")
    parser.add_argument("--output", type=Path, required=True, help="Новый файл резервной копии")
    args = parser.parse_args()
    print(f"Резервная копия создана: {make_backup(args.database, args.output)}")


if __name__ == "__main__":
    main()
