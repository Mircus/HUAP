"""
fs_sandbox — Sandboxed filesystem tool.

Enforces:
- Root directory (no path traversal)
- Size caps per file
- Read/write allowlists
- Traces file ops (metadata only, never file contents)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import BaseTool, ToolResult, ToolStatus, ToolCategory


class FsSandbox(BaseTool):
    """Sandboxed file I/O confined to a root directory."""

    name = "fs_sandbox"
    description = "Read/write files within a sandboxed root directory"
    category = ToolCategory.STORAGE

    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read", "write", "list", "exists"],
                "description": "File operation",
            },
            "path": {"type": "string", "description": "Relative path inside the sandbox"},
            "root": {"type": "string", "description": "Sandbox root directory (absolute)"},
            "content": {"type": "string", "description": "Content to write (for write action)"},
            "max_bytes": {"type": "integer", "default": 1_048_576, "description": "Max file size in bytes"},
            "allowed_extensions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Allowed file extensions (e.g. ['.json', '.txt']). Empty = all.",
            },
        },
        "required": ["action", "path", "root"],
    }

    async def execute(self, input_data: Dict[str, Any], context: Any = None) -> ToolResult:
        action: str = input_data["action"]
        rel_path: str = input_data["path"]
        root: str = input_data["root"]
        content: Optional[str] = input_data.get("content")
        max_bytes: int = input_data.get("max_bytes", 1_048_576)
        allowed_ext: List[str] = input_data.get("allowed_extensions", [])

        root_path = Path(root).resolve()
        target = (root_path / rel_path).resolve()

        # Path traversal check
        try:
            target.relative_to(root_path)
        except ValueError:
            return ToolResult(
                status=ToolStatus.ERROR,
                data={"error": f"Path traversal denied: '{rel_path}' escapes root '{root}'"},
            )

        # Extension check
        if allowed_ext and target.suffix and target.suffix not in allowed_ext:
            return ToolResult(
                status=ToolStatus.ERROR,
                data={"error": f"Extension '{target.suffix}' not allowed. Allowed: {allowed_ext}"},
            )

        if action == "read":
            return self._read(target, max_bytes)
        elif action == "write":
            return self._write(target, content or "", max_bytes)
        elif action == "list":
            return self._list(target)
        elif action == "exists":
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"exists": target.exists(), "path": str(target.relative_to(root_path))},
            )
        else:
            return ToolResult(
                status=ToolStatus.ERROR,
                data={"error": f"Unknown action '{action}'"},
            )

    @staticmethod
    def _read(target: Path, max_bytes: int) -> ToolResult:
        if not target.exists():
            return ToolResult(status=ToolStatus.ERROR, data={"error": f"File not found: {target.name}"})
        size = target.stat().st_size
        if size > max_bytes:
            return ToolResult(status=ToolStatus.ERROR, data={"error": f"File too large: {size} > {max_bytes}"})
        text = target.read_text(encoding="utf-8")
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"content": text, "size_bytes": size, "path": target.name},
        )

    @staticmethod
    def _write(target: Path, content: str, max_bytes: int) -> ToolResult:
        encoded = content.encode("utf-8")
        if len(encoded) > max_bytes:
            return ToolResult(status=ToolStatus.ERROR, data={"error": f"Content too large: {len(encoded)} > {max_bytes}"})
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(encoded)
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={"written_bytes": len(encoded), "path": target.name},
        )

    @staticmethod
    def _list(target: Path) -> ToolResult:
        if not target.exists():
            return ToolResult(status=ToolStatus.ERROR, data={"error": f"Directory not found: {target.name}"})
        if not target.is_dir():
            return ToolResult(status=ToolStatus.ERROR, data={"error": f"Not a directory: {target.name}"})
        entries = [
            {"name": p.name, "is_dir": p.is_dir(), "size": p.stat().st_size if p.is_file() else 0}
            for p in sorted(target.iterdir())
        ]
        return ToolResult(status=ToolStatus.SUCCESS, data={"entries": entries, "count": len(entries)})
