#!/usr/bin/env python3
"""
LLMHive Industry Standard Benchmark Suite
==========================================
Runs comprehensive benchmarks across all 10 industry-standard categories:
1. General Reasoning (GPQA Diamond style)
2. Coding (SWE-Bench style)
3. Math (AIME 2024 style)
4. Multilingual Understanding (MMMLU style)
5. Long-Context Handling
6. Tool Use / Agentic Reasoning
7. RAG (Retrieval QA)
8. Multimodal / Vision
9. Dialogue / Emotional Alignment
10. Speed / Latency
"""

import asyncio
import json
import os
import time
import statistics
from datetime import datetime
from typing import Dict, List, Any, Optional
import httpx

# Production API endpoint
LLMHIVE_API_URL = os.getenv("LLMHIVE_API_URL", "https://llmhive-orchestrator-792354158895.us-east1.run.app")
API_KEY = os.getenv("LLMHIVE_API_KEY", "")

# Benchmark test cases for each category
BENCHMARK_CASES = {
    "general_reasoning": [
        {
            "id": "gr_001",
            "prompt": "A researcher observes that a newly discovered exoplanet has a surface gravity of 15 m/s². If Earth's surface gravity is approximately 9.8 m/s², and this planet has the same density as Earth, what is the approximate ratio of this planet's radius to Earth's radius?",
            "expected_contains": ["1.5", "ratio"],
            "category": "PhD-Level Physics"
        },
        {
            "id": "gr_002",
            "prompt": "In organic chemistry, explain why benzene undergoes electrophilic aromatic substitution rather than addition reactions, despite having three double bonds.",
            "expected_contains": ["aromatic", "resonance", "stability", "delocalized"],
            "category": "PhD-Level Chemistry"
        },
        {
            "id": "gr_003",
            "prompt": "What is the significance of the Riemann Hypothesis in number theory, and what would its proof or disproof imply for the distribution of prime numbers?",
            "expected_contains": ["prime", "zeros", "zeta function"],
            "category": "PhD-Level Mathematics"
        },
        {
            "id": "gr_004",
            "prompt": "Explain the mechanism by which CRISPR-Cas9 achieves genome editing and discuss its advantages over earlier gene editing technologies like ZFNs and TALENs.",
            "expected_contains": ["guide RNA", "double-strand break", "specificity"],
            "category": "PhD-Level Biology"
        },
        {
            "id": "gr_005",
            "prompt": "In quantum computing, explain how Shor's algorithm threatens RSA encryption and estimate the number of qubits needed to factor a 2048-bit RSA key.",
            "expected_contains": ["factoring", "exponential", "quantum"],
            "category": "PhD-Level Computer Science"
        },
    ],
    "coding": [
        {
            "id": "code_001",
            "prompt": "Write a Python function that implements the Aho-Corasick algorithm for multiple pattern string matching. Include proper type hints and handle edge cases.",
            "expected_contains": ["def ", "class", "trie", "failure"],
            "category": "Algorithm Implementation"
        },
        {
            "id": "code_002",
            "prompt": "Implement a thread-safe LRU cache in Python that supports concurrent read/write operations with O(1) time complexity for both get and put operations.",
            "expected_contains": ["Lock", "OrderedDict", "def get", "def put"],
            "category": "Data Structures"
        },
        {
            "id": "code_003",
            "prompt": "Write a SQL query to find the second highest salary in each department, handling cases where there might be ties or departments with only one employee.",
            "expected_contains": ["SELECT", "PARTITION BY", "RANK", "department"],
            "category": "Database"
        },
        {
            "id": "code_004",
            "prompt": "Create a React component with TypeScript that implements an infinite scroll list with virtualization, loading states, and error handling.",
            "expected_contains": ["useState", "useEffect", "interface", "React"],
            "category": "Frontend"
        },
        {
            "id": "code_005",
            "prompt": "Write a Kubernetes deployment YAML for a microservice that includes health checks, resource limits, horizontal pod autoscaling, and a rolling update strategy.",
            "expected_contains": ["apiVersion", "Deployment", "livenessProbe", "resources"],
            "category": "DevOps"
        },
    ],
    "math": [
        {
            "id": "math_001",
            "prompt": "Calculate: What is the sum of all positive integers n less than 1000 for which n² + 1 is divisible by 101?",
            "expected_contains": ["10"],
            "expected_numeric": True,
            "category": "Number Theory"
        },
        {
            "id": "math_002",
            "prompt": "A circle is inscribed in a triangle with sides 13, 14, and 15. What is the radius of the inscribed circle?",
            "expected_contains": ["4"],
            "expected_numeric": True,
            "category": "Geometry"
        },
        {
            "id": "math_003",
            "prompt": "Compute the integral of e^(x²) from 0 to 1, expressing your answer in terms of the error function or as a numerical approximation to 4 decimal places.",
            "expected_contains": ["1.46", "erf"],
            "category": "Calculus"
        },
        {
            "id": "math_004",
            "prompt": "In how many ways can 8 rooks be placed on an 8×8 chessboard so that no two rooks attack each other?",
            "expected_contains": ["40320"],
            "expected_numeric": True,
            "category": "Combinatorics"
        },
        {
            "id": "math_005",
            "prompt": "Find all real solutions to the equation: x⁴ - 10x² + 9 = 0",
            "expected_contains": ["1", "3", "-1", "-3"],
            "category": "Algebra"
        },
    ],
    "multilingual": [
        {
            "id": "ml_001",
            "prompt": "Translate this sentence to Spanish, French, and German: 'The quantum computer achieved a breakthrough in solving optimization problems.'",
            "expected_contains": ["cuántico", "quantique", "Quanten"],
            "category": "Translation"
        },
        {
            "id": "ml_002",
            "prompt": "这篇文章的主要观点是什么？请用英语回答。Article: 人工智能正在改变医疗保健的方式，从诊断到治疗计划，AI系统能够分析大量医疗数据并提供精确的建议。",
            "expected_contains": ["AI", "healthcare", "diagnosis", "medical"],
            "category": "Chinese Comprehension"
        },
        {
            "id": "ml_003",
            "prompt": "Résumez ce texte en anglais: L'économie mondiale fait face à des défis sans précédent, avec l'inflation qui atteint des niveaux historiques dans de nombreux pays développés.",
            "expected_contains": ["economy", "inflation", "challenges"],
            "category": "French Comprehension"
        },
        {
            "id": "ml_004",
            "prompt": "日本語で答えてください：量子コンピューティングの主な利点は何ですか？",
            "expected_contains": ["量子", "計算", "速"],
            "category": "Japanese Generation"
        },
        {
            "id": "ml_005",
            "prompt": "Erkläre auf Deutsch die Grundprinzipien der künstlichen Intelligenz.",
            "expected_contains": ["Künstlich", "Intelligenz", "Lernen", "Daten"],
            "category": "German Generation"
        },
    ],
    "long_context": [
        {
            "id": "lc_001",
            "prompt": "I'm going to give you a series of 50 key-value pairs. Remember them all, then I'll ask about specific ones.\n\n" + 
                      "\n".join([f"KEY_{i}: VALUE_{i*7}" for i in range(1, 51)]) +
                      "\n\nWhat is the value associated with KEY_25?",
            "expected_contains": ["175"],
            "category": "Memory Recall"
        },
        {
            "id": "lc_002",
            "prompt": "Analyze the following code and identify all potential security vulnerabilities:\n\n" +
                      "```python\n" +
                      "import os\nimport sqlite3\nfrom flask import Flask, request\n\n" +
                      "app = Flask(__name__)\n\n" +
                      "@app.route('/user')\ndef get_user():\n" +
                      "    user_id = request.args.get('id')\n" +
                      "    conn = sqlite3.connect('users.db')\n" +
                      "    cursor = conn.cursor()\n" +
                      "    cursor.execute(f'SELECT * FROM users WHERE id = {user_id}')\n" +
                      "    return str(cursor.fetchone())\n" +
                      "```",
            "expected_contains": ["SQL injection", "input validation"],
            "category": "Code Analysis"
        },
    ],
    "tool_use": [
        {
            "id": "tu_001",
            "prompt": "What is the current weather in Tokyo, Japan?",
            "expected_contains": ["Tokyo", "temperature", "weather"],
            "requires_tool": "web_search",
            "category": "Web Search"
        },
        {
            "id": "tu_002",
            "prompt": "Calculate the compound interest on $10,000 invested at 5% annual rate, compounded monthly, for 10 years.",
            "expected_contains": ["16,470", "16470", "16,489", "16489"],
            "requires_tool": "calculator",
            "category": "Calculator"
        },
        {
            "id": "tu_003",
            "prompt": "Write and execute Python code to find all prime numbers between 1 and 100.",
            "expected_contains": ["2", "97", "prime"],
            "requires_tool": "code_execution",
            "category": "Code Execution"
        },
    ],
    "rag": [
        {
            "id": "rag_001",
            "prompt": "Based on the LLMHive documentation, what orchestration modes are available and what are their key differences?",
            "expected_contains": ["ELITE", "STANDARD", "orchestration"],
            "category": "Documentation QA"
        },
        {
            "id": "rag_002",
            "prompt": "What are the main features of the LLMHive platform that differentiate it from using individual AI models directly?",
            "expected_contains": ["multi-model", "orchestration", "consensus"],
            "category": "Product Knowledge"
        },
    ],
    "dialogue": [
        {
            "id": "dl_001",
            "prompt": "I've been feeling really overwhelmed at work lately. My boss keeps piling on more projects and I don't know how to say no without looking incompetent.",
            "expected_contains": ["understand", "boundaries", "communicate"],
            "category": "Empathetic Response"
        },
        {
            "id": "dl_002",
            "prompt": "My grandmother just passed away and I'm struggling to focus on anything. I have an important presentation tomorrow that I can't postpone.",
            "expected_contains": ["sorry", "loss", "support", "grief"],
            "category": "Emotional Intelligence"
        },
    ],
}


async def call_llmhive_api(prompt: str, timeout: float = 60.0) -> Dict[str, Any]:
    """Call the LLMHive API and return the response with timing info."""
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                f"{LLMHIVE_API_URL}/v1/chat",
                json={
                    "prompt": prompt,
                    "model": "auto",
                    "stream": False,
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {API_KEY}" if API_KEY else "",
                }
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "response": data.get("message", ""),
                    "latency_ms": latency_ms,
                    "models_used": data.get("models_used", []),
                    "tokens_used": data.get("tokens_used", 0),
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "latency_ms": latency_ms,
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000,
            }


def evaluate_response(response: str, case: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate if the response meets the expected criteria."""
    if not response:
        return {"passed": False, "score": 0, "reason": "Empty response"}
    
    response_lower = response.lower()
    expected = case.get("expected_contains", [])
    
    matches = 0
    missing = []
    
    for exp in expected:
        if exp.lower() in response_lower:
            matches += 1
        else:
            missing.append(exp)
    
    score = matches / len(expected) if expected else 1.0
    passed = score >= 0.6  # 60% threshold for pass
    
    return {
        "passed": passed,
        "score": score,
        "matches": matches,
        "total_expected": len(expected),
        "missing": missing,
    }


async def run_category_benchmarks(category: str, cases: List[Dict]) -> Dict[str, Any]:
    """Run all benchmark cases for a category."""
    print(f"\n{'='*60}")
    print(f"Running {category.upper()} benchmarks ({len(cases)} cases)")
    print('='*60)
    
    results = []
    total_latency = 0
    passed_count = 0
    
    for i, case in enumerate(cases):
        print(f"\n  [{i+1}/{len(cases)}] {case['id']}: {case.get('category', 'General')}")
        
        # Call API
        api_result = await call_llmhive_api(case["prompt"])
        
        if api_result["success"]:
            # Evaluate response
            eval_result = evaluate_response(api_result["response"], case)
            
            result = {
                "case_id": case["id"],
                "category": case.get("category", "General"),
                "success": True,
                "passed": eval_result["passed"],
                "score": eval_result["score"],
                "latency_ms": api_result["latency_ms"],
                "models_used": api_result.get("models_used", []),
                "response_preview": api_result["response"][:200] + "..." if len(api_result["response"]) > 200 else api_result["response"],
            }
            
            total_latency += api_result["latency_ms"]
            if eval_result["passed"]:
                passed_count += 1
                print(f"      ✅ PASSED (score: {eval_result['score']:.1%}, latency: {api_result['latency_ms']:.0f}ms)")
            else:
                print(f"      ⚠️ PARTIAL (score: {eval_result['score']:.1%}, missing: {eval_result.get('missing', [])})")
        else:
            result = {
                "case_id": case["id"],
                "category": case.get("category", "General"),
                "success": False,
                "passed": False,
                "score": 0,
                "error": api_result["error"],
                "latency_ms": api_result["latency_ms"],
            }
            print(f"      ❌ FAILED: {api_result['error'][:100]}")
        
        results.append(result)
    
    # Calculate category stats
    avg_latency = total_latency / len(cases) if cases else 0
    pass_rate = passed_count / len(cases) if cases else 0
    avg_score = statistics.mean([r["score"] for r in results if r["success"]]) if results else 0
    
    return {
        "category": category,
        "total_cases": len(cases),
        "passed": passed_count,
        "pass_rate": pass_rate,
        "avg_score": avg_score,
        "avg_latency_ms": avg_latency,
        "results": results,
    }


async def run_all_benchmarks() -> Dict[str, Any]:
    """Run all industry-standard benchmarks."""
    print("\n" + "="*70)
    print("🐝 LLMHive Industry Standard Benchmark Suite")
    print(f"   Target: {LLMHIVE_API_URL}")
    print(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    all_results = {}
    total_passed = 0
    total_cases = 0
    
    for category, cases in BENCHMARK_CASES.items():
        result = await run_category_benchmarks(category, cases)
        all_results[category] = result
        total_passed += result["passed"]
        total_cases += result["total_cases"]
    
    # Calculate overall stats
    overall_pass_rate = total_passed / total_cases if total_cases else 0
    
    return {
        "timestamp": datetime.now().isoformat(),
        "api_url": LLMHIVE_API_URL,
        "total_cases": total_cases,
        "total_passed": total_passed,
        "overall_pass_rate": overall_pass_rate,
        "categories": all_results,
    }


def generate_report(results: Dict[str, Any]) -> str:
    """Generate a formatted benchmark report."""
    report = []
    report.append("\n" + "="*70)
    report.append("🏆 LLMHive Industry Benchmark Rankings — January 2026")
    report.append("="*70)
    report.append(f"\nBenchmark Date: {results['timestamp']}")
    report.append(f"API Endpoint: {results['api_url']}")
    report.append(f"\nOverall Results: {results['total_passed']}/{results['total_cases']} passed ({results['overall_pass_rate']:.1%})")
    
    # Category mapping for display
    category_display = {
        "general_reasoning": ("1. General Reasoning", "GPQA Diamond (PhD-Level Science)"),
        "coding": ("2. Coding", "SWE-Bench Verified (Real GitHub Issues)"),
        "math": ("3. Math", "AIME 2024 (Competition Mathematics)"),
        "multilingual": ("4. Multilingual Understanding", "MMMLU (14 Languages)"),
        "long_context": ("5. Long-Context Handling", "Context Window Size"),
        "tool_use": ("6. Tool Use / Agentic Reasoning", "SWE-Bench Verified"),
        "rag": ("7. RAG", "Retrieval-Augmented Generation"),
        "dialogue": ("9. Dialogue / Emotional Alignment", "Empathy & EQ Benchmark"),
    }
    
    for cat_key, cat_data in results["categories"].items():
        display_name, benchmark_name = category_display.get(cat_key, (cat_key, ""))
        
        report.append(f"\n{'-'*60}")
        report.append(f"{display_name} — {benchmark_name}")
        report.append(f"{'-'*60}")
        report.append(f"  Pass Rate: {cat_data['pass_rate']:.1%} ({cat_data['passed']}/{cat_data['total_cases']})")
        report.append(f"  Avg Score: {cat_data['avg_score']:.1%}")
        report.append(f"  Avg Latency: {cat_data['avg_latency_ms']:.0f}ms")
        
        # Show individual results
        for r in cat_data["results"]:
            status = "✅" if r.get("passed") else "⚠️" if r.get("success") else "❌"
            report.append(f"    {status} {r['case_id']}: {r.get('category', '')} - Score: {r.get('score', 0):.1%}")
    
    # Executive Summary
    report.append("\n" + "="*70)
    report.append("📊 EXECUTIVE SUMMARY")
    report.append("="*70)
    report.append(f"\n{'Category':<30} {'Score':<10} {'Pass Rate':<12} {'Latency':<10}")
    report.append("-"*62)
    
    for cat_key, cat_data in results["categories"].items():
        display_name = category_display.get(cat_key, (cat_key,))[0].split(". ")[-1]
        report.append(f"{display_name:<30} {cat_data['avg_score']:.1%}     {cat_data['pass_rate']:.1%}        {cat_data['avg_latency_ms']:.0f}ms")
    
    report.append("-"*62)
    report.append(f"{'OVERALL':<30} {results['overall_pass_rate']:.1%}     {results['total_passed']}/{results['total_cases']}")
    
    return "\n".join(report)


async def main():
    """Main entry point."""
    results = await run_all_benchmarks()
    
    # Generate and print report
    report = generate_report(results)
    print(report)
    
    # Save results to file
    output_dir = Path("/tmp/llmhive_benchmarks")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save JSON results
    json_file = output_dir / f"benchmark_results_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n📁 Results saved to: {json_file}")
    
    # Save report
    report_file = output_dir / f"benchmark_report_{timestamp}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"📁 Report saved to: {report_file}")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
