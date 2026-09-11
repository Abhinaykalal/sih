"""
AgriSaathi Conversation Memory
================================
Stores per-user conversation history with a sliding window
so the AI has real context across turns (NOT hardcoded responses).

Features:
- Per-user session isolation
- Configurable window length (default: last 12 messages)
- Field context injection per turn
- Persisted to SQLite so memory survives server restarts
- Thread-safe
"""
import json
import sqlite3
import threading
import time
from typing import List, Dict, Any, Optional
from pathlib import Path


DB_PATH = Path(__file__).parent / "conversation_memory.db"
_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_schema():
    with _lock:
        conn = _get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('system','user','assistant')),
                content TEXT NOT NULL,
                context_snapshot TEXT,
                ts REAL NOT NULL DEFAULT (unixepoch('now', 'subsec'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_session ON messages(user_id, session_id, ts)")
        conn.commit()
        conn.close()


_ensure_schema()


class ConversationMemory:
    """
    Thread-safe conversation memory manager.
    
    Usage:
        mem = ConversationMemory(user_id="user-123", session_id="sess-abc")
        mem.add_user_message("My rice leaves are yellowing")
        mem.add_assistant_message("This could be nitrogen deficiency...")
        history = mem.get_window(max_turns=6)
    """

    def __init__(self, user_id: str, session_id: str = "default"):
        self.user_id = user_id
        self.session_id = session_id

    def add_user_message(self, text: str, context: Optional[Dict] = None):
        """Record a user message, optionally with sensor/farm context snapshot."""
        self._insert("user", text, context)

    def add_assistant_message(self, text: str, context: Optional[Dict] = None):
        """Record the AI assistant response."""
        self._insert("assistant", text, context)

    def add_system_message(self, text: str):
        """Record a system-level prompt or instruction."""
        self._insert("system", text, None)

    def _insert(self, role: str, content: str, context: Optional[Dict]):
        ctx_str = json.dumps(context, ensure_ascii=False) if context else None
        with _lock:
            conn = _get_conn()
            conn.execute(
                "INSERT INTO messages(user_id, session_id, role, content, context_snapshot) VALUES (?,?,?,?,?)",
                (self.user_id, self.session_id, role, content, ctx_str)
            )
            conn.commit()
            conn.close()

    def get_window(self, max_turns: int = 12) -> List[Dict[str, str]]:
        """
        Return last N (user + assistant) messages as a list of {role, content} dicts
        suitable for passing to an LLM as a conversation history.
        System messages are always included at the start.
        """
        with _lock:
            conn = _get_conn()
            rows = conn.execute(
                """
                SELECT role, content FROM messages
                WHERE user_id=? AND session_id=?
                ORDER BY ts ASC
                """,
                (self.user_id, self.session_id)
            ).fetchall()
            conn.close()

        all_msgs = [{"role": r, "content": c} for r, c in rows]
        system_msgs = [m for m in all_msgs if m["role"] == "system"]
        conversation_msgs = [m for m in all_msgs if m["role"] != "system"]

        # Keep only the latest `max_turns` exchanges (each turn = user + assistant)
        window = conversation_msgs[-(max_turns * 2):]
        return system_msgs + window

    def get_last_context(self) -> Optional[Dict]:
        """Retrieve the most recent farm context snapshot from memory."""
        with _lock:
            conn = _get_conn()
            row = conn.execute(
                """
                SELECT context_snapshot FROM messages
                WHERE user_id=? AND session_id=? AND context_snapshot IS NOT NULL
                ORDER BY ts DESC LIMIT 1
                """,
                (self.user_id, self.session_id)
            ).fetchone()
            conn.close()
        if row and row[0]:
            return json.loads(row[0])
        return None

    def clear_session(self):
        """Clear conversation history for this session."""
        with _lock:
            conn = _get_conn()
            conn.execute(
                "DELETE FROM messages WHERE user_id=? AND session_id=?",
                (self.user_id, self.session_id)
            )
            conn.commit()
            conn.close()

    def get_session_summary_stats(self) -> Dict[str, Any]:
        """Return basic stats for debugging / admin panel."""
        with _lock:
            conn = _get_conn()
            row = conn.execute(
                """
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN role='user' THEN 1 ELSE 0 END) as user_msgs,
                       SUM(CASE WHEN role='assistant' THEN 1 ELSE 0 END) as ai_msgs,
                       MIN(ts) as first_ts,
                       MAX(ts) as last_ts
                FROM messages WHERE user_id=? AND session_id=?
                """,
                (self.user_id, self.session_id)
            ).fetchone()
            conn.close()
        return {
            "total_messages": row[0],
            "user_messages": row[1],
            "ai_messages": row[2],
            "session_started": row[3],
            "last_activity": row[4]
        }
