"""
database.py  —  SQLite setup for Vebita
Single file: vebita.db lives in the backend/ folder.
"""

import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "vebita.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS datasets (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            filename      TEXT    NOT NULL,
            original_name TEXT    NOT NULL,
            species       TEXT    DEFAULT 'Unknown',
            n_fixes       INTEGER DEFAULT 0,
            file_size_kb  REAL    DEFAULT 0,
            uploaded_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS results (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id     INTEGER NOT NULL REFERENCES datasets(id),
            service_id     INTEGER NOT NULL,
            service_name   TEXT    NOT NULL,
            algo_a         TEXT    NOT NULL,
            algo_b         TEXT    NOT NULL,
            f1_a           REAL,
            f1_b           REAL,
            accuracy_a     REAL,
            accuracy_b     REAL,
            precision_a    REAL,
            precision_b    REAL,
            recall_a       REAL,
            recall_b       REAL,
            runtime_a      REAL,
            runtime_b      REAL,
            n_train        INTEGER,
            n_test         INTEGER,
            n_classes      INTEGER,
            label_names    TEXT,
            predictions_a  TEXT,
            predictions_b  TEXT,
            per_class_f1_a TEXT,
            per_class_f1_b TEXT,
            error_a        TEXT,
            error_b        TEXT,
            run_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()