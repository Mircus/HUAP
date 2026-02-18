"""
Model Router for HUAP Specialist Squad Orchestrator.

Deterministic, rule-based model selection with full explainability.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .model_registry import ModelRegistry, ModelSpec


@dataclass
class RouterRule:
    """A single routing rule from the policy YAML."""
    name: str
    when: Dict[str, Any]  # capability, privacy, etc.
    prefer: List[str]     # ordered model IDs


@dataclass
class RouterDecision:
    """Outcome of a routing decision, including explainability."""
    model: ModelSpec
    rule_name: str
    reason: str
    candidates_considered: int
    filters_applied: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model.id,
            "provider": self.model.provider,
            "rule_name": self.rule_name,
            "reason": self.reason,
            "candidates_considered": self.candidates_considered,
            "filters_applied": self.filters_applied,
        }


class ModelRouter:
    """
    Rule-based model router.

    Selection is fully deterministic: rules are evaluated in order,
    ties are broken by the ``prefer`` list position, then alphabetically by id.
    """

    def __init__(
        self,
        registry: ModelRegistry,
        rules: Optional[List[RouterRule]] = None,
    ):
        self._registry = registry
        self._rules: List[RouterRule] = rules or []

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load(
        cls,
        registry: Optional[ModelRegistry] = None,
        policy_path: Optional[str] = None,
    ) -> "ModelRouter":
        """Load router from YAML policy (or env var), with optional registry."""
        if registry is None:
            registry = ModelRegistry.load()

        policy_path = policy_path or os.getenv("HUAP_ROUTER_POLICY_PATH")
        rules: List[RouterRule] = []
        if policy_path and Path(policy_path).exists():
            rules = cls._load_rules(Path(policy_path))

        return cls(registry, rules)

    @staticmethod
    def _load_rules(path: Path) -> List[RouterRule]:
        import yaml
        data = yaml.safe_load(path.read_text())
        rules: List[RouterRule] = []
        for entry in data.get("rules", []):
            rules.append(RouterRule(
                name=entry.get("name", "unnamed"),
                when=entry.get("when", {}),
                prefer=entry.get("prefer", []),
            ))
        return rules

    # ------------------------------------------------------------------
    # Core routing
    # ------------------------------------------------------------------

    def select(
        self,
        capability: str = "chat",
        privacy: Optional[str] = None,
        max_usd_est: Optional[float] = None,
        providers_allow: Optional[List[str]] = None,
        models_allow: Optional[List[str]] = None,
    ) -> RouterDecision:
        """
        Select the best model for the given constraints.

        Raises ValueError if no model matches.
        """
        privacy = privacy or os.getenv("HUAP_PRIVACY", "cloud_ok")
        filters: List[str] = []

        # 1. Filter by constraints
        candidates = self._registry.filter(
            capability=capability,
            privacy=privacy,
            max_usd_est=max_usd_est,
            providers_allow=providers_allow,
            models_allow=models_allow,
        )
        filters.append(f"capability={capability}")
        filters.append(f"privacy={privacy}")
        if max_usd_est is not None:
            filters.append(f"max_usd_est={max_usd_est}")
        if providers_allow:
            filters.append(f"providers_allow={providers_allow}")
        if models_allow:
            filters.append(f"models_allow={models_allow}")

        total_candidates = len(candidates)

        if not candidates:
            raise ValueError(
                f"No models match constraints: {filters}. "
                f"Registry has {len(self._registry.list())} model(s)."
            )

        # 2. Apply policy rules (first matching rule wins)
        for rule in self._rules:
            if self._rule_matches(rule, capability, privacy):
                for preferred_id in rule.prefer:
                    for c in candidates:
                        if c.id == preferred_id:
                            return RouterDecision(
                                model=c,
                                rule_name=rule.name,
                                reason=f"Matched rule '{rule.name}', preferred model '{c.id}'",
                                candidates_considered=total_candidates,
                                filters_applied=filters,
                            )

        # 3. Deterministic fallback: sort by cost asc, then id asc
        candidates.sort(key=lambda m: (m.usd_per_1k_tokens_est, m.id))
        chosen = candidates[0]
        return RouterDecision(
            model=chosen,
            rule_name="__fallback",
            reason=f"No matching rule; cheapest candidate '{chosen.id}'",
            candidates_considered=total_candidates,
            filters_applied=filters,
        )

    @staticmethod
    def _rule_matches(rule: RouterRule, capability: str, privacy: str) -> bool:
        when = rule.when
        if "capability" in when and when["capability"] != capability:
            return False
        if "privacy" in when and when["privacy"] != privacy:
            return False
        return True

    # ------------------------------------------------------------------
    # Explain (for CLI / debugging)
    # ------------------------------------------------------------------

    def explain(
        self,
        capability: str = "chat",
        privacy: Optional[str] = None,
        max_usd_est: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Return a human-readable explanation of the routing decision."""
        privacy = privacy or os.getenv("HUAP_PRIVACY", "cloud_ok")
        try:
            decision = self.select(
                capability=capability,
                privacy=privacy,
                max_usd_est=max_usd_est,
            )
        except ValueError as exc:
            return {
                "selected": None,
                "error": str(exc),
                "all_models": [m.to_dict() for m in self._registry.list()],
            }

        return {
            "selected": decision.to_dict(),
            "all_models": [m.to_dict() for m in self._registry.list()],
            "matching_candidates": decision.candidates_considered,
            "filters_applied": decision.filters_applied,
        }
