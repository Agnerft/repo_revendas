import json
import os
import sqlite3
from datetime import datetime, timezone


def _connect(database_path):
    connection = sqlite3.connect(database_path, timeout=30)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA busy_timeout=30000")
    return connection


def init_database(database_path):
    os.makedirs(os.path.dirname(os.path.abspath(database_path)), exist_ok=True)

    with _connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS clientes_snapshot (
                source_row INTEGER PRIMARY KEY,
                dados_json TEXT NOT NULL,
                search_text TEXT NOT NULL,
                synced_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_clientes_snapshot_search_text
                ON clientes_snapshot(search_text);

            CREATE TABLE IF NOT EXISTS sync_status (
                source TEXT PRIMARY KEY,
                total_records INTEGER NOT NULL,
                synced_at TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
            (1, datetime.now(timezone.utc).isoformat()),
        )


def sync_excel_snapshot(database_path, dataframe):
    """Store an Excel snapshot without changing the application's read path."""
    synced_at = datetime.now(timezone.utc).isoformat()
    records = []

    for source_row, row in enumerate(dataframe.to_dict(orient="records"), start=2):
        normalized = {str(key): str(value or "") for key, value in row.items()}
        records.append(
            (
                source_row,
                json.dumps(normalized, ensure_ascii=False, separators=(",", ":")),
                " ".join(normalized.values()).lower(),
                synced_at,
            )
        )

    with _connect(database_path) as connection:
        connection.execute("DELETE FROM clientes_snapshot")
        connection.executemany(
            """
            INSERT INTO clientes_snapshot(source_row, dados_json, search_text, synced_at)
            VALUES (?, ?, ?, ?)
            """,
            records,
        )
        connection.execute(
            """
            INSERT INTO sync_status(source, total_records, synced_at)
            VALUES ('excel', ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                total_records = excluded.total_records,
                synced_at = excluded.synced_at
            """,
            (len(records), synced_at),
        )


def get_database_status(database_path):
    if not os.path.exists(database_path):
        return {"ready": False, "path": database_path, "total_records": 0, "synced_at": None}

    try:
        with _connect(database_path) as connection:
            row = connection.execute(
                "SELECT total_records, synced_at FROM sync_status WHERE source = 'excel'"
            ).fetchone()
    except sqlite3.Error as error:
        return {
            "ready": False,
            "path": database_path,
            "total_records": 0,
            "synced_at": None,
            "error": str(error),
        }

    return {
        "ready": True,
        "path": database_path,
        "total_records": row[0] if row else 0,
        "synced_at": row[1] if row else None,
        "size_bytes": os.path.getsize(database_path),
    }
