"""Build the DuckDB warehouse from the raw survey CSV.

Usage:  python -I src/pipeline.py  (run from the project root)
"""
from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "coffee_survey.csv"
DB = ROOT / "outputs" / "coffee_survey.duckdb"
SQL_FILES = [ROOT / "sql" / "01_staging.sql", ROOT / "sql" / "02_marts.sql"]


def build(db_path: Path = DB, raw_path: Path = RAW) -> duckdb.DuckDBPyConnection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute("SET VARIABLE raw_path = ?", [str(raw_path)])
    for f in SQL_FILES:
        con.execute(f.read_text())
    return con


if __name__ == "__main__":
    con = build()
    print(con.sql("SELECT * FROM mart_exclusions"))
    print(con.sql("SELECT * FROM mart_completion"))
    con.close()
