"""
Tests for Model Registry + Router (P2).

Covers:
- Deterministic selection
- Privacy=local excludes cloud models
- Capability filtering
- Fallback to stub
"""
import os
import pytest

from hu_core.services.model_registry import ModelRegistry, ModelSpec, BUILTIN_MODELS
from hu_core.services.model_router import ModelRouter, RouterRule


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------

class TestModelRegistry:
    def test_builtin_models_loaded(self):
        reg = ModelRegistry()
        assert len(reg.list()) == len(BUILTIN_MODELS)

    def test_get_known_model(self):
        reg = ModelRegistry()
        spec = reg.get("stub_chat")
        assert spec is not None
        assert spec.provider == "stub"

    def test_get_unknown_returns_none(self):
        reg = ModelRegistry()
        assert reg.get("nonexistent") is None

    def test_filter_by_capability(self):
        reg = ModelRegistry()
        results = reg.filter(capability="chat")
        assert len(results) >= 1
        for m in results:
            assert "chat" in m.capabilities

    def test_filter_by_privacy_local(self):
        reg = ModelRegistry()
        results = reg.filter(privacy="local")
        for m in results:
            assert m.privacy == "local"
        # Cloud models should not appear
        ids = {m.id for m in results}
        assert "openai_gpt4omini_chat" not in ids

    def test_filter_by_max_usd(self):
        reg = ModelRegistry()
        results = reg.filter(max_usd_est=0.0)
        for m in results:
            assert m.usd_per_1k_tokens_est <= 0.0

    def test_filter_by_provider(self):
        reg = ModelRegistry()
        results = reg.filter(providers_allow=["stub"])
        assert all(m.provider == "stub" for m in results)

    def test_custom_models(self):
        custom = [ModelSpec(id="my_model", provider="openai", model="gpt-5", capabilities=["chat"])]
        reg = ModelRegistry(custom)
        assert len(reg.list()) == 1
        assert reg.get("my_model") is not None


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------

class TestModelRouter:
    def _make_router(self, rules=None):
        reg = ModelRegistry()
        return ModelRouter(reg, rules or [])

    def test_deterministic_selection(self):
        """Same inputs must always produce the same model."""
        router = self._make_router()
        d1 = router.select(capability="chat", privacy="cloud_ok")
        d2 = router.select(capability="chat", privacy="cloud_ok")
        assert d1.model.id == d2.model.id

    def test_privacy_local_excludes_cloud(self):
        router = self._make_router()
        decision = router.select(capability="chat", privacy="local")
        assert decision.model.privacy == "local"
        assert decision.model.provider != "openai"

    def test_capability_filtering(self):
        router = self._make_router()
        decision = router.select(capability="classify")
        assert "classify" in decision.model.capabilities

    def test_fallback_to_stub(self):
        """With only stub models, router should select stub."""
        reg = ModelRegistry([
            ModelSpec(id="stub_chat", provider="stub", model="stub",
                      capabilities=["chat"], privacy="local"),
        ])
        router = ModelRouter(reg)
        decision = router.select(capability="chat")
        assert decision.model.id == "stub_chat"

    def test_rule_based_preference(self):
        rules = [
            RouterRule(
                name="prefer_stub",
                when={"capability": "chat"},
                prefer=["stub_chat"],
            ),
        ]
        router = self._make_router(rules)
        decision = router.select(capability="chat")
        assert decision.model.id == "stub_chat"
        assert decision.rule_name == "prefer_stub"

    def test_rule_with_privacy_constraint(self):
        rules = [
            RouterRule(
                name="local_first",
                when={"capability": "chat", "privacy": "local"},
                prefer=["ollama_phi3_chat", "stub_chat"],
            ),
        ]
        router = self._make_router(rules)
        decision = router.select(capability="chat", privacy="local")
        # Should pick ollama first (it's first in prefer list and local)
        assert decision.model.id == "ollama_phi3_chat"

    def test_no_match_raises(self):
        reg = ModelRegistry([
            ModelSpec(id="only_chat", provider="stub", model="stub",
                      capabilities=["chat"], privacy="local"),
        ])
        router = ModelRouter(reg)
        with pytest.raises(ValueError, match="No models match"):
            router.select(capability="vision")

    def test_explain_returns_decision(self):
        router = self._make_router()
        result = router.explain(capability="chat")
        assert result["selected"] is not None
        assert "model_id" in result["selected"]
        assert "all_models" in result

    def test_explain_no_match_returns_error(self):
        reg = ModelRegistry([])
        router = ModelRouter(reg)
        result = router.explain(capability="chat")
        assert result["selected"] is None
        assert "error" in result

    def test_fallback_determinism_sorts_by_cost_then_id(self):
        """Without rules, cheapest model wins; ties broken by id (alpha)."""
        reg = ModelRegistry([
            ModelSpec(id="b_model", provider="stub", model="b", capabilities=["chat"], usd_per_1k_tokens_est=0.0),
            ModelSpec(id="a_model", provider="stub", model="a", capabilities=["chat"], usd_per_1k_tokens_est=0.0),
        ])
        router = ModelRouter(reg)
        decision = router.select(capability="chat")
        assert decision.model.id == "a_model"  # alphabetically first
        assert decision.rule_name == "__fallback"
