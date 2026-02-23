"""
HUAP Memory CLI — search, ingest, and inspect persisted memories.

Commands:
    huap memory search <query>           — keyword search across stored memories
    huap memory ingest --from-trace <f>  — ingest trace events into memory
    huap memory stats                    — show db path, entry count, type breakdown
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click


def _default_db_path() -> str:
    return str(Path.cwd() / ".huap" / "memory.db")


def _get_provider(db_path: str | None = None):
    """Create and connect a HindsightProvider."""
    from ..memory.providers.hindsight import HindsightProvider
    p = HindsightProvider(db_path=db_path or _default_db_path())
    if not asyncio.run(p.connect()):
        click.echo("Error: could not open memory database.", err=True)
        sys.exit(1)
    return p


@click.group("memory")
def memory():
    """Memory management commands."""
    pass


@memory.command("search")
@click.argument("query")
@click.option("--k", "-k", default=10, type=int, help="Max results (default 10)")
@click.option("--user", "-u", default=None, help="Filter by user_id")
@click.option("--pod", "-p", default=None, help="Filter by pod_name")
@click.option("--db", default=None, help="Path to memory.db")
@click.option("--json-out", "json_output", is_flag=True, help="Output as JSON")
def memory_search(query: str, k: int, user: str | None, pod: str | None, db: str | None, json_output: bool):
    """Search stored memories by keyword."""
    provider = _get_provider(db)
    results = asyncio.run(provider.search_semantic(query, user_id=user, pod_name=pod, limit=k))
    provider.close()

    if not results:
        click.echo("No memories found.")
        return

    if json_output:
        click.echo(json.dumps([e.to_dict() for e in results], indent=2, default=str))
        return

    click.echo(f"Found {len(results)} result(s) for \"{query}\":\n")
    for i, entry in enumerate(results, 1):
        val = entry.value
        if isinstance(val, str) and len(val) > 120:
            val = val[:120] + "..."
        elif isinstance(val, dict):
            val = json.dumps(val, default=str)
            if len(val) > 120:
                val = val[:120] + "..."
        click.echo(f"  {i}. [{entry.memory_type.value}] {entry.key}")
        click.echo(f"     {val}")
        if entry.run_id:
            click.echo(f"     run: {entry.run_id}  ns: {entry.namespace}")
        click.echo()


@memory.command("ingest")
@click.option("--from-trace", "trace_path", required=True, help="Path to JSONL trace file")
@click.option("--user", "-u", default="default", help="User ID for stored entries")
@click.option("--db", default=None, help="Path to memory.db")
def memory_ingest(trace_path: str, user: str, db: str | None):
    """Ingest trace events into the memory database."""
    from ..memory.context_builder import ContextBuilder

    path = Path(trace_path)
    if not path.exists():
        click.echo(f"Error: trace file not found: {trace_path}", err=True)
        sys.exit(1)

    provider = _get_provider(db)
    builder = ContextBuilder(provider=provider)

    # Build context from trace (this also persists via the provider)
    context = asyncio.run(builder.build_from_trace(str(path), persist=True))

    # Count what was ingested
    facts = len(context.facts)
    decisions = len(context.decisions)
    artifacts = len(context.artifacts)
    critiques = len(context.critiques)
    total = facts + decisions + artifacts + critiques

    provider.close()

    click.echo(f"Ingested {total} entries from {path.name}:")
    click.echo(f"  Facts:     {facts}")
    click.echo(f"  Decisions: {decisions}")
    click.echo(f"  Artifacts: {artifacts}")
    click.echo(f"  Critiques: {critiques}")
    click.echo(f"\nStored in: {db or _default_db_path()}")


@memory.command("stats")
@click.option("--db", default=None, help="Path to memory.db")
def memory_stats(db: str | None):
    """Show memory database statistics."""
    db_path = db or _default_db_path()
    p = Path(db_path)

    if not p.exists():
        click.echo(f"No memory database found at {db_path}")
        click.echo("Run  huap memory ingest --from-trace <file>  to create one.")
        return

    provider = _get_provider(db)

    # Get counts by type
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    cur = conn.execute("SELECT COUNT(*) as cnt FROM memory_entries")
    total = cur.fetchone()["cnt"]

    cur = conn.execute("SELECT memory_type, COUNT(*) as cnt FROM memory_entries GROUP BY memory_type ORDER BY cnt DESC")
    type_counts = {row["memory_type"]: row["cnt"] for row in cur.fetchall()}

    cur = conn.execute("SELECT COUNT(DISTINCT namespace) as cnt FROM memory_entries")
    ns_count = cur.fetchone()["cnt"]

    cur = conn.execute("SELECT COUNT(DISTINCT run_id) as cnt FROM memory_entries WHERE run_id IS NOT NULL")
    run_count = cur.fetchone()["cnt"]

    conn.close()
    provider.close()

    click.echo(f"Memory Database: {db_path}")
    click.echo(f"Size:            {p.stat().st_size / 1024:.1f} KB")
    click.echo(f"Total entries:   {total}")
    click.echo(f"Namespaces:      {ns_count}")
    click.echo(f"Runs:            {run_count}")
    click.echo()
    if type_counts:
        click.echo("By type:")
        for typ, cnt in type_counts.items():
            click.echo(f"  {typ:<16} {cnt}")
