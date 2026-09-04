import sqlite3
from contextlib import contextmanager

DB_PATH = "payments.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                failure_reason TEXT,
                created_at TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                recovery_attempts INTEGER DEFAULT 0,
                recovered INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        conn.commit()


def insert_payment(customer_name, amount, status, failure_reason, created_at):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO payments (customer_name, amount, status, failure_reason, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (customer_name, amount, status, failure_reason, created_at),
        )
        conn.commit()
        return cur.lastrowid


def get_all_payments():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM payments ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]


def get_failed_payments():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM payments WHERE status = 'failed' AND recovered = 0"
        ).fetchall()
        return [dict(row) for row in rows]


def update_payment(payment_id, **fields):
    if not fields:
        return
    columns = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [payment_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE payments SET {columns} WHERE id = ?", values)
        conn.commit()


def log_action(payment_id, action, details, timestamp):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO audit_log (payment_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
            (payment_id, action, details, timestamp),
        )
        conn.commit()


def get_audit_log():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM audit_log ORDER BY timestamp DESC").fetchall()
        return [dict(row) for row in rows]


def clear_all():
    with get_connection() as conn:
        conn.execute("DELETE FROM payments")
        conn.execute("DELETE FROM audit_log")
        conn.commit()
