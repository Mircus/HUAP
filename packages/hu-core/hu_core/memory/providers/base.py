"""
Base Memory Provider Interface

Defines the abstract interface that all memory providers must implement.
This allows for pluggable memory backends (database, Hindsight, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class MemoryType(str, Enum):
    """Types of memory entries."""
    FACT = "fact"           # Observed facts (immutable)
    DECISION = "decision"   # Decisions made during workflow
    ARTIFACT = "artifact"   # Generated artifacts (plans, analyses)
    CRITIQUE = "critique"   # Critiques of decisions/artifacts
    PREFERENCE = "preference"  # User preferences
    CONTEXT = "context"     # Contextual information


class MemoryStatus(str, Enum):
    """Status of memory entries."""
    ACTIVE = "active"       # Currently valid
    SUPERSEDED = "superseded"  # Replaced by newer entry
    CLOSED = "closed"       # Critique addressed/closed
    ARCHIVED = "archived"   # Old but preserved


@dataclass
class MemoryEntry:
    """
    A single memory entry.

    Represents a piece of information stored in memory,
    with metadata for querying and lifecycle management.
    """
    key: str
    value: Any
    memory_type: MemoryType = MemoryType.FACT
    status: MemoryStatus = MemoryStatus.ACTIVE
    namespace: str = "default"
    user_id: Optional[str] = None
    pod_name: Optional[str] = None
    run_id: Optional[str] = None
    correlation_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # For critique tracking
    related_entry_id: Optional[str] = None
    is_closed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "memory_type": self.memory_type.value,
            "status": self.status.value,
            "namespace": self.namespace,
            "user_id": self.user_id,
            "pod_name": self.pod_name,
            "run_id": self.run_id,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "tags": list(self.tags),
            "metadata": self.metadata,
            "related_entry_id": self.related_entry_id,
            "is_closed": self.is_closed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Create from dictionary."""
        return cls(
            key=data["key"],
            value=data["value"],
            memory_type=MemoryType(data.get("memory_type", "fact")),
            status=MemoryStatus(data.get("status", "active")),
            namespace=data.get("namespace", "default"),
            user_id=data.get("user_id"),
            pod_name=data.get("pod_name"),
            run_id=data.get("run_id"),
            correlation_id=data.get("correlation_id"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            tags=set(data.get("tags", [])),
            metadata=data.get("metadata", {}),
            related_entry_id=data.get("related_entry_id"),
            is_closed=data.get("is_closed", False),
        )


@dataclass
class MemoryQuery:
    """
    Query parameters for memory retrieval.

    Allows filtering by various criteria.
    """
    user_id: Optional[str] = None
    pod_name: Optional[str] = None
    namespace: Optional[str] = None
    memory_type: Optional[MemoryType] = None
    status: Optional[MemoryStatus] = None
    run_id: Optional[str] = None
    correlation_id: Optional[str] = None
    tags: Optional[Set[str]] = None
    key_prefix: Optional[str] = None
    include_expired: bool = False
    limit: int = 100
    offset: int = 0


class MemoryProvider(ABC):
    """
    Abstract base class for memory providers.

    All memory backends must implement this interface to be
    compatible with the HUAP memory system.
    """

    @abstractmethod
    async def get(
        self,
        key: str,
        *,
        user_id: Optional[str] = None,
        pod_name: Optional[str] = None,
        namespace: str = "default",
    ) -> Optional[MemoryEntry]:
        """
        Get a single memory entry by key.

        Args:
            key: Entry key
            user_id: Optional user filter
            pod_name: Optional pod filter
            namespace: Memory namespace

        Returns:
            MemoryEntry if found, None otherwise
        """
        pass

    @abstractmethod
    async def set(
        self,
        entry: MemoryEntry,
    ) -> MemoryEntry:
        """
        Store a memory entry.

        Args:
            entry: Entry to store

        Returns:
            Stored entry (may include generated ID)
        """
        pass

    @abstractmethod
    async def delete(
        self,
        key: str,
        *,
        user_id: Optional[str] = None,
        pod_name: Optional[str] = None,
        namespace: str = "default",
    ) -> bool:
        """
        Delete a memory entry.

        Args:
            key: Entry key
            user_id: Optional user filter
            pod_name: Optional pod filter
            namespace: Memory namespace

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def query(
        self,
        query: MemoryQuery,
    ) -> List[MemoryEntry]:
        """
        Query memory entries.

        Args:
            query: Query parameters

        Returns:
            List of matching entries
        """
        pass

    @abstractmethod
    async def list_keys(
        self,
        *,
        user_id: Optional[str] = None,
        pod_name: Optional[str] = None,
        namespace: str = "default",
    ) -> List[str]:
        """
        List all keys in a namespace.

        Args:
            user_id: Optional user filter
            pod_name: Optional pod filter
            namespace: Memory namespace

        Returns:
            List of keys
        """
        pass

    # =========================================================================
    # FACT METHODS
    # =========================================================================

    async def store_fact(
        self,
        key: str,
        value: Any,
        *,
        user_id: Optional[str] = None,
        pod_name: Optional[str] = None,
        namespace: str = "facts",
        run_id: Optional[str] = None,
        tags: Optional[Set[str]] = None,
    ) -> MemoryEntry:
        """Store an observed fact (immutable)."""
        entry = MemoryEntry(
            key=key,
            value=value,
            memory_type=MemoryType.FACT,
            namespace=namespace,
            user_id=user_id,
            pod_name=pod_name,
            run_id=run_id,
            tags=tags or set(),
        )
        return await self.set(entry)

    async def get_facts(
        self,
        *,
        user_id: Optional[str] = None,
        pod_name: Optional[str] = None,
        namespace: str = "facts",
        limit: int = 100,
    ) -> List[MemoryEntry]:
        """Get all facts."""
        return await self.query(MemoryQuery(
            user_id=user_id,
            pod_name=pod_name,
            namespace=namespace,
            memory_type=MemoryType.FACT,
            limit=limit,
        ))

    # =========================================================================
    # DECISION METHODS
    # =========================================================================

    async def store_decision(
        self,
        key: str,
        decision: Any,
        *,
        user_id: Optional[str] = None,
        pod_name: Optional[str] = None,
        namespace: str = "decisions",
        run_id: Optional[str] = None,
        rationale: Optional[str] = None,
    ) -> MemoryEntry:
        """Store a decision made during workflow."""
        entry = MemoryEntry(
            key=key,
            value=decision,
            memory_type=MemoryType.DECISION,
            namespace=namespace,
            user_id=user_id,
            pod_name=pod_name,
            run_id=run_id,
            metadata={"rationale": rationale} if rationale else {},
        )
        return await self.set(entry)

    async def get_decisions(
        self,
        *,
        user_id: Optional[str] = None,
        pod_name: Optional[str] = None,
        namespace: str = "decisions",
        run_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[MemoryEntry]:
        """Get all decisions."""
        return await self.query(MemoryQuery(
            user_id=user_id,
            pod_name=pod_name,
            namespace=namespace,
            memory_type=MemoryType.DECISION,
            run_id=run_id,
            limit=limit,
        ))

    # =========================================================================
    # ARTIFACT METHODS
    # =========================================================================

    async def store_artifact(
        self,
        key: str,
        artifact: Any,
        *,
        user_id: Optional[str] = None,
        pod_name: Optional[str] = None,
        namespace: str = "artifacts",
        run_id: Optional[str] = None,
        artifact_type: Optional[str] = None,
    ) -> MemoryEntry:
        """Store a generated artifact (plan, analysis, etc.)."""
        entry = MemoryEntry(
            key=key,
            value=artifact,
            memory_type=MemoryType.ARTIFACT,
            namespace=namespace,
            user_id=user_id,
            pod_name=pod_name,
            run_id=run_id,
            metadata={"artifact_type": artifact_type} if artifact_type else {},
        )
        return await self.set(entry)

    async def get_artifacts(
        self,
        *,
        user_id: Optional[str] = None,
        pod_name: Optional[str] = None,
        namespace: str = "artifacts",
        run_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[MemoryEntry]:
        """Get all artifacts."""
        return await self.query(MemoryQuery(
            user_id=user_id,
            pod_name=pod_name,
            namespace=namespace,
            memory_type=MemoryType.ARTIFACT,
            run_id=run_id,
            limit=limit,
        ))

    # =========================================================================
    # CRITIQUE METHODS
    # =========================================================================

    async def store_critique(
        self,
        key: str,
        critique: Any,
        *,
        related_entry_id: str,
        user_id: Optional[str] = None,
        pod_name: Optional[str] = None,
        namespace: str = "critiques",
        run_id: Optional[str] = None,
    ) -> MemoryEntry:
        """Store a critique of a decision or artifact."""
        entry = MemoryEntry(
            key=key,
            value=critique,
            memory_type=MemoryType.CRITIQUE,
            namespace=namespace,
            user_id=user_id,
            pod_name=pod_name,
            run_id=run_id,
            related_entry_id=related_entry_id,
            is_closed=False,
        )
        return await self.set(entry)

    async def close_critique(
        self,
        key: str,
        *,
        user_id: Optional[str] = None,
        pod_name: Optional[str] = None,
        namespace: str = "critiques",
    ) -> Optional[MemoryEntry]:
        """Mark a critique as closed (addressed)."""
        entry = await self.get(
            key,
            user_id=user_id,
            pod_name=pod_name,
            namespace=namespace,
        )
        if entry:
            entry.is_closed = True
            entry.status = MemoryStatus.CLOSED
            entry.updated_at = datetime.utcnow()
            return await self.set(entry)
        return None

    async def get_open_critiques(
        self,
        *,
        user_id: Optional[str] = None,
        pod_name: Optional[str] = None,
        namespace: str = "critiques",
        limit: int = 100,
    ) -> List[MemoryEntry]:
        """Get all open (unaddressed) critiques."""
        all_critiques = await self.query(MemoryQuery(
            user_id=user_id,
            pod_name=pod_name,
            namespace=namespace,
            memory_type=MemoryType.CRITIQUE,
            status=MemoryStatus.ACTIVE,
            limit=limit,
        ))
        return [c for c in all_critiques if not c.is_closed]

    async def get_critique_closure_rate(
        self,
        *,
        user_id: Optional[str] = None,
        pod_name: Optional[str] = None,
        namespace: str = "critiques",
    ) -> float:
        """
        Calculate the critique closure rate.

        Returns:
            Ratio of closed critiques to total critiques (0.0 - 1.0)
        """
        all_critiques = await self.query(MemoryQuery(
            user_id=user_id,
            pod_name=pod_name,
            namespace=namespace,
            memory_type=MemoryType.CRITIQUE,
            limit=10000,
        ))

        if not all_critiques:
            return 1.0  # No critiques = perfect score

        closed = sum(1 for c in all_critiques if c.is_closed)
        return closed / len(all_critiques)
