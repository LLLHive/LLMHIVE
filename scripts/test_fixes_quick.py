#!/usr/bin/env python3
"""
Quick test of the 3 category fixes
Tests just 2 questions from each problem category
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.run_category_benchmarks import (
    evaluate_tool_use,
    evaluate_long_context,
    evaluate_coding,
    SAMPLE_SIZES
)

async def main():
    print("="*70)
    print("QUICK TEST OF 3 CATEGORY FIXES")
    print("="*70)
    print("\nTesting with reduced sample sizes:")
    print("- Tool Use: 6 questions (was 30)")
    print("- Long Context: 3 questions (was 20)")
    print("- Coding: 5 questions (was 50)")
    print("\n" + "="*70 + "\n")
    
    # Temporarily reduce sample sizes
    original_sizes = {
        "tool_use": SAMPLE_SIZES["tool_use"],
        "long_context": SAMPLE_SIZES["long_context"],
        "coding": SAMPLE_SIZES["coding"],
    }
    
    SAMPLE_SIZES["tool_use"] = 6
    SAMPLE_SIZES["long_context"] = 3
    SAMPLE_SIZES["coding"] = 5
    
    try:
        results = []
        
        # Test Tool Use
        print("Testing Tool Use fixes...")
        tool_result = await evaluate_tool_use("elite")
        results.append(tool_result)
        print(f"\n✅ Tool Use: {tool_result.get('accuracy', 0)}% ({tool_result.get('correct', 0)}/{tool_result.get('sample_size', 0)})")
        print(f"   Errors: {tool_result.get('errors', 0)}")
        print(f"   Cost: ${tool_result.get('total_cost', 0):.4f}")
        
        # Test Long Context
        print("\nTesting Long Context fixes...")
        long_result = await evaluate_long_context("elite")
        results.append(long_result)
        print(f"\n✅ Long Context: {long_result.get('accuracy', 0)}% ({long_result.get('correct', 0)}/{long_result.get('sample_size', 0)})")
        print(f"   Errors: {long_result.get('errors', 0)}")
        print(f"   Cost: ${long_result.get('total_cost', 0):.4f}")
        
        # Test Coding
        print("\nTesting Coding fixes...")
        coding_result = await evaluate_coding("elite")
        results.append(coding_result)
        print(f"\n✅ Coding: {coding_result.get('accuracy', 0)}% ({coding_result.get('correct', 0)}/{coding_result.get('sample_size', 0)})")
        print(f"   Errors: {coding_result.get('errors', 0)}")
        print(f"   Cost: ${coding_result.get('total_cost', 0):.4f}")
        
        # Summary
        print("\n" + "="*70)
        print("QUICK TEST SUMMARY")
        print("="*70)
        
        total_correct = sum(r.get('correct', 0) for r in results)
        total_sample = sum(r.get('sample_size', 0) for r in results)
        total_errors = sum(r.get('errors', 0) for r in results)
        total_cost = sum(r.get('total_cost', 0) for r in results)
        
        print(f"\nTotal Accuracy: {(total_correct/total_sample*100) if total_sample > 0 else 0:.1f}%")
        print(f"Total Correct: {total_correct}/{total_sample}")
        print(f"Total Errors: {total_errors}")
        print(f"Total Cost: ${total_cost:.4f}")
        
        print("\nResults by Category:")
        for result in results:
            category = result.get('category', 'Unknown')
            accuracy = result.get('accuracy', 0)
            status = "✅" if accuracy > 0 else "⚠️"
            print(f"  {status} {category}: {accuracy}%")
        
        print("\n" + "="*70)
        if total_errors == 0 and total_correct > 0:
            print("✅ QUICK TEST PASSED - Fixes are working!")
            print("\nRecommendation: Run full benchmark to see complete results")
        elif total_errors > 0:
            print("⚠️  Some errors occurred - review logs above")
        else:
            print("⚠️  No successes - review test implementation")
        
    finally:
        # Restore original sizes
        SAMPLE_SIZES.update(original_sizes)

if __name__ == "__main__":
    asyncio.run(main())
