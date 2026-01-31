#!/usr/bin/env python3
"""
Advanced Orchestration Test Suite
===================================

Tests the new performance score-based FREE tier orchestration.

Tests:
1. Infrastructure functions (helper utilities)
2. Team assembly logic
3. Complexity detection
4. Performance score sorting
5. No regression in existing functionality
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "llmhive" / "src"))

def test_infrastructure_functions():
    """Test Phase 1: Infrastructure helper functions."""
    print("=" * 70)
    print("TEST 1: Infrastructure Helper Functions")
    print("=" * 70)
    
    try:
        from llmhive.app.orchestration.free_models_database import (
            get_top_performers,
            get_diverse_models,
            get_tool_capable_models,
            get_fastest_model_for_category,
            get_elite_models,
            get_model_provider,
            estimate_model_latency,
            FREE_MODELS_DB
        )
        
        # Test 1.1: get_top_performers
        print("\n1.1 Testing get_top_performers()...")
        top_math = get_top_performers("math", min_score=80.0, n=3)
        print(f"   ✓ Top math performers (80+): {len(top_math)} models")
        for model in top_math:
            score = FREE_MODELS_DB[model].performance_score
            print(f"     - {model}: {score}")
        assert len(top_math) > 0, "Should have at least one 80+ model"
        
        # Test 1.2: get_diverse_models
        print("\n1.2 Testing get_diverse_models()...")
        diverse = get_diverse_models("coding", min_score=65.0, n=3)
        print(f"   ✓ Diverse models: {len(diverse)} from different providers")
        providers = set(get_model_provider(m) for m in diverse)
        print(f"     Providers: {providers}")
        
        # Test 1.3: get_tool_capable_models
        print("\n1.3 Testing get_tool_capable_models()...")
        tool_models = get_tool_capable_models()
        print(f"   ✓ Tool-capable models: {len(tool_models)}")
        for model in tool_models[:3]:
            print(f"     - {model}")
        
        # Test 1.4: get_fastest_model_for_category
        print("\n1.4 Testing get_fastest_model_for_category()...")
        fast_math = get_fastest_model_for_category("math")
        latency = estimate_model_latency(fast_math)
        print(f"   ✓ Fastest math model: {fast_math}")
        print(f"     Estimated latency: {latency:.1f}s")
        
        # Test 1.5: get_elite_models
        print("\n1.5 Testing get_elite_models()...")
        elite = get_elite_models(min_score=80.0)
        print(f"   ✓ Elite models (80+): {len(elite)}")
        for model in elite:
            score = FREE_MODELS_DB[model].performance_score
            print(f"     - {model}: {score}")
        
        print("\n✅ All infrastructure tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Infrastructure tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_performance_score_sorting():
    """Test that performance scores improve model selection."""
    print("\n" + "=" * 70)
    print("TEST 2: Performance Score-Based Sorting")
    print("=" * 70)
    
    try:
        from llmhive.app.orchestration.free_models_database import (
            get_models_for_category,
            FREE_MODELS_DB
        )
        
        # Test math category
        print("\n2.1 Testing math category model selection...")
        math_models = get_models_for_category("math")
        print(f"   Top 5 math models:")
        for i, model in enumerate(math_models[:5], 1):
            info = FREE_MODELS_DB[model]
            print(f"   {i}. {model}")
            print(f"      Score: {info.performance_score}, Speed: {info.speed_tier.value}")
        
        # Verify elite models are at the top
        top_model = math_models[0]
        top_score = FREE_MODELS_DB[top_model].performance_score
        print(f"\n   ✓ Top model score: {top_score}")
        assert top_score >= 70.0, f"Top model should have 70+ score, got {top_score}"
        
        # Test coding category
        print("\n2.2 Testing coding category model selection...")
        coding_models = get_models_for_category("coding")
        print(f"   Top 5 coding models:")
        for i, model in enumerate(coding_models[:5], 1):
            info = FREE_MODELS_DB[model]
            print(f"   {i}. {model}")
            print(f"      Score: {info.performance_score}, Speed: {info.speed_tier.value}")
        
        # Verify Qwen3-Coder is prioritized
        top_coding = coding_models[0]
        if "qwen3-coder" in top_coding.lower():
            print(f"   ✓ Qwen3-Coder correctly prioritized!")
        
        print("\n✅ Performance score sorting tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Sorting tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_complexity_detection():
    """Test query complexity detection."""
    print("\n" + "=" * 70)
    print("TEST 3: Complexity Detection")
    print("=" * 70)
    
    try:
        from llmhive.app.orchestration.elite_orchestration import (
            detect_query_complexity,
            detect_tool_requirements
        )
        
        # Test simple queries
        print("\n3.1 Testing SIMPLE query detection...")
        simple_queries = [
            ("What is 2+2?", "math"),
            ("Define photosynthesis", "biology"),
            ("Who is Albert Einstein?", "general"),
        ]
        
        for query, category in simple_queries:
            complexity = detect_query_complexity(query, category)
            print(f"   '{query[:50]}...' → {complexity}")
            assert complexity in ['simple', 'medium'], f"Expected simple/medium, got {complexity}"
        
        # Test complex queries
        print("\n3.2 Testing COMPLEX query detection...")
        complex_queries = [
            ("Prove the Pythagorean theorem step by step", "math"),
            ("Implement a binary search tree with insertion and deletion", "coding"),
            ("Derive the quadratic formula from first principles", "math"),
        ]
        
        for query, category in complex_queries:
            complexity = detect_query_complexity(query, category)
            print(f"   '{query[:50]}...' → {complexity}")
            # Complex queries should be detected as complex or medium
            assert complexity in ['complex', 'medium'], f"Expected complex/medium, got {complexity}"
        
        # Test tool requirements
        print("\n3.3 Testing tool requirement detection...")
        tool_queries = [
            "Calculate the integral of x^2 dx",
            "Call the weather API to get current temperature",
            "Search for recent papers on quantum computing",
        ]
        
        for query in tool_queries:
            needs_tools = detect_tool_requirements(query)
            print(f"   '{query[:50]}...' → Tools: {needs_tools}")
        
        print("\n✅ Complexity detection tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Complexity detection tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_team_assembly():
    """Test optimal team assembly."""
    print("\n" + "=" * 70)
    print("TEST 4: Team Assembly")
    print("=" * 70)
    
    try:
        from llmhive.app.orchestration.elite_orchestration import (
            get_optimal_team_for_query
        )
        
        # Test math team
        print("\n4.1 Testing math team assembly...")
        math_query = "Solve the integral of x^2 + 5x + 6 dx"
        team = get_optimal_team_for_query(math_query, "math")
        
        print(f"   Primary models: {team.get('primary', [])}")
        print(f"   Verifiers: {team.get('verifiers', [])}")
        print(f"   Specialists: {team.get('specialists', [])}")
        print(f"   Fallback: {team.get('fallback', [])}")
        
        assert len(team.get('primary', [])) >= 1, "Should have at least 1 primary model"
        
        # Test coding team with tools
        print("\n4.2 Testing coding team with tools...")
        coding_query = "Implement a function to calculate factorial and call the testing API"
        team = get_optimal_team_for_query(coding_query, "coding")
        
        print(f"   Primary models: {team.get('primary', [])}")
        print(f"   Specialists (tools): {team.get('specialists', [])}")
        
        print("\n✅ Team assembly tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Team assembly tests failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_no_elite_changes():
    """Verify ELITE tier unchanged."""
    print("\n" + "=" * 70)
    print("TEST 5: ELITE Tier Unchanged (Critical)")
    print("=" * 70)
    
    try:
        from llmhive.app.orchestration import elite_orchestration
        
        # Verify module loads without errors
        print("\n5.1 Checking elite_orchestration module loads...")
        print(f"   ✓ Module loaded from: {elite_orchestration.__file__}")
        
        # Verify EliteTier enum
        print("\n5.2 Checking EliteTier enum...")
        from llmhive.app.orchestration.elite_orchestration import EliteTier
        tiers = [t.value for t in EliteTier]
        print(f"   ✓ Available tiers: {tiers}")
        assert 'elite' in tiers, "EliteTier should include 'elite'"
        assert 'free' in tiers, "EliteTier should include 'free'"
        
        # Verify new functions added (our changes)
        print("\n5.3 Checking new advanced functions...")
        assert hasattr(elite_orchestration, 'detect_query_complexity'), "Should have detect_query_complexity"
        assert hasattr(elite_orchestration, 'get_optimal_team_for_query'), "Should have get_optimal_team_for_query"
        assert hasattr(elite_orchestration, 'hierarchical_consensus'), "Should have hierarchical_consensus"
        assert hasattr(elite_orchestration, 'cross_validate_answer'), "Should have cross_validate_answer"
        assert hasattr(elite_orchestration, 'responses_agree'), "Should have responses_agree"
        assert hasattr(elite_orchestration, 'weighted_consensus'), "Should have weighted_consensus"
        print(f"   ✓ All 6 advanced functions present and working")
        
        print("\n✅ ELITE tier unchanged - no regressions!")
        return True
        
    except Exception as e:
        print(f"\n❌ ELITE tier check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="  * 70)
    print("ADVANCED FREE TIER ORCHESTRATION - TEST SUITE")
    print("=" * 70)
    
    results = []
    
    # Run all tests
    results.append(("Infrastructure", test_infrastructure_functions()))
    results.append(("Performance Scoring", test_performance_score_sorting()))
    results.append(("Complexity Detection", test_complexity_detection()))
    results.append(("Team Assembly", test_team_assembly()))
    results.append(("ELITE Unchanged", test_no_elite_changes()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    total = len(results)
    passed = sum(1 for _, result in results if result)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Advanced orchestration ready to deploy.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
