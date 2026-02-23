"""Tests for P9 — Plugin SDK, MemoryPort, ingest policy, CMP toolpack, HindsightProvider."""
import pytest
from pathlib import Path

from hu_core.plugins.spec import PluginSpec
from hu_core.plugins.registry import PluginRegistry
from hu_core.ports.memory import InMemoryPort, MemoryItem
from hu_core.tools.memory_tools import memory_retain, memory_recall, memory_reflect
from hu_core.policies.memory_ingest import MemoryIngestPolicy
from hu_core.memory.providers.hindsight import HindsightProvider
from hu_core.memory.providers.base import MemoryEntry, MemoryQuery, MemoryType, MemoryStatus


# ═══════════════════════════════════════════════════════════════════════════
# Plugin Spec
# ═══════════════════════════════════════════════════════════════════════════

class TestPluginSpec:
    def test_valid_types(self):
        for t in ("memory", "toolpack", "provider", "other"):
            s = PluginSpec(id="x", type=t, impl="mod:Cls")
            assert s.type == t

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Unknown plugin type"):
            PluginSpec(id="x", type="banana", impl="mod:Cls")

    def test_from_dict_roundtrip(self):
        d = {"id": "test", "type": "memory", "impl": "a.b:C", "enabled": False,
             "settings": {"key": "val"}}
        spec = PluginSpec.from_dict(d)
        assert spec.to_dict() == d


# ═══════════════════════════════════════════════════════════════════════════
# Plugin Registry
# ═══════════════════════════════════════════════════════════════════════════

class TestPluginRegistry:
    def test_empty_registry(self):
        reg = PluginRegistry()
        assert reg.list() == []

    def test_load_from_yaml(self, tmp_path):
        cfg = tmp_path / "plugins.yaml"
        cfg.write_text(
            "plugins:\n"
            "  - id: test_plug\n"
            "    type: other\n"
            "    impl: os.path:join\n"
            "    enabled: true\n"
        )
        reg = PluginRegistry.load(str(cfg))
        assert len(reg.list()) == 1
        assert reg.get("test_plug").impl == "os.path:join"

    def test_list_enabled_only(self):
        specs = [
            PluginSpec(id="a", type="other", impl="x:Y", enabled=True),
            PluginSpec(id="b", type="other", impl="x:Z", enabled=False),
        ]
        reg = PluginRegistry(specs)
        assert len(reg.list(only_enabled=True)) == 1

    def test_by_type(self):
        specs = [
            PluginSpec(id="a", type="memory", impl="x:Y"),
            PluginSpec(id="b", type="toolpack", impl="x:Z"),
        ]
        reg = PluginRegistry(specs)
        assert len(reg.by_type("memory")) == 1

    def test_resolve_imports(self):
        spec = PluginSpec(id="ospath", type="other", impl="os.path:join")
        reg = PluginRegistry([spec])
        fn = reg.resolve("ospath")
        import os.path
        assert fn is os.path.join

    def test_resolve_unknown_raises(self):
        reg = PluginRegistry()
        with pytest.raises(KeyError):
            reg.resolve("nope")

    def test_resolve_bad_format_raises(self):
        spec = PluginSpec(id="bad", type="other", impl="no_colon")
        reg = PluginRegistry([spec])
        with pytest.raises(ValueError, match="module:Class"):
            reg.resolve("bad")

    def test_load_missing_file_returns_empty(self):
        reg = PluginRegistry.load("/nonexistent/path.yaml")
        assert reg.list() == []


# ═══════════════════════════════════════════════════════════════════════════
# MemoryPort (InMemoryPort)
# ═══════════════════════════════════════════════════════════════════════════

class TestInMemoryPort:
    @pytest.mark.asyncio
    async def test_retain_returns_item(self):
        port = InMemoryPort()
        item = await port.retain("bank1", "hello world")
        assert isinstance(item, MemoryItem)
        assert item.content == "hello world"
        assert item.bank_id == "bank1"

    @pytest.mark.asyncio
    async def test_recall_matches_substring(self):
        port = InMemoryPort()
        await port.retain("b", "I like dark mode")
        await port.retain("b", "The weather is nice")
        results = await port.recall("b", "dark mode", k=5)
        assert len(results) == 2
        assert results[0].content == "I like dark mode"
        assert results[0].score == 1.0

    @pytest.mark.asyncio
    async def test_recall_empty_bank(self):
        port = InMemoryPort()
        results = await port.recall("empty", "anything")
        assert results == []

    @pytest.mark.asyncio
    async def test_reflect_delegates_to_recall(self):
        port = InMemoryPort()
        await port.retain("b", "fact one")
        results = await port.reflect("b", "fact", k=5)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_recall_respects_k(self):
        port = InMemoryPort()
        for i in range(10):
            await port.retain("b", f"item {i} match")
        results = await port.recall("b", "match", k=3)
        assert len(results) == 3


# ═══════════════════════════════════════════════════════════════════════════
# Memory Tools
# ═══════════════════════════════════════════════════════════════════════════

class TestMemoryTools:
    @pytest.mark.asyncio
    async def test_retain_and_recall_roundtrip(self):
        port = InMemoryPort()
        await memory_retain("bank", "test content", port=port)
        result = await memory_recall("bank", "test", port=port)
        assert result["count"] == 1
        assert result["items"][0]["content"] == "test content"

    @pytest.mark.asyncio
    async def test_reflect(self):
        port = InMemoryPort()
        await memory_retain("bank", "insight about tools", port=port)
        result = await memory_reflect("bank", "tools", port=port)
        assert result["status"] == "reflected"
        assert result["count"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# Memory Ingest Policy
# ═══════════════════════════════════════════════════════════════════════════

class TestMemoryIngestPolicy:
    def test_allows_normal_content(self):
        policy = MemoryIngestPolicy()
        dec = policy.should_retain("User prefers dark mode", context="preference")
        assert dec.allowed is True

    def test_rejects_too_short(self):
        policy = MemoryIngestPolicy(min_content_length=10)
        dec = policy.should_retain("hi")
        assert dec.allowed is False
        assert "Too short" in dec.reason

    def test_rejects_too_long(self):
        policy = MemoryIngestPolicy(max_content_length=20)
        dec = policy.should_retain("x" * 50)
        assert dec.allowed is False
        assert "Too long" in dec.reason

    def test_rejects_skip_pattern(self):
        policy = MemoryIngestPolicy()
        dec = policy.should_retain("This is a raw transcript of the full conversation")
        assert dec.allowed is False
        assert "skip pattern" in dec.reason

    def test_dedup_rejects_duplicate(self):
        policy = MemoryIngestPolicy(dedup=True)
        dec1 = policy.should_retain("User prefers dark mode")
        dec2 = policy.should_retain("User prefers dark mode")
        assert dec1.allowed is True
        assert dec2.allowed is False
        assert "Duplicate" in dec2.reason

    def test_dedup_disabled(self):
        policy = MemoryIngestPolicy(dedup=False)
        policy.should_retain("Same content twice")
        dec = policy.should_retain("Same content twice")
        assert dec.allowed is True

    def test_context_filter(self):
        policy = MemoryIngestPolicy(allowed_contexts={"preference"})
        dec = policy.should_retain("important thing", context="random")
        assert dec.allowed is False

    def test_sanitize_redacts_openai_key(self):
        policy = MemoryIngestPolicy()
        text = "Using key sk-abc123def456ghi789jkl012mno345pqr678"
        sanitized = policy.sanitize(text)
        assert "sk-abc" not in sanitized
        assert "[REDACTED_API_KEY]" in sanitized

    def test_sanitize_redacts_github_pat(self):
        policy = MemoryIngestPolicy()
        text = "token: ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789AB"
        sanitized = policy.sanitize(text)
        assert "ghp_" not in sanitized
        assert "[REDACTED_TOKEN]" in sanitized

    def test_sanitize_redacts_aws_key(self):
        policy = MemoryIngestPolicy()
        text = "AWS access key: AKIAIOSFODNN7EXAMPLE"
        sanitized = policy.sanitize(text)
        assert "AKIA" not in sanitized
        assert "[REDACTED_AWS_KEY]" in sanitized

    def test_sanitize_preserves_normal_text(self):
        policy = MemoryIngestPolicy()
        text = "User prefers dark mode and uses Python 3.11"
        assert policy.sanitize(text) == text

    def test_sanitize_redacts_bearer_token(self):
        policy = MemoryIngestPolicy()
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"
        sanitized = policy.sanitize(text)
        assert "eyJh" not in sanitized
        assert "Bearer [REDACTED]" in sanitized


# ═══════════════════════════════════════════════════════════════════════════
# HindsightProvider (SQLite backend)
# ═══════════════════════════════════════════════════════════════════════════

class TestHindsightProvider:
    @pytest.fixture
    async def provider(self, tmp_path):
        p = HindsightProvider(db_path=str(tmp_path / "test.db"))
        assert await p.connect() is True
        yield p
        p.close()

    def _make_entry(self, key="test_key", value="test_value", **kwargs):
        defaults = {
            "key": key,
            "value": value,
            "memory_type": MemoryType.FACT,
            "namespace": "default",
        }
        defaults.update(kwargs)
        return MemoryEntry(**defaults)

    @pytest.mark.asyncio
    async def test_connect_creates_db(self, tmp_path):
        db = tmp_path / "sub" / "test.db"
        p = HindsightProvider(db_path=str(db))
        result = await p.connect()
        assert result is True
        assert db.exists()
        p.close()

    @pytest.mark.asyncio
    async def test_set_and_get_roundtrip(self, provider):
        entry = self._make_entry(key="k1", value={"msg": "hello"})
        await provider.set(entry)
        got = await provider.get("k1")
        assert got is not None
        assert got.key == "k1"
        assert got.value == {"msg": "hello"}
        assert got.memory_type == MemoryType.FACT

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self, provider):
        got = await provider.get("nonexistent")
        assert got is None

    @pytest.mark.asyncio
    async def test_set_overwrites(self, provider):
        await provider.set(self._make_entry(key="k1", value="first"))
        await provider.set(self._make_entry(key="k1", value="second"))
        got = await provider.get("k1")
        assert got.value == "second"

    @pytest.mark.asyncio
    async def test_delete(self, provider):
        await provider.set(self._make_entry(key="del_me"))
        assert await provider.delete("del_me") is True
        assert await provider.get("del_me") is None

    @pytest.mark.asyncio
    async def test_delete_missing(self, provider):
        assert await provider.delete("nope") is False

    @pytest.mark.asyncio
    async def test_query_by_type(self, provider):
        await provider.set(self._make_entry(key="f1", memory_type=MemoryType.FACT, namespace="ns"))
        await provider.set(self._make_entry(key="d1", memory_type=MemoryType.DECISION, namespace="ns"))
        results = await provider.query(MemoryQuery(namespace="ns", memory_type=MemoryType.FACT))
        assert len(results) == 1
        assert results[0].key == "f1"

    @pytest.mark.asyncio
    async def test_query_by_run_id(self, provider):
        await provider.set(self._make_entry(key="r1", run_id="run_abc"))
        await provider.set(self._make_entry(key="r2", run_id="run_xyz"))
        results = await provider.query(MemoryQuery(run_id="run_abc"))
        assert len(results) == 1
        assert results[0].key == "r1"

    @pytest.mark.asyncio
    async def test_query_pagination(self, provider):
        for i in range(5):
            await provider.set(self._make_entry(key=f"p{i}", namespace="page"))
        results = await provider.query(MemoryQuery(namespace="page", limit=2, offset=0))
        assert len(results) == 2
        results2 = await provider.query(MemoryQuery(namespace="page", limit=2, offset=2))
        assert len(results2) == 2
        results3 = await provider.query(MemoryQuery(namespace="page", limit=2, offset=4))
        assert len(results3) == 1

    @pytest.mark.asyncio
    async def test_list_keys(self, provider):
        await provider.set(self._make_entry(key="a", namespace="ns"))
        await provider.set(self._make_entry(key="b", namespace="ns"))
        await provider.set(self._make_entry(key="c", namespace="other"))
        keys = await provider.list_keys(namespace="ns")
        assert sorted(keys) == ["a", "b"]

    @pytest.mark.asyncio
    async def test_persistence_across_sessions(self, tmp_path):
        db = str(tmp_path / "persist.db")
        # Session 1: write
        p1 = HindsightProvider(db_path=db)
        await p1.connect()
        await p1.set(self._make_entry(key="persist_key", value="survives"))
        p1.close()
        # Session 2: read
        p2 = HindsightProvider(db_path=db)
        await p2.connect()
        got = await p2.get("persist_key")
        assert got is not None
        assert got.value == "survives"
        p2.close()

    @pytest.mark.asyncio
    async def test_search_semantic_keyword(self, provider):
        await provider.set(self._make_entry(key="agent_pref", value="User prefers dark mode"))
        await provider.set(self._make_entry(key="weather", value="Today is sunny"))
        results = await provider.search_semantic("dark mode")
        assert len(results) == 1
        assert results[0].key == "agent_pref"

    @pytest.mark.asyncio
    async def test_get_episode(self, provider):
        await provider.set(self._make_entry(key="e1", run_id="ep1", user_id="u1"))
        await provider.set(self._make_entry(key="e2", run_id="ep1", user_id="u1"))
        await provider.set(self._make_entry(key="e3", run_id="ep2", user_id="u1"))
        episode = await provider.get_episode("ep1", user_id="u1")
        assert episode is not None
        assert episode["entry_count"] == 2
        assert episode["episode_id"] == "ep1"

    @pytest.mark.asyncio
    async def test_reflect_returns_summary(self, provider):
        await provider.set(self._make_entry(key="f1", memory_type=MemoryType.FACT, user_id="u1"))
        await provider.set(self._make_entry(key="f2", memory_type=MemoryType.FACT, user_id="u1"))
        await provider.set(self._make_entry(key="d1", memory_type=MemoryType.DECISION, user_id="u1"))
        result = await provider.reflect(user_id="u1")
        assert result["status"] == "ok"
        assert result["total_entries"] == 3
        assert result["by_type"]["fact"] == 2
        assert result["by_type"]["decision"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# CMP Toolpack
# ═══════════════════════════════════════════════════════════════════════════

_has_cmp = False
try:
    import hu_plugins_cmp  # noqa: F401
    _has_cmp = True
except ImportError:
    pass


@pytest.mark.skipif(not _has_cmp, reason="hu-plugins-cmp not installed")
class TestCMPToolpack:
    def test_capture_creates_note(self, tmp_path):
        from hu_plugins_cmp.toolpack import cmp_capture
        result = cmp_capture("Hello world", title="test note", root=str(tmp_path))
        assert result["status"] == "captured"
        assert Path(result["path"]).exists()
        content = Path(result["path"]).read_text()
        assert "Hello world" in content
        assert "test note" in content  # frontmatter title

    def test_capture_appends(self, tmp_path):
        from hu_plugins_cmp.toolpack import cmp_capture
        cmp_capture("First", title="note", root=str(tmp_path))
        cmp_capture("Second", title="note", root=str(tmp_path))
        content = Path(tmp_path / "note.md").read_text()
        assert "First" in content
        assert "Second" in content

    def test_search(self, tmp_path):
        from hu_plugins_cmp.toolpack import cmp_capture, cmp_search
        cmp_capture("AI agents are cool", title="agents", root=str(tmp_path))
        cmp_capture("Cooking recipes", title="cooking", root=str(tmp_path))
        result = cmp_search("agents", root=str(tmp_path))
        assert result["count"] == 1
        assert result["results"][0]["slug"] == "agents"

    def test_search_empty(self, tmp_path):
        from hu_plugins_cmp.toolpack import cmp_search
        result = cmp_search("anything", root=str(tmp_path))
        assert result["count"] == 0

    def test_link(self, tmp_path):
        from hu_plugins_cmp.toolpack import cmp_capture, cmp_link
        cmp_capture("Note A", title="note-a", root=str(tmp_path))
        cmp_capture("Note B", title="note-b", root=str(tmp_path))
        result = cmp_link("note-a", "note-b", relation="related", root=str(tmp_path))
        assert result["status"] == "linked"
        a_content = (tmp_path / "note-a.md").read_text()
        assert "note-b" in a_content

    def test_toolpack_class(self, tmp_path):
        from hu_plugins_cmp.toolpack import CommonplaceToolpack
        tp = CommonplaceToolpack(root=str(tmp_path))
        tools = tp.get_tools()
        assert "cmp.capture" in tools
        assert "cmp.link" in tools
        assert "cmp.search" in tools
