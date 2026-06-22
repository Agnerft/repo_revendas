import json
import os
import re
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
                synced_at TEXT NOT NULL,
                revenda TEXT NOT NULL DEFAULT '',
                dt_row_id TEXT NOT NULL DEFAULT '',
                id_client TEXT NOT NULL DEFAULT '',
                nome TEXT NOT NULL DEFAULT '',
                telefone TEXT NOT NULL DEFAULT '',
                telefone_digits TEXT NOT NULL DEFAULT '',
                data_expiracao TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS sync_status (
                source TEXT PRIMARY KEY,
                total_records INTEGER NOT NULL,
                synced_at TEXT NOT NULL
            );
            """
        )
        existing_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(clientes_snapshot)")
        }
        required_columns = {
            "revenda": "TEXT NOT NULL DEFAULT ''",
            "dt_row_id": "TEXT NOT NULL DEFAULT ''",
            "id_client": "TEXT NOT NULL DEFAULT ''",
            "nome": "TEXT NOT NULL DEFAULT ''",
            "telefone": "TEXT NOT NULL DEFAULT ''",
            "telefone_digits": "TEXT NOT NULL DEFAULT ''",
            "data_expiracao": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in required_columns.items():
            if column not in existing_columns:
                connection.execute(
                    f"ALTER TABLE clientes_snapshot ADD COLUMN {column} {definition}"
                )

        connection.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_clientes_snapshot_telefone
                ON clientes_snapshot(telefone COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_clientes_snapshot_telefone_digits
                ON clientes_snapshot(telefone_digits);
            CREATE INDEX IF NOT EXISTS idx_clientes_snapshot_id_client
                ON clientes_snapshot(id_client);
            CREATE INDEX IF NOT EXISTS idx_clientes_snapshot_dt_row_id
                ON clientes_snapshot(dt_row_id);
            CREATE INDEX IF NOT EXISTS idx_clientes_snapshot_nome
                ON clientes_snapshot(nome COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_clientes_snapshot_revenda
                ON clientes_snapshot(revenda COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_clientes_snapshot_data_expiracao
                ON clientes_snapshot(data_expiracao);
            """
        )
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
            (1, datetime.now(timezone.utc).isoformat()),
        )
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
            (2, datetime.now(timezone.utc).isoformat()),
        )


def sync_excel_snapshot(database_path, dataframe):
    """Store an Excel snapshot without changing the application's read path."""
    synced_at = datetime.now(timezone.utc).isoformat()
    records = []

    for source_row, row in enumerate(dataframe.to_dict(orient="records"), start=2):
        normalized = {str(key): str(value or "") for key, value in row.items()}
        telefone = normalized.get("telefone", "")
        records.append(
            (
                source_row,
                json.dumps(normalized, ensure_ascii=False, separators=(",", ":")),
                " ".join(normalized.values()).lower(),
                synced_at,
                normalized.get("Revenda", ""),
                normalized.get("DT_RowId", ""),
                normalized.get("Id_client", ""),
                normalized.get("nome", ""),
                telefone,
                re.sub(r"[^\d]", "", telefone),
                normalized.get("data_expiracao", ""),
            )
        )

    with _connect(database_path) as connection:
        connection.execute("DELETE FROM clientes_snapshot")
        connection.executemany(
            """
            INSERT INTO clientes_snapshot(
                source_row, dados_json, search_text, synced_at, revenda, dt_row_id,
                id_client, nome, telefone, telefone_digits, data_expiracao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
