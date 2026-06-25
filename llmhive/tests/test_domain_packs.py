"""Industry domain pack wiring: API enum, presets, prompts, and task routing."""
from __future__ import annotations

import pytest

from llmhive.app.domain_presets import (
    DOMAIN_PRESETS,
    filter_models_by_domain,
    get_domain_preset,
    normalize_domain_pack,
)
from llmhive.app.models.orchestration import ChatRequest, DomainPack, ModelTier
from llmhive.app.services.orchestrator_adapter import _resolve_task_type_for_domain_pack
from llmhive.app.services.reasoning_prompts import (
    get_domain_instruction_prefix,
    get_category_prompt,
)

ALL_PACKS = {pack.value for pack in DomainPack}


class TestDomainPackApi:
    def test_all_packs_accepted_by_chat_request(self):
        for pack in DomainPack:
            req = ChatRequest(prompt="Hello", domain_pack=pack)
            assert req.domain_pack == pack

    def test_enum_matches_product_surface(self):
        assert ALL_PACKS == {
            "default",
            "medical",
            "legal",
            "marketing",
            "coding",
            "research",
            "finance",
            "education",
            "real_estate",
        }


class TestDomainPresets:
    @pytest.mark.parametrize(
        "pack",
        ["medical", "legal", "marketing", "coding", "research", "finance", "education", "real_estate"],
    )
    def test_industry_pack_has_preset(self, pack: str):
        assert get_domain_preset(pack) is not None
        assert pack in DOMAIN_PRESETS

    def test_default_maps_to_no_specialization(self):
        assert normalize_domain_pack("default") is None
        assert get_domain_preset("default") is not None  # alias -> general


class TestDomainPrompts:
    @pytest.mark.parametrize(
        "pack,needle",
        [
            ("medical", "medical"),
            ("legal", "legal"),
            ("marketing", "marketing"),
            ("coding", "software"),
            ("research", "research"),
            ("finance", "finance"),
            ("education", "education"),
            ("real_estate", "real estate"),
        ],
    )
    def test_domain_instruction_prefix(self, pack: str, needle: str):
        prefix = get_domain_instruction_prefix(pack)
        assert needle in prefix.lower()

    def test_default_pack_has_no_prefix(self):
        assert get_domain_instruction_prefix("default") == ""

    def test_category_prompt_includes_pack_prefix(self):
        out = get_category_prompt("general", "What is aspirin?", domain_pack="medical")
        assert "medical" in out.lower()
        assert "aspirin" in out


class TestDomainPackTaskRouting:
    def test_medical_pack_routes_generic_query(self):
        assert _resolve_task_type_for_domain_pack("general", "medical") == "health_medical"

    def test_legal_pack_routes_generic_query(self):
        assert _resolve_task_type_for_domain_pack("general", "legal") == "legal_analysis"

    def test_finance_pack_routes_generic_query(self):
        assert _resolve_task_type_for_domain_pack("general", "finance") == "financial_analysis"

    def test_coding_pack_routes_generic_query(self):
        assert _resolve_task_type_for_domain_pack("general", "coding") == "code_generation"

    def test_default_pack_unchanged(self):
        assert _resolve_task_type_for_domain_pack("general", "default") == "general"

    def test_specific_keyword_task_not_overridden(self):
        assert _resolve_task_type_for_domain_pack("code_generation", "medical") == "code_generation"


class TestDomainPackDoesNotBypassPolicy:
    """Industry packs tune prompts/routing only — never billing, tier, or model eligibility."""

    @pytest.mark.parametrize("pack", list(DomainPack))
    def test_pack_independent_of_request_tier(self, pack: DomainPack):
        free_req = ChatRequest(
            prompt="Hello",
            domain_pack=pack,
            tier=ModelTier.free,
        )
        elite_req = ChatRequest(
            prompt="Hello",
            domain_pack=pack,
            tier=ModelTier.elite,
        )
        assert free_req.domain_pack == pack
        assert elite_req.domain_pack == pack
        assert free_req.tier == ModelTier.free
        assert elite_req.tier == ModelTier.elite

    @pytest.mark.parametrize(
        "pack",
        ["medical", "legal", "finance", "marketing", "coding", "real_estate"],
    )
    def test_filter_models_by_domain_never_adds_models(self, pack: str):
        """Pack prioritization may reorder but must not unlock models outside the tier set."""
        allowed = ["gpt-4o-mini", "glm-4-flash", "deepseek-chat"]
        filtered = filter_models_by_domain(allowed, pack)
        assert set(filtered) == set(allowed)
        assert len(filtered) == len(allowed)

    def test_billing_layer_has_no_domain_pack_hooks(self):
        import llmhive.app.billing.access_guard as access_guard
        import llmhive.app.billing.query_quota as query_quota
        import llmhive.app.billing.spend_guard as spend_guard

        for mod in (access_guard, query_quota, spend_guard):
            src = open(mod.__file__, encoding="utf-8").read()
            assert "domain_pack" not in src
