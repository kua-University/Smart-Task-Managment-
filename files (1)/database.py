"""
Database layer — connection, schema initialisation, seeding.
"""

import os
import sqlite3
from datetime import datetime

DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(__file__), "tasks.db"),
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row):
    return dict(row)


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            description TEXT    DEFAULT '',
            status      TEXT    NOT NULL DEFAULT 'Pending',
            priority    TEXT    NOT NULL DEFAULT 'Medium',
            category    TEXT    DEFAULT 'General',
            created_at  TEXT    NOT NULL,
            updated_at  TEXT    NOT NULL
        )
    """)

    # Seed with sample tasks if table is empty
    count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    if count == 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        samples = [
            ("Design REST API endpoints",   "Define all CRUD routes for task management",        "Completed",   "High",   "Backend",  now, now),
            ("Set up SQLite database",       "Create schema with task attributes per ASR",         "Completed",   "High",   "Backend",  now, now),
            ("Build Flask application",      "Implement business logic and routing layer",          "In Progress", "High",   "Backend",  now, now),
            ("Create responsive UI",         "HTML/CSS frontend with filtering and forms",          "In Progress", "High",   "Frontend", now, now),
            ("Add input validation",         "Client-side and server-side checks per ASR-02",       "Pending",     "Medium", "Frontend", now, now),
            ("Write unit tests",             "Decouple business logic for testability",             "Pending",     "Medium", "Testing",  now, now),
            ("Docker containerisation",      "Wrap app in Docker per DevOps perspective",           "Pending",     "Low",    "DevOps",   now, now),
            ("CI/CD with GitHub Actions",    "Automate deploy pipeline per ASR-05",                 "Pending",     "Low",    "DevOps",   now, now),
        ]
        conn.executemany(
            "INSERT INTO tasks (title,description,status,priority,category,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?)",
            samples,
        )
    conn.commit()
    conn.close()
