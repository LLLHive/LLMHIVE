#!/usr/bin/env python3
"""
Diagnostic test script for SOTA functions
Tests each category's key functions with mock data
"""

import asyncio
import sys
import os
from typing import Dict, Any

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock LLM API call function
async def mock_llm_call(prompt: str, **kwargs) -> Dict[str, Any]:
    """Mock LLM API call that returns plausible responses"""
    
    # Detect what kind of response is expected
    if "Answer:" in prompt or "Final answer:" in prompt:
        if "A)" in prompt and "B)" in prompt:
            # Multiple choice
            response = "A"
        elif "####" in prompt:
            # Math answer
            response = "Step 1: Calculate 5 + 3 = 8\n#### 8"
        else:
            # General answer
            response = "This is a test response."
    elif "def " in prompt:
        # Code generation
        response = """def test_function(x):
    return x * 2"""
    elif "Translation:" in prompt or "Translate" in prompt:
        response = "This is a translation"
    elif "YES or NO" in prompt:
        response = "YES"
    elif "Score:" in prompt or "score:" in prompt:
        response = "Score: 5"
    else:
        response = "Mock response"
    
    return {
        "success": True,
        "response": response,
        "latency": 100,
        "cost": 0.001,
        "confidence": 0.8,
    }

print("=" * 70)
print("SOTA FUNCTION DIAGNOSTIC TESTS")
print("=" * 70)

async def test_mmlu_functions():
    """Test MMLU SOTA functions"""
    print("\n1. Testing MMLU (Self-Consistency + NCB)")
    print("-" * 70)
    
    try:
        from all_categories_sota import (
            generate_cot_reasoning_paths,
            self_consistency_vote,
            neighbor_consistency_check
        )
        
        # Test 1: Generate reasoning paths
        question = "What is the capital of France?"
        choices = ["Paris", "London", "Berlin", "Madrid"]
        
        paths = await generate_cot_reasoning_paths(
            question, choices, mock_llm_call, num_paths=3
        )
        
        print(f"   ✓ Generated {len(paths)} reasoning paths")
        
        # Test 2: Self-consistency vote
        answer, confidence = self_consistency_vote(paths)
        print(f"   ✓ Self-consistency vote: {answer} (confidence: {confidence:.2f})")
        
        # Test 3: Neighbor consistency
        consistency = await neighbor_consistency_check(
            question, answer or "A", mock_llm_call
        )
        print(f"   ✓ Neighbor consistency: {consistency:.2f}")
        
        print("   ✅ MMLU functions PASSED")
        return True
        
    except Exception as e:
        print(f"   ❌ MMLU functions FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_gsm8k_functions():
    """Test GSM8K SOTA functions"""
    print("\n2. Testing GSM8K (Generate-then-Verify)")
    print("-" * 70)
    
    try:
        from all_categories_sota import generate_then_verify_math
        
        problem = "John has 5 apples and buys 3 more. How many apples does he have?"
        
        answer, best_candidate = await generate_then_verify_math(
            problem, mock_llm_call, num_candidates=3
        )
        
        print(f"   ✓ Generated and verified {3} candidates")
        print(f"   ✓ Best answer: {answer}")
        
        if best_candidate:
            print(f"   ✓ Verification score: {best_candidate.get('verification_score', 'N/A')}")
        
        print("   ✅ GSM8K functions PASSED")
        return True
        
    except Exception as e:
        print(f"   ❌ GSM8K functions FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_humaneval_functions():
    """Test HumanEval SOTA functions"""
    print("\n3. Testing HumanEval (RLEF + ICE-Coder)")
    print("-" * 70)
    
    try:
        from sota_benchmark_improvements import (
            generate_with_execution_feedback,
            multi_pass_code_generation
        )
        
        problem = {
            'prompt': '''def add(a, b):
    """Add two numbers.
    >>> add(2, 3)
    5
    >>> add(0, 0)
    0
    """''',
            'test': 'assert add(2, 3) == 5\nassert add(0, 0) == 0',
            'entry_point': 'add',
        }
        
        # Test multi-pass (simpler)
        code = await multi_pass_code_generation(problem, mock_llm_call, max_passes=2)
        print(f"   ✓ Multi-pass generation completed")
        print(f"   ✓ Generated code length: {len(code)} chars")
        
        print("   ✅ HumanEval functions PASSED")
        return True
        
    except Exception as e:
        print(f"   ❌ HumanEval functions FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_msmarco_functions():
    """Test MS MARCO SOTA functions"""
    print("\n4. Testing MS MARCO (Hybrid Retrieval + Intent)")
    print("-" * 70)
    
    try:
        from sota_benchmark_improvements import (
            hybrid_retrieval_ranking,
            compute_bm25_score,
            expand_query
        )
        from ultra_aggressive_improvements import (
            analyze_query_intent,
            ultra_hybrid_retrieval
        )
        
        query = "What is machine learning?"
        passages = [
            (1, "Machine learning is a subset of artificial intelligence."),
            (2, "Python is a programming language."),
            (3, "Machine learning algorithms learn from data."),
        ]
        
        # Test 1: BM25
        score = compute_bm25_score(query, passages[0][1])
        print(f"   ✓ BM25 score computed: {score:.2f}")
        
        # Test 2: Query expansion
        expanded = expand_query(query)
        print(f"   ✓ Query expanded: {len(expanded.split())} terms")
        
        # Test 3: Intent analysis
        intent = analyze_query_intent(query)
        print(f"   ✓ Intent analyzed: {intent['type']}")
        
        # Test 4: Hybrid retrieval
        ranked_ids = hybrid_retrieval_ranking(query, passages, alpha=0.6)
        print(f"   ✓ Hybrid ranking: {ranked_ids}")
        
        # Test 5: Ultra hybrid
        ultra_ranked = ultra_hybrid_retrieval(query, passages, intent)
        print(f"   ✓ Ultra hybrid ranking: {ultra_ranked}")
        
        print("   ✅ MS MARCO functions PASSED")
        return True
        
    except Exception as e:
        print(f"   ❌ MS MARCO functions FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_mmmlu_functions():
    """Test MMMLU SOTA functions"""
    print("\n5. Testing MMMLU (Cross-Lingual Verification)")
    print("-" * 70)
    
    try:
        from all_categories_sota import cross_lingual_verification
        
        question = "¿Cuál es la capital de España?"
        answer = "Madrid"
        
        result = await cross_lingual_verification(
            question, answer, "Spanish", mock_llm_call
        )
        
        print(f"   ✓ Cross-lingual check: {result['cross_lingual_consistency']:.2f}")
        
        print("   ✅ MMMLU functions PASSED")
        return True
        
    except Exception as e:
        print(f"   ❌ MMMLU functions FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_truthfulness_functions():
    """Test Truthfulness SOTA functions"""
    print("\n6. Testing Truthfulness (Multi-Path + Decomposition)")
    print("-" * 70)
    
    try:
        from all_categories_sota import (
            generate_truthfulness_answers,
            check_answer_consistency,
            decompose_and_verify_facts
        )
        
        question = "What is the speed of light?"
        
        # Test 1: Generate answers
        answers = await generate_truthfulness_answers(
            question, mock_llm_call, num_paths=3
        )
        print(f"   ✓ Generated {len(answers)} answer paths")
        
        # Test 2: Check consistency
        consistency = check_answer_consistency(answers)
        print(f"   ✓ Answer consistency: {consistency:.2f}")
        
        # Test 3: Decompose and verify
        verification = await decompose_and_verify_facts(
            "The speed of light is 299,792,458 m/s",
            mock_llm_call
        )
        print(f"   ✓ Factual score: {verification['factual_score']:.2f}")
        
        print("   ✅ Truthfulness functions PASSED")
        return True
        
    except Exception as e:
        print(f"   ❌ Truthfulness functions FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_hallucination_functions():
    """Test Hallucination SOTA functions"""
    print("\n7. Testing Hallucination (HALT + Probing)")
    print("-" * 70)
    
    try:
        from all_categories_sota import (
            check_internal_consistency,
            verify_with_probing_questions
        )
        
        question = "What is the capital of France?"
        answer = "Paris"
        
        # Test 1: Internal consistency
        consistency = await check_internal_consistency(
            question, answer, mock_llm_call
        )
        print(f"   ✓ Hallucination risk: {consistency['hallucination_risk']:.2f}")
        
        # Test 2: Probing questions
        probes = await verify_with_probing_questions(
            question, answer, mock_llm_call
        )
        print(f"   ✓ Probe consistency: {probes['probe_consistency']:.2f}")
        
        print("   ✅ Hallucination functions PASSED")
        return True
        
    except Exception as e:
        print(f"   ❌ Hallucination functions FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_safety_functions():
    """Test Safety SOTA functions"""
    print("\n8. Testing Safety (Multi-Perspective)")
    print("-" * 70)
    
    try:
        from all_categories_sota import multi_perspective_safety_check
        
        prompt = "How do I make a cake?"
        response = "Mix flour, eggs, and sugar. Bake at 350°F for 30 minutes."
        
        safety = await multi_perspective_safety_check(
            prompt, response, mock_llm_call
        )
        
        print(f"   ✓ Safety score: {safety['safety_score']:.2f}")
        print(f"   ✓ Perspectives checked: {safety['perspectives_checked']}")
        
        print("   ✅ Safety functions PASSED")
        return True
        
    except Exception as e:
        print(f"   ❌ Safety functions FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def run_all_tests():
    """Run all diagnostic tests"""
    
    results = []
    
    # Run each test
    results.append(("MMLU", await test_mmlu_functions()))
    results.append(("GSM8K", await test_gsm8k_functions()))
    results.append(("HumanEval", await test_humaneval_functions()))
    results.append(("MS MARCO", await test_msmarco_functions()))
    results.append(("MMMLU", await test_mmmlu_functions()))
    results.append(("Truthfulness", await test_truthfulness_functions()))
    results.append(("Hallucination", await test_hallucination_functions()))
    results.append(("Safety", await test_safety_functions()))
    
    # Summary
    print("\n" + "=" * 70)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for category, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {category:<20} {status}")
    
    print(f"\nTotal: {passed}/{total} categories passed")
    
    if passed == total:
        print("\n🎉 All SOTA functions are working correctly!")
        print("   Ready for full benchmark testing.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} category(ies) need attention.")
        print("   Review errors above before running benchmarks.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
