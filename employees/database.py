from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().with_name("employees.db")


def get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_schema() -> None:
    """Create required tables and indices if they do not exist."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                salary REAL NOT NULL,
                department_id INTEGER,
                manager_id INTEGER,
                phone TEXT,
                role TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(department_id) REFERENCES departments(id),
                FOREIGN KEY(manager_id) REFERENCES employees(id)
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_departments_name ON departments(name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(status)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_employees_department_id "
            "ON employees(department_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_employees_manager_id "
            "ON employees(manager_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_employees_role ON employees(role)"
        )

