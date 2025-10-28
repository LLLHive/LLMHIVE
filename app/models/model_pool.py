"""ModelPool implementation that exposes model metadata and helpers."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from app.config import settings

from .language_model import LanguageModel
from .summarizer import Summarizer
from .tavily_client import TavilyClient
from .stub_language_model import StubLanguageModel

try:  # PyYAML is optional in some deployment environments
    import yaml  # type: ignore
except Exception:  # pragma: no cover - fallback handled below
    yaml = None  # type: ignore


@dataclass
class ModelProfile:
    """Metadata describing an available model."""

    model_id: str
    provider: str
    strengths: List[str] = field(default_factory=list)
    cost_per_token: float = 0.0
    context_window: Optional[int] = None
    metadata: Dict[str, object] = field(default_factory=dict)


class ModelPool:
    """Central registry for tools, agents, and model metadata."""

    def __init__(self) -> None:
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

        self.tools: Dict[str, object] = {}
        self.agents: Dict[str, object] = {}
        self.llms: Dict[str, LanguageModel] = {}
        self._models: Dict[str, ModelProfile] = {}

        self._register_default_integrations()
        self._load_models_into_pool()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_tool(self, tool_name: str):
        return self.tools.get(tool_name)

    def get_agent(self, agent_name: str):
        return self.agents.get(agent_name)

    def get_llm(self, llm_name: str):
        return self.llms.get(llm_name)

    def get_model_profile(self, model_id: str) -> Optional[ModelProfile]:
        """Return the metadata profile for the requested model, if present."""

        return self._models.get(model_id)

    def list_models(self) -> List[ModelProfile]:
        """Return all registered model profiles."""

        return list(self._models.values())

    def register_model(self, profile: ModelProfile) -> None:
        """Register (or replace) a model profile in the pool."""

        self._models[profile.model_id] = profile

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _register_default_integrations(self) -> None:
        if self.tavily_api_key:
            tavily_client = TavilyClient(self.tavily_api_key)
            self.tools["tavily"] = tavily_client
            self.agents["tavily"] = tavily_client

        if self.openai_api_key:
            general_llm = LanguageModel(self.openai_api_key, model="gpt-4o")
        else:
            general_llm = StubLanguageModel(model="gpt-4o")

        # Always register the general LLM so the planner has a dependency even
        # when we fall back to the stub implementation.
        self.llms["gpt-4o"] = general_llm
        self.agents["summarizer"] = Summarizer(llm=general_llm)

    def _load_models_into_pool(self) -> None:
        for profile in self._load_model_config():
            self.register_model(profile)

    def _load_model_config(self) -> List[ModelProfile]:
        """Load model metadata from the configured YAML/JSON file."""

        config_path = self._resolve_config_path(settings.MODEL_CONFIG_PATH)
        if not config_path or not config_path.exists():
            return self._default_models()

        try:
            raw_text = config_path.read_text(encoding="utf-8")
            data = self._parse_model_config(raw_text, config_path.suffix)
            models = data.get("models", []) if isinstance(data, dict) else []
            return [self._profile_from_dict(entry) for entry in models if isinstance(entry, dict)] or self._default_models()
        except Exception:
            # Any parsing error should fall back to known-safe defaults so the API keeps working.
            return self._default_models()

    def _parse_model_config(self, raw_text: str, suffix: str):
        if suffix.lower() in {".yaml", ".yml"} and yaml:
            return yaml.safe_load(raw_text)
        if suffix.lower() == ".json":
            return json.loads(raw_text)
        if yaml:  # Attempt YAML parse even without extension hint.
            return yaml.safe_load(raw_text)
        # Fallback: try JSON before giving up.
        return json.loads(raw_text)

    def _profile_from_dict(self, data: Dict[str, object]) -> ModelProfile:
        strengths_value = data.get("strengths", [])
        if isinstance(strengths_value, (list, tuple, set)):
            strengths = [str(item) for item in strengths_value]
        elif isinstance(strengths_value, str):
            strengths = [strengths_value]
        else:
            strengths = []

        cost_value = data.get("cost_per_token", 0.0)
        try:
            cost_per_token = float(cost_value)
        except (TypeError, ValueError):
            cost_per_token = 0.0

        metadata = {
            k: v
            for k, v in data.items()
            if k
            not in {"model_id", "provider", "strengths", "cost_per_token", "context_window"}
        }

        return ModelProfile(
            model_id=str(data.get("model_id", "")),
            provider=str(data.get("provider", "stub")),
            strengths=strengths,
            cost_per_token=cost_per_token,
            context_window=self._safe_int(data.get("context_window")),
            metadata=metadata,
        )

    def _default_models(self) -> List[ModelProfile]:
        return [
            ModelProfile(
                model_id="gpt-4-turbo",
                provider="openai",
                strengths=["reasoning", "coding", "general"],
                context_window=128000,
                cost_per_token=0.01,
            ),
            ModelProfile(
                model_id="gpt-4",
                provider="openai",
                strengths=["reasoning", "analysis"],
                context_window=8192,
                cost_per_token=0.03,
            ),
            ModelProfile(
                model_id="claude-3-opus",
                provider="anthropic",
                strengths=["writing", "long-context", "analysis"],
                context_window=200000,
                cost_per_token=0.025,
            ),
            ModelProfile(
                model_id="claude-3-sonnet",
                provider="anthropic",
                strengths=["general", "writing"],
                context_window=200000,
                cost_per_token=0.005,
            ),
        ]

    def _resolve_config_path(self, configured_path: str) -> Optional[Path]:
        if not configured_path:
            return None

        path = Path(configured_path)
        if path.exists():
            return path

        base_dir = Path(__file__).resolve().parents[2]
        candidate = base_dir / configured_path
        if candidate.exists():
            return candidate
        return None

    def _safe_int(self, value: object) -> Optional[int]:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None


model_pool = ModelPool()
