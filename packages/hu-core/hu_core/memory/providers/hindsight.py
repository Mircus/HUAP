"""
Hindsight Memory Provider (SQLite)

Persistent memory backend using SQLite for cross-session knowledge retention.
Implements the full MemoryProvider interface with real persistence.

SQLite is stdlib (zero extra dependencies) and works everywhere.
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import (
    MemoryProvider,
    MemoryEntry,
    MemoryQuery,
    MemoryType,
    MemoryStatus,
)

logger = logging.getLogger("huap.memory.hindsight")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS memory_entries (
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    memory_type TEXT NOT NULL DEFAULT 'fact',
    status TEXT NOT NULL DEFAULT 'active',
    namespace TEXT NOT NULL DEFAULT 'default',
    user_id TEXT NOT NULL DEFAULT '',
    pod_name TEXT NOT NULL DEFAULT '',
    run_id TEXT,
    correlation_id TEXT,
    created_at TEXT,
    updated_at TEXT,
    expires_at TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    metadata TEXT NOT NULL DEFAULT '{}',
    related_entry_id TEXT,
    is_closed INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (key, namespace, user_id, pod_name)
);
"""

_CREATE_INDEX_RUN = """
CREATE INDEX IF NOT EXISTS idx_memory_run_id ON memory_entries (run_id);
"""

_CREATE_INDEX_TYPE = """
CREATE INDEX IF NOT EXISTS idx_memory_type ON memory_entries (memory_type, namespace);
"""


def _entry_to_row(entry: MemoryEntry) -> Dict[str, Any]:
    """Convert a MemoryEntry to a dict suitable for SQLite INSERT."""
    return {
        "key": entry.key,
        "value": json.dumps(entry.value),
        "memory_type": entry.memory_type.value if isinstance(entry.memory_type, MemoryType) else entry.memory_type,
        "status": entry.status.value if isinstance(entry.status, MemoryStatus) else entry.status,
        "namespace": entry.namespace or "default",
        "user_id": entry.user_id or "",
        "pod_name": entry.pod_name or "",
        "run_id": entry.run_id,
        "correlation_id": entry.correlation_id,
        "created_at": entry.created_at.isoformat() if isinstance(entry.created_at, datetime) else str(entry.created_at) if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if isinstance(entry.updated_at, datetime) else str(entry.updated_at) if entry.updated_at else None,
        "expires_at": entry.expires_at.isoformat() if isinstance(entry.expires_at, datetime) else str(entry.expires_at) if entry.expires_at else None,
        "tags": json.dumps(list(entry.tags)) if entry.tags else "[]",
        "metadata": json.dumps(entry.metadata) if entry.metadata else "{}",
        "related_entry_id": entry.related_entry_id,
        "is_closed": 1 if entry.is_closed else 0,
    }


def _row_to_entry(row: sqlite3.Row) -> MemoryEntry:
    """Convert a SQLite row to a MemoryEntry."""
    created_at = datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.utcnow()
    updated_at = datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None
    expires_at = datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None

    return MemoryEntry(
        key=row["key"],
        value=json.loads(row["value"]),
        memory_type=MemoryType(row["memory_type"]),
        status=MemoryStatus(row["status"]),
        namespace=row["namespace"],
        user_id=row["user_id"] or None,
        pod_name=row["pod_name"] or None,
        run_id=row["run_id"],
        correlation_id=row["correlation_id"],
        created_at=created_at,
        updated_at=updated_at,
        expires_at=expires_at,
        tags=set(json.loads(row["tags"])) if row["tags"] else set(),
        metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        related_entry_id=row["related_entry_id"],
        is_closed=bool(row["is_closed"]),
    )


class HindsightProvider(MemoryProvider):
    """
    SQLite-backed memory provider for persistent cross-session knowledge.

    Provides:
    - Full CRUD via get/set/delete/query/list_keys
    - Keyword-based search (search_semantic)
    - Episode retrieval by run_id (get_episode)
    - Reflection summaries by type counts (reflect)
    - Period summaries with date filtering (summarize_period)
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the Hindsight provider.

        Args:
            db_path: Path to SQLite database file.
                     Defaults to '.huap/memory.db' in cwd.
        """
        self._db_path = db_path or str(Path.cwd() / ".huap" / "memory.db")
        self._conn: Optional[sqlite3.Connection] = None

    async def connect(self) -> bool:
        """
        Open (or create) the SQLite database and ensure tables exist.

        Returns:
            True on success
        """
        try:
            db_dir = Path(self._db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute(_CREATE_TABLE)
            self._conn.execute(_CREATE_INDEX_RUN)
            self._conn.execute(_CREATE_INDEX_TYPE)
            self._conn.commit()
            logger.info("Hindsight connected to %s", self._db_path)
            return True
        except Exception:
            logger.exception("Failed to connect to Hindsight DB at %s", self._db_path)
            return False

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _ensure_connected(self):
        if self._conn is None:
            raise RuntimeError("HindsightProvider is not connected. Call connect() first.")

    # =========================================================================
    # CORE CRUD (MemoryProvider interface)
    # =========================================================================

    async def get(
        self,
        key: str,
        *,
        user_id: Optional[str] = None,
        pod_name: Optional[str] = None,
        namespace: str = "default",
    ) -> Optional[MemoryEntry]:
        """Get a single memory entry by key."""
        self._ensure_connected()
        cur = self._conn.execute(
            "SELECT * FROM memory_entries WHERE key=? AND namespace=? AND user_id=? AND pod_name=?",
            (key, namespace, user_id or "", pod_name or ""),
        )
        row = cur.fetchone()
        return _row_to_entry(row) if row else None

    async def set(self, entry: MemoryEntry) -> MemoryEntry:
        """Store a memory entry (insert or replace)."""
        self._ensure_connected()
        if entry.updated_at is None:
            entry.updated_at = datetime.utcnow()
        row = _entry_to_row(entry)
        cols = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        self._conn.execute(
            f"INSERT OR REPLACE INTO memory_entries ({cols}) VALUES ({placeholders})",
            list(row.values()),
        )
        self._conn.commit()
        return entry

    async def delete(
        self,
        key: str,
        *,
        user_id: Optional[str] = None,
        pod_name: Optional[str] = None,
        namespace: str = "default",
    ) -> bool:
        """Delete a memory entry. Returns True if a row was deleted."""
        self._ensure_connected()
        cur = self._conn.execute(
            "DELETE FROM memory_entries WHERE key=? AND namespace=? AND user_id=? AND pod_name=?",
            (key, namespace, user_id or "", pod_name or ""),
        )
        self._conn.commit()
        return cur.rowcount > 0

    async def query(self, query: MemoryQuery) -> List[MemoryEntry]:
        """Query memory entries with filters."""
        self._ensure_connected()
        clauses = []
        params: list = []

        if query.user_id is not None:
            clauses.append("user_id = ?")
            params.append(query.user_id)
        if query.pod_name is not None:
            clauses.append("pod_name = ?")
            params.append(query.pod_name)
        if query.namespace is not None:
            clauses.append("namespace = ?")
            params.append(query.namespace)
        if query.memory_type is not None:
            val = query.memory_type.value if isinstance(query.memory_type, MemoryType) else query.memory_type
            clauses.append("memory_type = ?")
            params.append(val)
        if query.status is not None:
            val = query.status.value if isinstance(query.status, MemoryStatus) else query.status
            clauses.append("status = ?")
            params.append(val)
        if query.run_id is not None:
            clauses.append("run_id = ?")
            params.append(query.run_id)
        if query.correlation_id is not None:
            clauses.append("correlation_id = ?")
            params.append(query.correlation_id)
        if query.key_prefix is not None:
            clauses.append("key LIKE ?")
            params.append(query.key_prefix + "%")
        if query.tags:
            for tag in query.tags:
                clauses.append("tags LIKE ?")
                params.append(f'%"{tag}"%')
        if not query.include_expired:
            clauses.append("(expires_at IS NULL OR expires_at > ?)")
            params.append(datetime.utcnow().isoformat())

        where = " AND ".join(clauses) if clauses else "1=1"
        sql = f"SELECT * FROM memory_entries WHERE {where} ORDER BY created_at DESC, key ASC LIMIT ? OFFSET ?"
        params.extend([query.limit, query.offset])

        cur = self._conn.execute(sql, params)
        return [_row_to_entry(row) for row in cur.fetchall()]

    async def list_keys(
        self,
        *,
        user_id: Optional[str] = None,
        pod_name: Optional[str] = None,
        namespace: str = "default",
    ) -> List[str]:
        """List all keys in a namespace."""
        self._ensure_connected()
        cur = self._conn.execute(
            "SELECT DISTINCT key FROM memory_entries WHERE namespace=? AND user_id=? AND pod_name=?",
            (namespace, user_id or "", pod_name or ""),
        )
        return [row["key"] for row in cur.fetchall()]

    # =========================================================================
    # HINDSIGHT-SPECIFIC METHODS
    # =========================================================================

    async def reflect(
        self,
        *,
        user_id: str,
        pod_name: Optional[str] = None,
        topic: Optional[str] = None,
        depth: int = 1,
    ) -> Dict[str, Any]:
        """
        Reflect on stored memories — returns summary counts by type.

        Args:
            user_id: User to reflect on
            pod_name: Optional pod filter
            topic: Optional keyword to focus on
            depth: 1=shallow counts, 2+=include recent entries
        """
        self._ensure_connected()
        clauses = ["user_id = ?"]
        params: list = [user_id]
        if pod_name:
            clauses.append("pod_name = ?")
            params.append(pod_name)
        if topic:
            clauses.append("(key LIKE ? OR value LIKE ?)")
            params.extend([f"%{topic}%", f"%{topic}%"])

        where = " AND ".join(clauses)

        # Count by type
        cur = self._conn.execute(
            f"SELECT memory_type, COUNT(*) as cnt FROM memory_entries WHERE {where} GROUP BY memory_type",
            params,
        )
        type_counts = {row["memory_type"]: row["cnt"] for row in cur.fetchall()}
        total = sum(type_counts.values())

        result: Dict[str, Any] = {
            "status": "ok",
            "total_entries": total,
            "by_type": type_counts,
        }

        # Depth >= 2: include recent entries
        if depth >= 2:
            cur = self._conn.execute(
                f"SELECT * FROM memory_entries WHERE {where} ORDER BY created_at DESC, key ASC LIMIT 20",
                params,
            )
            result["recent"] = [
                {"key": row["key"], "type": row["memory_type"], "created_at": row["created_at"]}
                for row in cur.fetchall()
            ]

        return result

    async def search_semantic(
        self,
        query: str,
        *,
        user_id: Optional[str] = None,
        pod_name: Optional[str] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """
        Keyword-based search across memory entries.

        Searches key and value fields using LIKE. For vector-based semantic
        search, a future version will integrate embeddings.
        """
        self._ensure_connected()
        clauses = ["(key LIKE ? OR value LIKE ?)"]
        params: list = [f"%{query}%", f"%{query}%"]

        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        if pod_name is not None:
            clauses.append("pod_name = ?")
            params.append(pod_name)

        where = " AND ".join(clauses)
        cur = self._conn.execute(
            f"SELECT * FROM memory_entries WHERE {where} ORDER BY created_at DESC, key ASC LIMIT ?",
            [*params, limit],
        )
        return [_row_to_entry(row) for row in cur.fetchall()]

    async def get_episode(
        self,
        episode_id: str,
        *,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a complete episode (all entries for a given run_id).

        Args:
            episode_id: Episode identifier (usually a run_id)
            user_id: User ID
        """
        self._ensure_connected()
        cur = self._conn.execute(
            "SELECT * FROM memory_entries WHERE run_id = ? AND user_id = ? ORDER BY created_at ASC, key ASC",
            (episode_id, user_id),
        )
        rows = cur.fetchall()
        if not rows:
            return None

        entries = [_row_to_entry(row) for row in rows]
        return {
            "episode_id": episode_id,
            "user_id": user_id,
            "entry_count": len(entries),
            "entries": [e.to_dict() for e in entries],
            "start": entries[0].created_at.isoformat() if entries[0].created_at else None,
            "end": entries[-1].created_at.isoformat() if entries[-1].created_at else None,
        }

    async def summarize_period(
        self,
        *,
        user_id: str,
        pod_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Summarize entries in a time period — counts by type + key list.
        """
        self._ensure_connected()
        clauses = ["user_id = ?"]
        params: list = [user_id]

        if pod_name:
            clauses.append("pod_name = ?")
            params.append(pod_name)
        if start_date:
            clauses.append("created_at >= ?")
            params.append(start_date.isoformat())
        if end_date:
            clauses.append("created_at <= ?")
            params.append(end_date.isoformat())

        where = " AND ".join(clauses)

        # Counts by type
        cur = self._conn.execute(
            f"SELECT memory_type, COUNT(*) as cnt FROM memory_entries WHERE {where} GROUP BY memory_type",
            params,
        )
        type_counts = {row["memory_type"]: row["cnt"] for row in cur.fetchall()}

        # Key list
        cur = self._conn.execute(
            f"SELECT key, memory_type, created_at FROM memory_entries WHERE {where} ORDER BY created_at DESC, key ASC LIMIT 100",
            params,
        )
        entries = [
            {"key": row["key"], "type": row["memory_type"], "created_at": row["created_at"]}
            for row in cur.fetchall()
        ]

        return {
            "status": "ok",
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "total_entries": sum(type_counts.values()),
            "by_type": type_counts,
            "entries": entries,
        }
