"""Tests for P9 — Plugin SDK, MemoryPort, ingest policy, CMP toolpack."""
import json
import pytest
from pathlib import Path

from hu_core.plugins.spec import PluginSpec
from hu_core.plugins.registry import PluginRegistry
from hu_core.ports.memory import InMemoryPort, MemoryItem
from hu_core.tools.memory_tools import memory_retain, memory_recall, memory_reflect
from hu_core.policies.memory_ingest import MemoryIngestPolicy, IngestDecision


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
