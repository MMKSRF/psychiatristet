import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Iterator

logger = logging.getLogger("backend_database")

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_FILE = "fulldb.db"

# Database path resolution: env var, or fulldb.db in root project dir
_db_env = os.getenv("DATABASE_PATH", "").strip()
if _db_env:
    DB_PATH = Path(_db_env) if Path(_db_env).is_absolute() else (ROOT_DIR / _db_env)
else:
    DB_PATH = ROOT_DIR / DEFAULT_DB_FILE

DATA_DIR = Path(__file__).resolve().parent
_DB_LOCK = RLock()


def get_db_path() -> Path:
    return DB_PATH


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection configured for high performance and integrity."""
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """Context manager for atomic write transactions with thread locking."""
    with _DB_LOCK:
        conn = sqlite3.connect(str(DB_PATH), timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def init_db(db_path: Path | None = None) -> None:
    """Initialize SQLite database, apply WAL optimizations, and run migration."""
    target_path = db_path or DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with _DB_LOCK:
        conn = sqlite3.connect(str(target_path), timeout=30.0, check_same_thread=False)
        try:
            # High-performance optimizations for 1GB RAM / SSD server:
            # - WAL (Write-Ahead-Log): Allows concurrent reads during writes without lock blocking
            # - synchronous = NORMAL: Blazing fast write speed while remaining WAL-safe
            # - cache_size = -2000: Limits SQLite RAM cache to ~2MB (ideal for 1GB RAM)
            # - temp_store = MEMORY: Speeds up temporary sorting and grouping
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA cache_size = -2000;")
            conn.execute("PRAGMA temp_store = MEMORY;")

            # 1. Accounts Table (Admin & Clinicians)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    psychiatrist_id INTEGER,
                    created_at TEXT NOT NULL
                );
                """
            )

            # 2. Psychiatrists Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS psychiatrists (
                    psychiatrist_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    email TEXT,
                    field TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Active',
                    max_patients INTEGER NOT NULL DEFAULT 5,
                    password_hash TEXT,
                    must_change_password INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT
                );
                """
            )

            # 3. Patients Table (Supports Amharic and English)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS patients (
                    telegram_id INTEGER PRIMARY KEY,
                    telegram_username TEXT DEFAULT '',
                    name TEXT NOT NULL,
                    age INTEGER,
                    complaint TEXT,
                    language TEXT NOT NULL DEFAULT 'am',
                    status TEXT NOT NULL DEFAULT 'Pending_Assignment',
                    assigned_psychiatrist_id INTEGER,
                    created_at TEXT NOT NULL,
                    assigned_at TEXT,
                    FOREIGN KEY (assigned_psychiatrist_id) REFERENCES psychiatrists(psychiatrist_id)
                );
                """
            )

            # 4. Messages Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    psychiatrist_id INTEGER,
                    sender_type TEXT NOT NULL,
                    text TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    telegram_message_id INTEGER,
                    edited_at TEXT,
                    deleted_at TEXT,
                    deleted_for_psychiatrist INTEGER NOT NULL DEFAULT 0,
                    deleted_for_psychiatrist_at TEXT,
                    FOREIGN KEY (telegram_id) REFERENCES patients(telegram_id),
                    FOREIGN KEY (psychiatrist_id) REFERENCES psychiatrists(psychiatrist_id)
                );
                """
            )

            # 5. Patient Notes Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS patient_notes (
                    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    psychiatrist_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (patient_id) REFERENCES patients(telegram_id),
                    FOREIGN KEY (psychiatrist_id) REFERENCES psychiatrists(psychiatrist_id)
                );
                """
            )

            # Indexes for instant lookups
            conn.execute("CREATE INDEX IF NOT EXISTS idx_patients_status ON patients(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_patients_assigned ON patients(assigned_psychiatrist_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(telegram_id, psychiatrist_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_patient_psych ON patient_notes(patient_id, psychiatrist_id);")

            conn.commit()
        finally:
            conn.close()

    # Automatically import any existing JSON data into SQLite
    _migrate_json_data()


def _migrate_json_data() -> None:
    """Migrates existing JSON files into fulldb.db if tables are empty."""
    with _DB_LOCK:
        with transaction() as conn:
            # Migrate psychiatrists
            cur = conn.execute("SELECT COUNT(*) FROM psychiatrists;")
            if cur.fetchone()[0] == 0:
                psych_file = DATA_DIR / "psychiatrists.json"
                if psych_file.exists():
                    try:
                        psych_data = json.loads(psych_file.read_text(encoding="utf-8"))
                        for item in psych_data:
                            conn.execute(
                                """
                                INSERT INTO psychiatrists (
                                    psychiatrist_id, username, full_name, email, field, status,
                                    max_patients, password_hash, must_change_password, created_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                                """,
                                (
                                    item.get("psychiatrist_id"),
                                    item.get("username"),
                                    item.get("full_name"),
                                    item.get("email", item.get("username")),
                                    item.get("field", "Psychiatry"),
                                    item.get("status", "Active"),
                                    item.get("max_patients", 5),
                                    item.get("password_hash"),
                                    1 if item.get("must_change_password") else 0,
                                    datetime.now(timezone.utc).isoformat(),
                                ),
                            )
                        logger.info("Migrated psychiatrists from JSON to SQLite.")
                    except Exception as exc:
                        logger.warning("Could not migrate psychiatrists.json: %s", exc)

            # Migrate patients
            cur = conn.execute("SELECT COUNT(*) FROM patients;")
            if cur.fetchone()[0] == 0:
                patients_file = DATA_DIR / "patients.json"
                if patients_file.exists():
                    try:
                        patients_data = json.loads(patients_file.read_text(encoding="utf-8"))
                        for item in patients_data:
                            if not item.get("telegram_id"):
                                continue
                            conn.execute(
                                """
                                INSERT INTO patients (
                                    telegram_id, telegram_username, name, age, complaint,
                                    language, status, assigned_psychiatrist_id, created_at, assigned_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                                """,
                                (
                                    item.get("telegram_id"),
                                    item.get("telegram_username", item.get("username", "")),
                                    item.get("name", "Unknown"),
                                    item.get("age"),
                                    item.get("complaint", ""),
                                    item.get("language", "am"),
                                    item.get("status", "Pending_Assignment"),
                                    item.get("assigned_psychiatrist_id"),
                                    item.get("created_at", datetime.now(timezone.utc).isoformat()),
                                    item.get("assigned_at"),
                                ),
                            )
                        logger.info("Migrated patients from JSON to SQLite.")
                    except Exception as exc:
                        logger.warning("Could not migrate patients.json: %s", exc)

            # Migrate messages
            cur = conn.execute("SELECT COUNT(*) FROM messages;")
            if cur.fetchone()[0] == 0:
                messages_file = DATA_DIR / "messages.json"
                if messages_file.exists():
                    try:
                        messages_data = json.loads(messages_file.read_text(encoding="utf-8"))
                        for item in messages_data:
                            conn.execute(
                                """
                                INSERT INTO messages (
                                    message_id, telegram_id, psychiatrist_id, sender_type, text,
                                    timestamp, telegram_message_id, edited_at, deleted_at,
                                    deleted_for_psychiatrist, deleted_for_psychiatrist_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                                """,
                                (
                                    item.get("message_id"),
                                    item.get("telegram_id"),
                                    item.get("psychiatrist_id"),
                                    item.get("sender_type"),
                                    item.get("text", ""),
                                    item.get("timestamp", datetime.now(timezone.utc).isoformat()),
                                    item.get("telegram_message_id"),
                                    item.get("edited_at"),
                                    item.get("deleted_at"),
                                    1 if item.get("deleted_for_psychiatrist") else 0,
                                    item.get("deleted_for_psychiatrist_at"),
                                ),
                            )
                        logger.info("Migrated messages from JSON to SQLite.")
                    except Exception as exc:
                        logger.warning("Could not migrate messages.json: %s", exc)

            # Migrate patient notes
            cur = conn.execute("SELECT COUNT(*) FROM patient_notes;")
            if cur.fetchone()[0] == 0:
                notes_file = DATA_DIR / "patient_notes.json"
                if notes_file.exists():
                    try:
                        notes_data = json.loads(notes_file.read_text(encoding="utf-8"))
                        for item in notes_data:
                            conn.execute(
                                """
                                INSERT INTO patient_notes (
                                    note_id, patient_id, psychiatrist_id, text, created_at, updated_at
                                ) VALUES (?, ?, ?, ?, ?, ?);
                                """,
                                (
                                    item.get("note_id"),
                                    item.get("patient_id"),
                                    item.get("psychiatrist_id"),
                                    item.get("text", ""),
                                    item.get("created_at", datetime.now(timezone.utc).isoformat()),
                                    item.get("updated_at", datetime.now(timezone.utc).isoformat()),
                                ),
                            )
                        logger.info("Migrated patient notes from JSON to SQLite.")
                    except Exception as exc:
                        logger.warning("Could not migrate patient_notes.json: %s", exc)


# ============================================================================
# PATIENTS REPOSITORY
# ============================================================================

def _patient_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "telegram_id": row["telegram_id"],
        "telegram_username": row["telegram_username"] or "",
        "name": row["name"],
        "age": row["age"],
        "complaint": row["complaint"] or "",
        "language": row["language"] or "am",
        "status": row["status"],
        "assigned_psychiatrist_id": row["assigned_psychiatrist_id"],
        "created_at": row["created_at"],
        "assigned_at": row["assigned_at"],
    }


def get_patient(telegram_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM patients WHERE telegram_id = ?;", (telegram_id,))
        row = cur.fetchone()
        return _patient_from_row(row) if row else None


def get_patients(
    status: str | None = None,
    assigned_psychiatrist_id: int | None = None,
) -> list[dict[str, Any]]:
    query = "SELECT * FROM patients WHERE 1=1"
    params: list[Any] = []
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    if assigned_psychiatrist_id is not None:
        query += " AND assigned_psychiatrist_id = ?"
        params.append(assigned_psychiatrist_id)
    query += " ORDER BY created_at DESC;"

    with get_connection() as conn:
        cur = conn.execute(query, params)
        return [_patient_from_row(row) for row in cur.fetchall()]


def upsert_patient(data: dict[str, Any]) -> dict[str, Any]:
    telegram_id = data["telegram_id"]
    with transaction() as conn:
        cur = conn.execute("SELECT * FROM patients WHERE telegram_id = ?;", (telegram_id,))
        existing = cur.fetchone()

        telegram_username = data.get("telegram_username", data.get("username", "")) or ""
        name = data.get("name", "Unknown")
        age = data.get("age")
        complaint = data.get("complaint", "")
        language = data.get("language", "am")
        status = data.get("status", "Pending_Assignment")
        assigned_psychiatrist_id = data.get("assigned_psychiatrist_id")
        created_at = data.get("created_at", datetime.now(timezone.utc).isoformat())
        assigned_at = data.get("assigned_at")

        if existing:
            conn.execute(
                """
                UPDATE patients SET
                    telegram_username = ?,
                    name = ?,
                    age = ?,
                    complaint = ?,
                    language = ?,
                    status = ?,
                    assigned_psychiatrist_id = ?,
                    assigned_at = ?
                WHERE telegram_id = ?;
                """,
                (
                    telegram_username,
                    name,
                    age,
                    complaint,
                    language,
                    status,
                    assigned_psychiatrist_id,
                    assigned_at,
                    telegram_id,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO patients (
                    telegram_id, telegram_username, name, age, complaint,
                    language, status, assigned_psychiatrist_id, created_at, assigned_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    telegram_id,
                    telegram_username,
                    name,
                    age,
                    complaint,
                    language,
                    status,
                    assigned_psychiatrist_id,
                    created_at,
                    assigned_at,
                ),
            )

        cur = conn.execute("SELECT * FROM patients WHERE telegram_id = ?;", (telegram_id,))
        return _patient_from_row(cur.fetchone())


def update_patient_language(telegram_id: int, language: str) -> None:
    with transaction() as conn:
        conn.execute("UPDATE patients SET language = ? WHERE telegram_id = ?;", (language, telegram_id))


def assign_patient(telegram_id: int, psychiatrist_id: int) -> dict[str, Any]:
    assigned_at = datetime.now(timezone.utc).isoformat()
    with transaction() as conn:
        conn.execute(
            """
            UPDATE patients SET
                assigned_psychiatrist_id = ?,
                status = 'Active',
                assigned_at = ?
            WHERE telegram_id = ?;
            """,
            (psychiatrist_id, assigned_at, telegram_id),
        )
        conn.execute("UPDATE psychiatrists SET status = 'Active' WHERE psychiatrist_id = ?;", (psychiatrist_id,))
        cur = conn.execute("SELECT * FROM patients WHERE telegram_id = ?;", (telegram_id,))
        return _patient_from_row(cur.fetchone())


# ============================================================================
# PSYCHIATRISTS REPOSITORY
# ============================================================================

def _psychiatrist_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "psychiatrist_id": row["psychiatrist_id"],
        "username": row["username"],
        "email": row["email"] or row["username"],
        "full_name": row["full_name"],
        "field": row["field"],
        "status": row["status"],
        "max_patients": row["max_patients"],
        "password_hash": row["password_hash"],
        "must_change_password": bool(row["must_change_password"]),
        "created_at": row["created_at"],
    }


def get_psychiatrists() -> list[dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM psychiatrists ORDER BY psychiatrist_id ASC;")
        return [_psychiatrist_from_row(row) for row in cur.fetchall()]


def get_psychiatrist(psychiatrist_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM psychiatrists WHERE psychiatrist_id = ?;", (psychiatrist_id,))
        row = cur.fetchone()
        return _psychiatrist_from_row(row) if row else None


def get_psychiatrist_by_username(username: str) -> dict[str, Any] | None:
    norm = username.strip().casefold()
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM psychiatrists WHERE lower(username) = ? OR lower(email) = ?;",
            (norm, norm),
        )
        row = cur.fetchone()
        return _psychiatrist_from_row(row) if row else None


def create_psychiatrist(data: dict[str, Any]) -> dict[str, Any]:
    with transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO psychiatrists (
                username, full_name, email, field, status, max_patients,
                password_hash, must_change_password, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                data["username"],
                data["full_name"],
                data.get("email", data["username"]),
                data["field"],
                data.get("status", "Active"),
                data.get("max_patients", 5),
                data.get("password_hash"),
                1 if data.get("must_change_password") else 0,
                data.get("created_at", datetime.now(timezone.utc).isoformat()),
            ),
        )
        new_id = cur.lastrowid
        cur = conn.execute("SELECT * FROM psychiatrists WHERE psychiatrist_id = ?;", (new_id,))
        return _psychiatrist_from_row(cur.fetchone())


def update_psychiatrist_capacity(psychiatrist_id: int, max_patients: int) -> dict[str, Any] | None:
    with transaction() as conn:
        conn.execute(
            "UPDATE psychiatrists SET max_patients = ? WHERE psychiatrist_id = ?;",
            (max_patients, psychiatrist_id),
        )
        cur = conn.execute("SELECT * FROM psychiatrists WHERE psychiatrist_id = ?;", (psychiatrist_id,))
        row = cur.fetchone()
        return _psychiatrist_from_row(row) if row else None


def update_psychiatrist_password(psychiatrist_id: int, password_hash: str) -> None:
    with transaction() as conn:
        conn.execute(
            "UPDATE psychiatrists SET password_hash = ?, must_change_password = 0 WHERE psychiatrist_id = ?;",
            (password_hash, psychiatrist_id),
        )


# ============================================================================
# MESSAGES REPOSITORY
# ============================================================================

def _message_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "message_id": row["message_id"],
        "telegram_id": row["telegram_id"],
        "psychiatrist_id": row["psychiatrist_id"],
        "sender_type": row["sender_type"],
        "text": row["text"],
        "timestamp": row["timestamp"],
        "telegram_message_id": row["telegram_message_id"],
        "edited_at": row["edited_at"],
        "deleted_at": row["deleted_at"],
        "deleted_for_psychiatrist": bool(row["deleted_for_psychiatrist"]),
        "deleted_for_psychiatrist_at": row["deleted_for_psychiatrist_at"],
    }


def get_chat_messages(telegram_id: int, psychiatrist_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT * FROM messages
            WHERE telegram_id = ?
              AND psychiatrist_id = ?
              AND deleted_at IS NULL
              AND deleted_for_psychiatrist = 0
            ORDER BY timestamp ASC;
            """,
            (telegram_id, psychiatrist_id),
        )
        return [_message_from_row(row) for row in cur.fetchall()]


get_messages = get_chat_messages


def get_message(message_id: int, telegram_id: int, psychiatrist_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT * FROM messages
            WHERE message_id = ? AND telegram_id = ? AND psychiatrist_id = ?;
            """,
            (message_id, telegram_id, psychiatrist_id),
        )
        row = cur.fetchone()
        return _message_from_row(row) if row else None


def add_message(data: dict[str, Any]) -> dict[str, Any]:
    with transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO messages (
                telegram_id, psychiatrist_id, sender_type, text, timestamp,
                telegram_message_id, edited_at, deleted_at, deleted_for_psychiatrist
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                data["telegram_id"],
                data.get("psychiatrist_id"),
                data["sender_type"],
                data["text"],
                data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                data.get("telegram_message_id"),
                data.get("edited_at"),
                data.get("deleted_at"),
                1 if data.get("deleted_for_psychiatrist") else 0,
            ),
        )
        new_id = cur.lastrowid
        cur = conn.execute("SELECT * FROM messages WHERE message_id = ?;", (new_id,))
        return _message_from_row(cur.fetchone())


def edit_message(message_id: int, telegram_id: int, psychiatrist_id: int, new_text: str) -> dict[str, Any] | None:
    edited_at = datetime.now(timezone.utc).isoformat()
    with transaction() as conn:
        conn.execute(
            """
            UPDATE messages SET text = ?, edited_at = ?
            WHERE message_id = ? AND telegram_id = ? AND psychiatrist_id = ?;
            """,
            (new_text, edited_at, message_id, telegram_id, psychiatrist_id),
        )
        cur = conn.execute("SELECT * FROM messages WHERE message_id = ?;", (message_id,))
        row = cur.fetchone()
        return _message_from_row(row) if row else None


def delete_message(message_id: int, telegram_id: int, psychiatrist_id: int, scope: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with transaction() as conn:
        if scope == "everyone":
            conn.execute(
                """
                UPDATE messages SET deleted_at = ?, text = ''
                WHERE message_id = ? AND telegram_id = ? AND psychiatrist_id = ?;
                """,
                (now, message_id, telegram_id, psychiatrist_id),
            )
        else:
            conn.execute(
                """
                UPDATE messages SET deleted_for_psychiatrist = 1, deleted_for_psychiatrist_at = ?
                WHERE message_id = ? AND telegram_id = ? AND psychiatrist_id = ?;
                """,
                (now, message_id, telegram_id, psychiatrist_id),
            )


def get_interaction_logs() -> list[dict[str, Any]]:
    with get_connection() as conn:
        # High-efficiency SQL aggregate grouping
        cur = conn.execute(
            """
            SELECT
                m.telegram_id,
                COALESCE(p.name, 'Unknown patient') as patient_name,
                m.psychiatrist_id,
                COALESCE(psy.full_name, 'Unknown psychiatrist') as psychiatrist_name,
                COUNT(*) as message_count,
                SUM(CASE WHEN m.sender_type = 'patient' THEN 1 ELSE 0 END) as patient_message_count,
                SUM(CASE WHEN m.sender_type = 'psychiatrist' THEN 1 ELSE 0 END) as psychiatrist_message_count,
                MAX(m.timestamp) as last_message_at
            FROM messages m
            LEFT JOIN patients p ON m.telegram_id = p.telegram_id
            LEFT JOIN psychiatrists psy ON m.psychiatrist_id = psy.psychiatrist_id
            WHERE m.psychiatrist_id IS NOT NULL
            GROUP BY m.telegram_id, m.psychiatrist_id
            ORDER BY last_message_at DESC;
            """
        )
        return [
            {
                "telegram_id": row["telegram_id"],
                "patient_name": row["patient_name"],
                "psychiatrist_id": row["psychiatrist_id"],
                "psychiatrist_name": row["psychiatrist_name"],
                "message_count": row["message_count"],
                "patient_message_count": row["patient_message_count"],
                "psychiatrist_message_count": row["psychiatrist_message_count"],
                "last_message_at": row["last_message_at"],
            }
            for row in cur.fetchall()
        ]


# ============================================================================
# PATIENT NOTES REPOSITORY
# ============================================================================

def _note_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "note_id": row["note_id"],
        "patient_id": row["patient_id"],
        "psychiatrist_id": row["psychiatrist_id"],
        "text": row["text"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_patient_notes(patient_id: int, psychiatrist_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT * FROM patient_notes
            WHERE patient_id = ? AND psychiatrist_id = ?
            ORDER BY updated_at DESC;
            """,
            (patient_id, psychiatrist_id),
        )
        return [_note_from_row(row) for row in cur.fetchall()]


def create_patient_note(patient_id: int, psychiatrist_id: int, text: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    with transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO patient_notes (patient_id, psychiatrist_id, text, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?);
            """,
            (patient_id, psychiatrist_id, text, now, now),
        )
        new_id = cur.lastrowid
        cur = conn.execute("SELECT * FROM patient_notes WHERE note_id = ?;", (new_id,))
        return _note_from_row(cur.fetchone())


def update_patient_note(note_id: int, patient_id: int, psychiatrist_id: int, text: str) -> dict[str, Any] | None:
    now = datetime.now(timezone.utc).isoformat()
    with transaction() as conn:
        conn.execute(
            """
            UPDATE patient_notes SET text = ?, updated_at = ?
            WHERE note_id = ? AND patient_id = ? AND psychiatrist_id = ?;
            """,
            (text, now, note_id, patient_id, psychiatrist_id),
        )
        cur = conn.execute("SELECT * FROM patient_notes WHERE note_id = ?;", (note_id,))
        row = cur.fetchone()
        return _note_from_row(row) if row else None


def delete_patient_note(note_id: int, patient_id: int, psychiatrist_id: int) -> bool:
    with transaction() as conn:
        cur = conn.execute(
            "DELETE FROM patient_notes WHERE note_id = ? AND patient_id = ? AND psychiatrist_id = ?;",
            (note_id, patient_id, psychiatrist_id),
        )
        return cur.rowcount > 0


# ============================================================================
# BACKWARD COMPATIBILITY LAYER (Seamlessly routes JSON calls to SQLite)
# ============================================================================

def read_json(filename: str) -> list[dict[str, Any]]:
    """Backward-compatible read_json that queries live SQLite tables."""
    name = Path(filename).name
    if name == "patients.json":
        return get_patients()
    elif name == "psychiatrists.json":
        return get_psychiatrists()
    elif name == "messages.json":
        with get_connection() as conn:
            cur = conn.execute("SELECT * FROM messages ORDER BY timestamp ASC;")
            return [_message_from_row(row) for row in cur.fetchall()]
    elif name == "patient_notes.json":
        with get_connection() as conn:
            cur = conn.execute("SELECT * FROM patient_notes ORDER BY updated_at DESC;")
            return [_note_from_row(row) for row in cur.fetchall()]
    return []


def write_json(filename: str, records: list[dict[str, Any]]) -> None:
    """Backward-compatible write_json that syncs records into SQLite."""
    name = Path(filename).name
    if name == "patients.json":
        for rec in records:
            if rec.get("telegram_id"):
                upsert_patient(rec)
    elif name == "psychiatrists.json":
        for rec in records:
            if rec.get("psychiatrist_id"):
                existing = get_psychiatrist(rec["psychiatrist_id"])
                if not existing:
                    create_psychiatrist(rec)
                else:
                    with transaction() as conn:
                        conn.execute(
                            """
                            UPDATE psychiatrists SET
                                username = ?, full_name = ?, email = ?, field = ?,
                                status = ?, max_patients = ?, password_hash = ?,
                                must_change_password = ?
                            WHERE psychiatrist_id = ?;
                            """,
                            (
                                rec["username"],
                                rec["full_name"],
                                rec.get("email", rec["username"]),
                                rec["field"],
                                rec.get("status", "Active"),
                                rec.get("max_patients", 5),
                                rec.get("password_hash"),
                                1 if rec.get("must_change_password") else 0,
                                rec["psychiatrist_id"],
                            ),
                        )
    elif name == "messages.json":
        for rec in records:
            if rec.get("message_id"):
                with transaction() as conn:
                    cur = conn.execute("SELECT 1 FROM messages WHERE message_id = ?;", (rec["message_id"],))
                    if not cur.fetchone():
                        conn.execute(
                            """
                            INSERT INTO messages (
                                message_id, telegram_id, psychiatrist_id, sender_type, text,
                                timestamp, telegram_message_id, edited_at, deleted_at,
                                deleted_for_psychiatrist, deleted_for_psychiatrist_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                            """,
                            (
                                rec["message_id"],
                                rec["telegram_id"],
                                rec.get("psychiatrist_id"),
                                rec["sender_type"],
                                rec.get("text", ""),
                                rec.get("timestamp", datetime.now(timezone.utc).isoformat()),
                                rec.get("telegram_message_id"),
                                rec.get("edited_at"),
                                rec.get("deleted_at"),
                                1 if rec.get("deleted_for_psychiatrist") else 0,
                                rec.get("deleted_for_psychiatrist_at"),
                            ),
                        )
    elif name == "patient_notes.json":
        for rec in records:
            if rec.get("note_id"):
                with transaction() as conn:
                    cur = conn.execute("SELECT 1 FROM patient_notes WHERE note_id = ?;", (rec["note_id"],))
                    if not cur.fetchone():
                        conn.execute(
                            """
                            INSERT INTO patient_notes (note_id, patient_id, psychiatrist_id, text, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?);
                            """,
                            (
                                rec["note_id"],
                                rec["patient_id"],
                                rec["psychiatrist_id"],
                                rec.get("text", ""),
                                rec.get("created_at", datetime.now(timezone.utc).isoformat()),
                                rec.get("updated_at", datetime.now(timezone.utc).isoformat()),
                            ),
                        )
