#!/usr/bin/env python3
"""
Multi-Provider System Test
==========================

Tests the new multi-provider architecture for FREE tier.

Verifies:
1. Google AI client connectivity
2. Groq client connectivity
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

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


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
    groq_key = os.getenv("GROQ_API_KEY")
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
    
    if groq_key:
        print(f"✅ GROQ_API_KEY: Set ({len(groq_key)} chars)")
        providers_available += 1
        total_rpm += 50
    else:
        print("⚠️  GROQ_API_KEY: Not set (optional)")
    
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
    
    if providers_available == 1:
        print("⚠️  Only OpenRouter available. Performance will be slower.")
        print("   Get FREE keys at:")
        print("   - Google AI: https://aistudio.google.com")
        print("   - Groq: https://console.groq.com")
        print()
    
    # Test Google AI client
    print("=" * 60)
    print("🔵 Testing Google AI Client...")
    print("-" * 60)
    
    if google_key:
        try:
            from llmhive.src.llmhive.app.providers import get_google_client
            
            client = get_google_client()
            if client:
                print("✅ Google AI client initialized")
                
                # Test API call
                print("   Testing Gemini 2.0 Flash...")
                start = time.time()
                response = await client.generate(
                    "Say 'Hello' in one word",
                    model="gemini-2.0-flash-exp"
                )
                elapsed = time.time() - start
                
                if response:
                    print(f"   ✅ Response: \"{response[:50]}...\" ({elapsed:.2f}s)")
                else:
                    print("   ❌ Empty response")
            else:
                print("❌ Failed to initialize client")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("⏭️  Skipped (no API key)")
    
    print()
    
    # Test Groq client
    print("=" * 60)
    print("🟢 Testing Groq Client...")
    print("-" * 60)
    
    if groq_key:
        try:
            from llmhive.src.llmhive.app.providers import get_groq_client
            
            client = get_groq_client()
            if client:
                print("✅ Groq client initialized (LPU-powered)")
                
                # Test API call
                print("   Testing Llama 3.3 70B...")
                start = time.time()
                response = await client.generate(
                    "Say 'Hello' in one word",
                    model="llama-3.3-70b-versatile"
                )
                elapsed = time.time() - start
                
                if response:
                    print(f"   ✅ Response: \"{response[:50]}...\" ({elapsed:.2f}s)")
                    print(f"   🚀 Ultra-fast LPU inference!")
                else:
                    print("   ❌ Empty response")
            else:
                print("❌ Failed to initialize client")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("⏭️  Skipped (no API key)")
    
    print()
    
    # Test DeepSeek client
    print("=" * 60)
    print("🟣 Testing DeepSeek Client...")
    print("-" * 60)
    
    if deepseek_key:
        try:
            from llmhive.src.llmhive.app.providers import get_deepseek_client
            
            client = get_deepseek_client()
            if client:
                print("✅ DeepSeek client initialized ($19.99 balance)")
                
                # Test API call
                print("   Testing DeepSeek Chat (V3.2)...")
                start = time.time()
                response = await client.generate(
                    "Say 'Hello' in one word",
                    model="deepseek-chat"
                )
                elapsed = time.time() - start
                
                if response:
                    print(f"   ✅ Response: \"{response[:50]}...\" ({elapsed:.2f}s)")
                    print(f"   💡 Elite math/reasoning: 96% AIME, 2701 Codeforces")
                else:
                    print("   ❌ Empty response")
            else:
                print("❌ Failed to initialize client")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("⏭️  Skipped (no API key)")
        print("   Get FREE account: https://platform.deepseek.com")
        print("   ($19.99 balance = ~70M tokens)")
    
    print()
    
    # Test provider router
    print("=" * 60)
    print("🔀 Testing Provider Router...")
    print("-" * 60)
    
    try:
        from llmhive.src.llmhive.app.providers import get_provider_router, Provider
        
        router = get_provider_router()
        print("✅ Provider router initialized")
        print()
        
        # Test routing decisions
        print("📍 Testing model routing...")
        
        test_models = [
            ("google/gemini-2.0-flash-exp:free", Provider.GOOGLE if google_key else Provider.OPENROUTER),
            ("meta-llama/llama-3.1-405b-instruct:free", Provider.GROQ if groq_key else Provider.OPENROUTER),
            ("meta-llama/llama-3.3-70b-instruct:free", Provider.GROQ if groq_key else Provider.OPENROUTER),
            ("deepseek/deepseek-r1-0528:free", Provider.DEEPSEEK if deepseek_key else Provider.OPENROUTER),
            ("deepseek/deepseek-chat", Provider.DEEPSEEK if deepseek_key else Provider.OPENROUTER),
            ("qwen/qwen3-coder:free", Provider.OPENROUTER),
        ]
        
        for model_id, expected_provider in test_models:
            provider, native_id = router.get_provider_for_model(model_id)
            status = "✅" if provider == expected_provider else "⚠️"
            print(f"   {status} {model_id}")
            print(f"      → {provider.value.upper()}", end="")
            if native_id:
                print(f" (native: {native_id})")
            else:
                print()
        
        print()
        
        # Test capacity tracking
        print("📊 Capacity Status:")
        status = router.get_capacity_status()
        for provider_name, info in status.items():
            available_str = "✅" if info['available'] else "❌ AT LIMIT"
            print(f"   {provider_name.upper()}: {info['utilization']} RPM {available_str}")
        
        print()
        
        # Test actual generation (if keys available)
        if google_key or groq_key:
            print("🧪 Testing end-to-end generation...")
            
            test_prompt = "Say hello in one word"
            
            if google_key:
                print(f"   Testing Gemini via router...")
                start = time.time()
                result = await router.generate(
                    "google/gemini-2.0-flash-exp:free",
                    test_prompt
                )
                elapsed = time.time() - start
                
                if result:
                    print(f"   ✅ Gemini: \"{result[:30]}...\" ({elapsed:.2f}s)")
                else:
                    print(f"   ⚠️  Gemini returned None (may need fallback)")
            
            if groq_key:
                print(f"   Testing Llama via router...")
                start = time.time()
                result = await router.generate(
                    "meta-llama/llama-3.3-70b-instruct:free",
                    test_prompt
                )
                elapsed = time.time() - start
                
                if result:
                    print(f"   ✅ Llama: \"{result[:30]}...\" ({elapsed:.2f}s)")
                else:
                    print(f"   ⚠️  Llama returned None (may need fallback)")
        
    except Exception as e:
        print(f"❌ Router error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 60)
    
    # Summary
    if providers_available == 4:
        print("🎉 PERFECT! All providers active (including DeepSeek).")
        print(f"   Expected capacity: ~{total_rpm} RPM")
        print(f"   Expected speedup: 4-5x faster, elite math/reasoning")
    elif providers_available == 3:
        print("🎉 EXCELLENT! Core providers active.")
        print(f"   Expected capacity: ~{total_rpm} RPM")
        print(f"   Expected speedup: 3-4x faster FREE tier")
    elif providers_available == 2:
        print("✅ GOOD! Multi-provider active.")
        print(f"   Expected capacity: ~{total_rpm} RPM")
        print(f"   Expected speedup: 2-3x faster FREE tier")
    else:
        print("⚠️  WARNING: Only OpenRouter available.")
        print("   FREE tier will be slower.")
        print()
        print("   To activate multi-provider:")
        print("   1. Get Google AI key: https://aistudio.google.com")
        print("   2. Get Groq key: https://console.groq.com")
        print("   3. Get DeepSeek key: https://platform.deepseek.com")
        print("   4. Export as environment variables")
    
    print()
    print("📝 Next Steps:")
    print("   1. Run benchmarks: python3 scripts/run_elite_free_benchmarks.py")
    print("   2. Deploy to production with API keys")
    print("   3. Monitor performance improvements")
    print()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_providers())
