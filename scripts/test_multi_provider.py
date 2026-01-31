#!/usr/bin/env python3
"""
Multi-Provider System Test
==========================

Tests the new multi-provider architecture for FREE tier.

Verifies:
1. Google AI client connectivity
2. DeepSeek client connectivity
3. Provider router functionality
4. Model routing logic
5. Capacity tracking

Usage:
    python3 scripts/test_multi_provider.py
"""

import os
import sys
import asyncio
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Load .env.local if it exists
env_file = Path(__file__).parent.parent / '.env.local'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Strip quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                # Only set if not already in environment
                if key not in os.environ:
                    os.environ[key] = value


async def test_providers():
    """Test all provider clients and routing."""
    
    print("🧪 Testing Multi-Provider System")
    print("=" * 60)
    print()
    
    # Check environment variables
    print("📋 Checking API Keys...")
    print("-" * 60)
    
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    google_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GEMINI_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    
    providers_available = 0
    total_rpm = 0
    
    if openrouter_key:
        print(f"✅ OPENROUTER_API_KEY: Set ({len(openrouter_key)} chars)")
        providers_available += 1
        total_rpm += 20
    else:
        print("❌ OPENROUTER_API_KEY: Not set")
    
    if google_key:
        key_name = "GOOGLE_AI_API_KEY" if os.getenv("GOOGLE_AI_API_KEY") else "GEMINI_API_KEY"
        print(f"✅ {key_name}: Set ({len(google_key)} chars)")
        providers_available += 1
        total_rpm += 15
    else:
        print("⚠️  GOOGLE_AI_API_KEY or GEMINI_API_KEY: Not set (optional)")
    
    if deepseek_key:
        print(f"✅ DEEPSEEK_API_KEY: Set ({len(deepseek_key)} chars)")
        providers_available += 1
        total_rpm += 30
    else:
        print("⚠️  DEEPSEEK_API_KEY: Not set (optional)")
    
    print()
    print(f"📊 Providers Available: {providers_available}/3")
    print(f"📊 Total Capacity: ~{total_rpm} RPM")
    print()
    
    # Test Google AI Client
    if google_key:
        print("=" * 60)
        print("🔵 Testing Google AI Client...")
        print("-" * 60)
        
        try:
            from llmhive.src.llmhive.app.providers.google_ai_client import get_google_client
            
            google_client = get_google_client()
            if google_client:
                print("✅ Google AI client initialized")
                print("   Testing Gemini 2.0 Flash...")
                
                start = time.time()
                result = await google_client.generate("Say 'Hello from Gemini!' in one sentence.", model="gemini-2.0-flash-exp")
                elapsed = time.time() - start
                
                if result:
                    print(f"✅ Response received in {elapsed:.2f}s")
                    print(f"   Preview: {result[:100]}...")
                else:
                    print("❌ No response received")
            else:
                print("⚠️  Google AI client not available (API key issue)")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()
    
    # Test DeepSeek Client
    if deepseek_key:
        print("=" * 60)
        print("🟡 Testing DeepSeek Client...")
        print("-" * 60)
        
        try:
            from llmhive.src.llmhive.app.providers.deepseek_client import get_deepseek_client
            
            deepseek_client = get_deepseek_client()
            if deepseek_client:
                print("✅ DeepSeek client initialized")
                print("   Testing DeepSeek Chat...")
                
                start = time.time()
                result = await deepseek_client.generate("What is 2+2? Answer in one sentence.", model="deepseek-chat")
                elapsed = time.time() - start
                
                if result:
                    print(f"✅ Response received in {elapsed:.2f}s")
                    print(f"   Preview: {result[:100]}...")
                else:
                    print("❌ No response received")
            else:
                print("⚠️  DeepSeek client not available (API key issue)")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()
    
    # Test Provider Router
    print("=" * 60)
    print("🎯 Testing Provider Router...")
    print("-" * 60)
    
    try:
        from llmhive.src.llmhive.app.providers.provider_router import get_provider_router, Provider
        
        router = get_provider_router()
        print("✅ Provider router initialized")
        print()
        
        # Test routing logic
        test_models = [
            "google/gemini-2.0-flash-exp:free",
            "deepseek/deepseek-r1-0528:free",
            "meta-llama/llama-3.1-405b-instruct:free",
            "qwen/qwen3-coder:free",
        ]
        
        print("📍 Model Routing:")
        print("-" * 60)
        for model in test_models:
            provider, native_id = router.get_provider_for_model(model)
            print(f"  {model}")
            print(f"    → {provider.value} (native: {native_id or 'same'})")
        
        print()
        
        # Test capacity tracking
        print("💾 Capacity Status:")
        print("-" * 60)
        status = router.get_capacity_status()
        for provider_name, info in status.items():
            available_icon = "✅" if info["available"] else "⚠️ "
            print(f"  {available_icon} {provider_name}: {info['utilization']} RPM")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()
    print("=" * 60)
    print("✅ Multi-Provider Test Complete!")
    print(f"   {providers_available} providers configured")
    print(f"   ~{total_rpm} RPM total capacity")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_providers())
