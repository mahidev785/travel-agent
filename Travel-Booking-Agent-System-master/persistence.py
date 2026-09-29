"""Checkpointer factory: persists the state of an in-progress run so the
human-approval interrupt() can pause for minutes, hours, or days and
resume exactly where it left off -- even after a process restart.

SQLite for anything you actually run more than once; in-memory only as a
fallback for quick tests where a DB file would be clutter.
"""

from __future__ import annotations

import config


def get_checkpointer():
    try:
        import sqlite3

        from langgraph.checkpoint.sqlite import SqliteSaver

        conn = sqlite3.connect(config.SQLITE_DB_PATH, check_same_thread=False)
        return SqliteSaver(conn)
    except ImportError:
        from langgraph.checkpoint.memory import InMemorySaver

        return InMemorySaver()
