# src/store.py
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import os

DEFAULT_DB_PATH = "data/rev.db"

class Store:
    def __init__(self, db_path: Optional[str] = None):
        path = db_path or os.getenv("REV_DB_PATH", DEFAULT_DB_PATH)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content_type TEXT NOT NULL,
                body TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                url TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                published_at TEXT
            );
            CREATE TABLE IF NOT EXISTS knowledge_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                hash TEXT NOT NULL,
                checked_at TEXT DEFAULT (datetime('now')),
                changed INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                url TEXT,
                summary TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                body_snippet TEXT,
                draft_response TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                submitted INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        self.conn.commit()

    def tables(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        return [r["name"] for r in rows]

    def queue_content(self, title: str, content_type: str, body: str):
        self.conn.execute(
            "INSERT INTO content (title, content_type, body) VALUES (?, ?, ?)",
            (title, content_type, body)
        )
        self.conn.commit()

    def get_pending_content(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM content WHERE status = 'pending' ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]

    def mark_published(self, content_id: int, url: str):
        self.conn.execute(
            "UPDATE content SET status='published', url=?, published_at=datetime('now') WHERE id=?",
            (url, content_id)
        )
        self.conn.commit()

    def log_interaction(self, platform: str, url: str, summary: str):
        self.conn.execute(
            "INSERT INTO interactions (platform, url, summary) VALUES (?, ?, ?)",
            (platform, url, summary)
        )
        self.conn.commit()

    def interaction_count_this_week(self) -> int:
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM interactions WHERE created_at > ?",
            (week_ago,)
        ).fetchone()
        return row["cnt"]

    def add_feedback(self, title: str, body: str):
        self.conn.execute(
            "INSERT INTO feedback (title, body) VALUES (?, ?)",
            (title, body)
        )
        self.conn.commit()

    def mark_feedback_submitted(self, feedback_id: int):
        self.conn.execute(
            "UPDATE feedback SET submitted=1 WHERE id=?",
            (feedback_id,)
        )
        self.conn.commit()

    def get_feedback(self, submitted: bool = False) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM feedback WHERE submitted = ? ORDER BY created_at",
            (1 if submitted else 0,)
        ).fetchall()
        return [dict(r) for r in rows]

    def record_knowledge_check(self, source: str, hash_val: str, changed: bool):
        self.conn.execute(
            "INSERT INTO knowledge_versions (source, hash, changed) VALUES (?, ?, ?)",
            (source, hash_val, 1 if changed else 0)
        )
        self.conn.commit()

    def save_draft(self, platform: str, url: str, title: str, body_snippet: str, draft_response: str):
        """Save a draft response. Skips if URL already exists."""
        try:
            self.conn.execute(
                "INSERT OR IGNORE INTO drafts (platform, url, title, body_snippet, draft_response) VALUES (?, ?, ?, ?, ?)",
                (platform, url, title, body_snippet, draft_response)
            )
            self.conn.commit()
        except Exception:
            pass

    def get_pending_drafts(self, platform: str = None) -> list[dict]:
        if platform:
            rows = self.conn.execute(
                "SELECT * FROM drafts WHERE status = 'pending' AND platform = ? ORDER BY created_at DESC",
                (platform,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM drafts WHERE status = 'pending' ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_draft(self, draft_id: int, status: str):
        self.conn.execute(
            "UPDATE drafts SET status = ? WHERE id = ?",
            (status, draft_id)
        )
        self.conn.commit()

    def get_published_content(self, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM content WHERE status='published' ORDER BY published_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
