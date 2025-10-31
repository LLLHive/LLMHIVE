#!/usr/bin/env python3
"""Verify API key connectivity for all configured providers.

This script tests connectivity to OpenAI, Grok, Anthropic, Gemini, DeepSeek,
and Manus providers by attempting to make a simple API call with each
configured provider. It helps diagnose connectivity issues and verify
that API keys are working correctly.

Usage:
    python verify_connectivity.py

Environment Variables:
    OPENAI_API_KEY - OpenAI API key
    GROK_API_KEY - xAI Grok API key
    ANTHROPIC_API_KEY - Anthropic Claude API key
    GEMINI_API_KEY - Google Gemini API key
    DEEPSEEK_API_KEY - DeepSeek API key
    MANUS_API_KEY - Manus API key
    MANUS_BASE_URL - (Optional) Custom Manus base URL
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from llmhive.app.services.base import ProviderNotConfiguredError
from llmhive.app.services.openai_provider import OpenAIProvider
from llmhive.app.services.grok_provider import GrokProvider
from llmhive.app.services.anthropic_provider import AnthropicProvider
from llmhive.providers.gemini import GeminiProvider
from llmhive.app.services.deepseek_provider import DeepSeekProvider
from llmhive.app.services.manus_provider import ManusProvider


async def test_provider(provider_class, api_key, provider_name, model, **kwargs):
    """Test a provider by making a simple API call."""
    print(f"\n{'='*60}")
    print(f"Testing {provider_name}...")
    print(f"{'='*60}")
    
    if not api_key:
        print(f"❌ SKIP: No API key found for {provider_name}")
        print(f"   Set environment variable for {provider_name}")
        return None  # Return None for skipped
    
    try:
        # Initialize provider
        print(f"✓ API key found for {provider_name}")
        provider = provider_class(api_key=api_key, **kwargs)
        print(f"✓ Provider initialized successfully")
        
        # Make a simple test call
        print(f"✓ Making test API call with model: {model}")
        result = await provider.complete("Say 'Connection successful' if you can read this.", model=model)
        
        # Check response
        if result and result.content:
            print(f"✓ API call successful!")
            print(f"  Response: {result.content[:100]}...")
            if result.tokens:
                print(f"  Tokens used: {result.tokens}")
            return True
        else:
            print(f"❌ API call returned empty response")
            return False
            
    except ProviderNotConfiguredError as e:
        print(f"❌ Configuration error: {e}")
        return False
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return False


async def main():
    """Test all configured providers."""
    print("\n" + "="*60)
    print("LLMHive Provider Connectivity Verification")
    print("="*60)
    
    results = {}
    
    # Test OpenAI
    results['openai'] = await test_provider(
        OpenAIProvider,
        os.getenv("OPENAI_API_KEY"),
        "OpenAI",
        "gpt-3.5-turbo"
    )
    
    # Test Grok
    results['grok'] = await test_provider(
        GrokProvider,
        os.getenv("GROK_API_KEY"),
        "Grok (xAI)",
        "grok-beta"
    )
    
    # Test Anthropic
    results['anthropic'] = await test_provider(
        AnthropicProvider,
        os.getenv("ANTHROPIC_API_KEY"),
        "Anthropic (Claude)",
        "claude-3-haiku-20240307"
    )
    
    # Test Gemini
    results['gemini'] = await test_provider(
        GeminiProvider,
        os.getenv("GEMINI_API_KEY"),
        "Google Gemini",
        "gemini-pro"
    )
    
    # Test DeepSeek
    results['deepseek'] = await test_provider(
        DeepSeekProvider,
        os.getenv("DEEPSEEK_API_KEY"),
        "DeepSeek",
        "deepseek-chat"
    )
    
    # Test Manus
    manus_base_url = os.getenv("MANUS_BASE_URL")
    manus_kwargs = {"base_url": manus_base_url} if manus_base_url else {}
    results['manus'] = await test_provider(
        ManusProvider,
        os.getenv("MANUS_API_KEY"),
        "Manus",
        "manus-default",
        **manus_kwargs
    )
    
    # Print summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    successful = [name for name, success in results.items() if success]
    failed = [name for name, success in results.items() if success is False]
    skipped = [name for name, success in results.items() if success is None]
    
    print(f"\n✓ Successful: {len(successful)}")
    for name in successful:
        print(f"  - {name}")
    
    if failed:
        print(f"\n❌ Failed: {len(failed)}")
        for name in failed:
            print(f"  - {name}")
    
    total_configured = len(successful) + len(failed)
    if total_configured == 0:
        print("\n⚠️  WARNING: No providers are configured!")
        print("   The system will fall back to stub responses.")
        print("\n   To configure providers, set environment variables:")
        print("   - OPENAI_API_KEY=sk-...")
        print("   - GROK_API_KEY=xai-...")
        print("   - ANTHROPIC_API_KEY=sk-ant-...")
        print("   - GEMINI_API_KEY=...")
        print("   - DEEPSEEK_API_KEY=...")
        print("   - MANUS_API_KEY=...")
    elif failed:
        print("\n⚠️  Some providers failed connectivity tests.")
        print("   Check your API keys and network connectivity.")
        sys.exit(1)
    else:
        print(f"\n✅ All {total_configured} configured provider(s) are working correctly!")
        print("   No stub responses will be returned for these providers.")
    
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nVerification cancelled by user.")
        sys.exit(1)
