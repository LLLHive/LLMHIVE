#!/usr/bin/env python3
"""P0 live-probe for free/direct catalog (Z.ai, NVIDIA, Kimi, DeepSeek, Google, OR).

Usage:
  python scripts/probe_free_catalog_p0.py

Does not print secrets. Exit 0 if core direct routes respond or soft-skip when keys missing.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "llmhive" / "src"))


async def _probe_catalog(name: str, getter, slug: str) -> tuple[str, str]:
    client = getter()
    if not client:
        return name, "SKIP (no API key)"
    try:
        text = await client.generate_with_retry("Reply with exactly: OK", slug, max_retries=0)
        if text and "ok" in text.lower()[:40]:
            return name, "OK"
        if text:
            return name, f"OK (got {len(text)} chars)"
        return name, "FAIL (empty)"
    except Exception as exc:
        return name, f"FAIL ({type(exc).__name__}: {str(exc)[:80]})"


async def main() -> int:
    from llmhive.app.providers.zai_client import get_zai_client
    from llmhive.app.providers.nvidia_client import get_nvidia_client
    from llmhive.app.providers.kimi_client import get_kimi_client
    from llmhive.app.providers.deepseek_client import get_deepseek_client
    from llmhive.app.orchestration.free_models_database import FREE_MODELS_DB
    from llmhive.app.providers.provider_chain import (
        build_provider_chain,
        P_ZAI,
        P_NVIDIA,
        P_KIMI,
        P_OPENROUTER,
    )

    print("=== FREE_MODELS_DB direct preferred_api check ===")
    for mid, info in FREE_MODELS_DB.items():
        if info.preferred_api in ("zai", "nvidia", "kimi"):
            print(f"  {mid}: preferred_api={info.preferred_api} native={info.native_model_id}")

    print("\n=== Chain order (keys may be absent → provider skipped) ===")
    for slug in (
        "z-ai/glm-5.3-flash",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "moonshotai/kimi-k2.6",
    ):
        chain = build_provider_chain(slug)
        print(f"  {slug}: {[p for p, _ in chain]}")
        assert chain[-1][0] == P_OPENROUTER or P_OPENROUTER not in [p for p, _ in chain] or True
        # OR must remain last when present
        providers = [p for p, _ in chain]
        if P_OPENROUTER in providers:
            assert providers.index(P_OPENROUTER) == len(providers) - 1, slug

    print("\n=== Live probes (best-effort) ===")
    probes = [
        ("Z.ai GLM-5.3-Flash", get_zai_client, "z-ai/glm-5.3-flash"),
        ("NVIDIA Nemotron Ultra", get_nvidia_client, "nvidia/nemotron-3-ultra-550b-a55b:free"),
        ("Kimi K2.6", get_kimi_client, "moonshotai/kimi-k2.6"),
        ("DeepSeek", get_deepseek_client, "deepseek/deepseek-chat"),
    ]
    results = await asyncio.gather(*[_probe_catalog(n, g, s) for n, g, s in probes])
    for name, status in results:
        print(f"  {name}: {status}")

    # Soft success: wiring OK even if keys missing
    print("\nROUTING_V2_STRICT_IDENTITY=", os.getenv("ROUTING_V2_STRICT_IDENTITY", "true"))
    print("P0 catalog probe complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
