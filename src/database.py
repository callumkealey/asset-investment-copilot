from __future__ import annotations

from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "copilot.db"


def initialise_database(portfolio: pd.DataFrame, db_path: Path = DB_PATH) -> Path:
    with sqlite3.connect(db_path) as conn:
        portfolio.to_sql("projects", conn, if_exists="replace", index=False)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_project_id ON projects(project_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_asset_id ON projects(asset_id)")
    return db_path


def get_project(project_id: str, db_path: Path = DB_PATH) -> dict | None:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        return dict(row) if row else None


def query_projects(sql: str, params: tuple = (), db_path: Path = DB_PATH) -> list[dict]:
    if not sql.lstrip().lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed")
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
