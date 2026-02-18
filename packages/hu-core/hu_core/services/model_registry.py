"""
Model Registry for HUAP Specialist Squad Orchestrator.

Provides:
- ModelSpec: dataclass describing a model's capabilities, privacy, and cost
- ModelRegistry: loads/lists/gets models from YAML config or built-in defaults
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ModelSpec:
    """Specification for a single model endpoint."""
    id: str
    provider: str  # stub | ollama | openai
    model: str
    capabilities: List[str] = field(default_factory=lambda: ["chat"])
    privacy: str = "cloud_ok"  # local | cloud_ok
    usd_per_1k_tokens_est: float = 0.0
    endpoint: Optional[str] = None

    def matches_capability(self, capability: str) -> bool:
        return capability in self.capabilities

    def matches_privacy(self, privacy: str) -> bool:
        if privacy == "cloud_ok":
            return True
        return self.privacy == privacy

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "provider": self.provider,
            "model": self.model,
            "capabilities": self.capabilities,
            "privacy": self.privacy,
            "usd_per_1k_tokens_est": self.usd_per_1k_tokens_est,
        }
        if self.endpoint:
            d["endpoint"] = self.endpoint
        return d


# Built-in fallback models (always available, no config file needed)
BUILTIN_MODELS: List[ModelSpec] = [
    ModelSpec(
        id="stub_chat",
        provider="stub",
        model="stub",
        capabilities=["chat", "classify", "extract"],
        privacy="local",
        usd_per_1k_tokens_est=0.0,
    ),
    ModelSpec(
        id="ollama_phi3_chat",
        provider="ollama",
        model="phi3",
        capabilities=["chat", "classify", "extract"],
        privacy="local",
        usd_per_1k_tokens_est=0.0,
        endpoint="http://localhost:11434",
    ),
    ModelSpec(
        id="openai_gpt4omini_chat",
        provider="openai",
        model="gpt-4o-mini",
        capabilities=["chat", "classify", "extract"],
        privacy="cloud_ok",
        usd_per_1k_tokens_est=0.00015,
    ),
]


class ModelRegistry:
    """Registry of available model specs, loaded from YAML or built-in defaults."""

    def __init__(self, models: Optional[List[ModelSpec]] = None):
        self._models: Dict[str, ModelSpec] = {}
        for m in (BUILTIN_MODELS if models is None else models):
            self._models[m.id] = m

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: Optional[str] = None) -> "ModelRegistry":
        """Load registry from YAML file or env var, falling back to built-ins."""
        path = path or os.getenv("HUAP_MODEL_REGISTRY_PATH")
        if path and Path(path).exists():
            return cls._from_yaml(Path(path))
        return cls()

    @classmethod
    def _from_yaml(cls, path: Path) -> "ModelRegistry":
        import yaml
        data = yaml.safe_load(path.read_text())
        specs: List[ModelSpec] = []
        for entry in data.get("models", []):
            specs.append(ModelSpec(
                id=entry["id"],
                provider=entry.get("provider", "stub"),
                model=entry.get("model", "stub"),
                capabilities=entry.get("capabilities", ["chat"]),
                privacy=entry.get("privacy", "cloud_ok"),
                usd_per_1k_tokens_est=float(entry.get("usd_per_1k_tokens_est", 0.0)),
                endpoint=entry.get("endpoint"),
            ))
        return cls(specs)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list(self) -> List[ModelSpec]:
        return list(self._models.values())

    def get(self, model_id: str) -> Optional[ModelSpec]:
        return self._models.get(model_id)

    def filter(
        self,
        capability: Optional[str] = None,
        privacy: Optional[str] = None,
        max_usd_est: Optional[float] = None,
        providers_allow: Optional[List[str]] = None,
        models_allow: Optional[List[str]] = None,
    ) -> List[ModelSpec]:
        """Return models matching all supplied constraints."""
        results = list(self._models.values())
        if capability:
            results = [m for m in results if m.matches_capability(capability)]
        if privacy:
            results = [m for m in results if m.matches_privacy(privacy)]
        if max_usd_est is not None:
            results = [m for m in results if m.usd_per_1k_tokens_est <= max_usd_est]
        if providers_allow:
            results = [m for m in results if m.provider in providers_allow]
        if models_allow:
            results = [m for m in results if m.id in models_allow]
        return results
