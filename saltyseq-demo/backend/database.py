import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "predictions.db"


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at   TEXT NOT NULL,
                station_id   TEXT NOT NULL,
                station_name TEXT NOT NULL,
                date         TEXT NOT NULL,
                probability  REAL NOT NULL,
                label        TEXT NOT NULL,
                confidence   TEXT NOT NULL,
                features_json TEXT,
                patterns_json TEXT
            )
        """)
        conn.commit()


def save_prediction(data: dict) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """INSERT INTO predictions
               (created_at, station_id, station_name, date, probability, label, confidence, features_json, patterns_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().isoformat(),
                data["station_id"],
                data["station_name"],
                data["date"],
                data["probability"],
                data["label"],
                data["confidence"],
                data.get("features_json"),
                data.get("patterns_json"),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_history(limit: int = 50) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM predictions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]


def delete_prediction(id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("DELETE FROM predictions WHERE id = ?", (id,))
        conn.commit()
        return cursor.rowcount > 0


def clear_history() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM predictions")
        conn.commit()
