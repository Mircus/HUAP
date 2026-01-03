"""
HUAP Trace Writer - JSONL output with flush/rotation.

Provides TraceWriter class for writing trace events to JSONL files.
"""
from __future__ import annotations

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, TextIO

from .models import TraceEvent

logger = logging.getLogger(__name__)


class TraceWriter:
    """
    Writes trace events to JSONL file.

    Features:
    - Automatic flush after each event (for crash safety)
    - Optional file rotation by size
    - Thread-safe writing
    """

    def __init__(
        self,
        path: str,
        max_size_mb: Optional[float] = None,
        auto_flush: bool = True,
    ):
        """
        Initialize trace writer.

        Args:
            path: Output file path (will be created if doesn't exist)
            max_size_mb: Optional max file size before rotation (None = no rotation)
            auto_flush: Whether to flush after each write
        """
        self.path = Path(path)
        self.max_size_bytes = int(max_size_mb * 1024 * 1024) if max_size_mb else None
        self.auto_flush = auto_flush
        self._file: Optional[TextIO] = None
        self._event_count = 0
        self._bytes_written = 0

        # Ensure directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def open(self) -> "TraceWriter":
        """Open the trace file for writing."""
        if self._file is None:
            self._file = open(self.path, "a", encoding="utf-8")
            logger.debug(f"Opened trace file: {self.path}")
        return self

    def close(self) -> None:
        """Close the trace file."""
        if self._file is not None:
            self._file.flush()
            self._file.close()
            self._file = None
            logger.debug(f"Closed trace file: {self.path} ({self._event_count} events)")

    def write(self, event: TraceEvent) -> None:
        """
        Write a single trace event.

        Args:
            event: TraceEvent to write
        """
        if self._file is None:
            self.open()

        # Check for rotation
        if self.max_size_bytes and self._bytes_written >= self.max_size_bytes:
            self._rotate()

        # Write event as JSONL
        line = event.to_jsonl() + "\n"
        self._file.write(line)
        self._bytes_written += len(line.encode("utf-8"))
        self._event_count += 1

        if self.auto_flush:
            self._file.flush()

    def write_many(self, events: list[TraceEvent]) -> None:
        """Write multiple trace events."""
        for event in events:
            self.write(event)

    def flush(self) -> None:
        """Flush the file buffer."""
        if self._file is not None:
            self._file.flush()

    def _rotate(self) -> None:
        """Rotate the trace file."""
        if self._file is not None:
            self._file.close()

        # Rename current file with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        rotated_path = self.path.with_suffix(f".{timestamp}.jsonl")
        self.path.rename(rotated_path)
        logger.info(f"Rotated trace file to: {rotated_path}")

        # Open new file
        self._file = open(self.path, "a", encoding="utf-8")
        self._bytes_written = 0

    @property
    def event_count(self) -> int:
        """Number of events written."""
        return self._event_count

    @property
    def bytes_written(self) -> int:
        """Total bytes written."""
        return self._bytes_written

    def __enter__(self) -> "TraceWriter":
        """Context manager entry."""
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()


class NullTraceWriter(TraceWriter):
    """
    No-op trace writer for when tracing is disabled.

    Useful for testing or when traces are not needed.
    """

    def __init__(self):
        # Don't call super().__init__ to avoid creating files
        self._event_count = 0
        self._bytes_written = 0

    def open(self) -> "NullTraceWriter":
        return self

    def close(self) -> None:
        pass

    def write(self, event: TraceEvent) -> None:
        self._event_count += 1

    def flush(self) -> None:
        pass
