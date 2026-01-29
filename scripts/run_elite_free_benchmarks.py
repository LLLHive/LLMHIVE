#!/usr/bin/env python3
"""
LLMHive Elite & Free Orchestration Benchmark Suite
===================================================
Runs comprehensive benchmarks for BOTH Elite and Free orchestration tiers
against the production API.

Usage:
    export API_KEY="your-api-key"
    python scripts/run_elite_free_benchmarks.py
"""

import asyncio
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import httpx

# Production API endpoint
LLMHIVE_API_URL = os.getenv("LLMHIVE_API_URL", "https://llmhive-orchestrator-792354158895.us-east1.run.app")
API_KEY = os.getenv("API_KEY") or os.getenv("LLMHIVE_API_KEY", "")

# Orchestration modes to test
# Note: API only accepts reasoning_mode: fast/standard/deep
# - "deep" = maximum quality with deep consensus and verification
# - "standard" = balanced quality and speed
# - "fast" = quick responses with single model
#
# IMPORTANT: The backend determines model selection based on user subscription tier.
# Both tests below use the same API but with different reasoning modes to show 
# orchestration capability range.
ORCHESTRATION_MODES = {
    "deep": {
        "name": "DEEP (Premium Quality)",
        "reasoning_mode": "deep",  # Deep consensus + verification
        "description": "Maximum quality with multi-model consensus and verification loops",
        "cost_per_query": "Variable (depends on models used)"
    },
    "standard": {
        "name": "STANDARD (Balanced)", 
        "reasoning_mode": "standard",  # Balanced orchestration
        "description": "Balanced quality and speed with standard orchestration",
        "cost_per_query": "Variable (depends on models used)"
    }
}

# Benchmark test cases for each category
BENCHMARK_CASES = {
    "general_reasoning": [
        {
            "id": "gr_001",
            "prompt": "A researcher observes that a newly discovered exoplanet has a surface gravity of 15 m/s². If Earth's surface gravity is approximately 9.8 m/s², and this planet has the same density as Earth, what is the approximate ratio of this planet's radius to Earth's radius?",
            "expected_contains": ["gravity", "radius", "density"],
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
            "expected_contains": ["guide RNA", "DNA", "target"],
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
            "category": "Number Theory"
        },
        {
            "id": "math_002",
            "prompt": "A circle is inscribed in a triangle with sides 13, 14, and 15. What is the radius of the inscribed circle?",
            "expected_contains": ["4"],
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
            "prompt": "Provide the direct translations (not code) of this sentence into Spanish, French, and German. Just give the translated sentences:\n'The quantum computer achieved a breakthrough in solving optimization problems.'",
            "expected_contains": ["computador", "ordinateur", "Computer"],
            "category": "Translation"
        },
        {
            "id": "ml_002",
            "prompt": "Read this Chinese text and answer in English: What technology is discussed?\n\n人工智能 (AI) 正在改变世界。",
            "expected_contains": ["AI", "artificial intelligence"],
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
            "category": "Web Search"
        },
        {
            "id": "tu_002",
            "prompt": "Calculate the compound interest on $10,000 invested at 5% annual rate, compounded monthly, for 10 years.",
            "expected_contains": ["16,470", "16470", "16,489", "16489"],
            "category": "Calculator"
        },
        {
            "id": "tu_003",
            "prompt": "Write and execute Python code to find all prime numbers between 1 and 100.",
            "expected_contains": ["2", "97", "prime"],
            "category": "Code Execution"
        },
    ],
    "rag": [
        {
            "id": "rag_001",
            "prompt": "Explain the concept of multi-model orchestration in AI systems. What are the different tiers or modes that could exist (like premium/standard tiers), and what are their key differences?",
            "expected_contains": ["orchestration", "model", "tier"],
            "category": "Documentation QA"
        },
        {
            "id": "rag_002",
            "prompt": "What are the advantages of using a multi-model AI orchestration platform compared to using a single AI model directly? Consider factors like accuracy, consensus, and reliability.",
            "expected_contains": ["model", "accuracy", "consensus"],
            "category": "Product Knowledge"
        },
    ],
    "dialogue": [
        {
            "id": "dl_001",
            "prompt": "I've been feeling really overwhelmed at work lately. My boss keeps piling on more projects and I don't know how to say no without looking incompetent.",
            "expected_contains": ["understand", "work", "help"],
            "category": "Empathetic Response"
        },
        {
            "id": "dl_002",
            "prompt": "My grandmother just passed away and I'm struggling to focus on anything. I have an important presentation tomorrow that I can't postpone.",
            "expected_contains": ["sorry", "loss", "difficult"],
            "category": "Emotional Intelligence"
        },
    ],
}


def extract_numbers(text: str) -> List[float]:
    """Extract all numeric values from text."""
    pattern = r'[\$]?(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)'
    matches = re.findall(pattern, text)
    numbers = []
    for m in matches:
        try:
            num = float(m.replace(',', ''))
            numbers.append(num)
        except ValueError:
            continue
    return numbers


def check_numeric_match(response: str, expected_value: str, tolerance_pct: float = 5.0) -> bool:
    """Check if response contains a number within tolerance of expected value."""
    try:
        expected_num = float(expected_value.replace(',', ''))
    except ValueError:
        return False
    
    response_numbers = extract_numbers(response)
    tolerance = expected_num * (tolerance_pct / 100.0)
    
    for num in response_numbers:
        if abs(num - expected_num) <= tolerance:
            return True
    return False


def evaluate_response(response: str, case: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate if the response meets the expected criteria."""
    if not response:
        return {"passed": False, "score": 0, "reason": "Empty response"}
    
    response_lower = response.lower()
    expected = case.get("expected_contains", [])
    
    # Alias mappings
    ALIASES = {
        "double-strand break": ["double-strand break", "double strand break", "dsb", "dna break", "dna cleavage"],
        "specificity": ["specificity", "specific", "precision", "precise", "accuracy", "accurate", "targeted"],
        "guide rna": ["guide rna", "grna", "guide-rna", "crrna", "single guide", "sgrna"],
        "loss": ["loss", "lost", "losing", "passing", "passed away", "death", "died", "gone"],
        "grief": ["grief", "grieving", "grieve", "mourning", "mourn", "bereavement", "sorrow"],
        "support": ["support", "supporting", "here for you", "lean on", "help you", "by your side"],
        "difficult": ["difficult", "hard", "tough", "challenging", "overwhelming", "struggle"],
        "ratio": ["ratio", "times", "factor", "proportion", "multiple"],
        "40320": ["40320", "40,320", "8!", "8 factorial", "eight factorial"],
    }
    
    NUMERIC_EXPECTATIONS = {
        "1.5": 15.0,
        "16,470": 5.0,
        "16470": 5.0,
        "16,489": 5.0,
        "16489": 5.0,
    }
    
    matches = 0
    missing = []
    
    for exp in expected:
        exp_lower = exp.lower()
        found = False
        
        if exp in NUMERIC_EXPECTATIONS:
            tolerance = NUMERIC_EXPECTATIONS[exp]
            if check_numeric_match(response, exp, tolerance_pct=tolerance):
                found = True
        
        if not found:
            aliases = ALIASES.get(exp_lower, [])
            for alias in aliases:
                if alias in response_lower:
                    found = True
                    break
        
        if not found:
            if exp_lower in response_lower:
                found = True
        
        if found:
            matches += 1
        else:
            missing.append(exp)
    
    score = matches / len(expected) if expected else 1.0
    passed = score >= 0.6
    
    return {
        "passed": passed,
        "score": score,
        "matches": matches,
        "total_expected": len(expected),
        "missing": missing,
    }


async def call_llmhive_api(prompt: str, reasoning_mode: str, timeout: float = 90.0) -> Dict[str, Any]:
    """Call the LLMHive API with specified reasoning mode."""
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            payload = {
                "prompt": prompt,
                "reasoning_mode": reasoning_mode,
            }
                
            response = await client.post(
                f"{LLMHIVE_API_URL}/v1/chat",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": API_KEY,
                },
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "response": data.get("response", ""),
                    "latency_ms": latency_ms,
                    "models_used": data.get("metadata", {}).get("models_used", []),
                    "cost_info": data.get("extra", {}).get("cost_tracking", {}),
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    "latency_ms": latency_ms,
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000,
            }


async def run_tier_benchmarks(tier_key: str, tier_config: Dict) -> Dict[str, Any]:
    """Run all benchmarks for a specific tier."""
    print(f"\n{'='*70}")
    print(f"🐝 Running {tier_config['name']} Tier Benchmarks")
    print(f"   Mode: {tier_config['reasoning_mode']}")
    print(f"   Cost: {tier_config['cost_per_query']}")
    print(f"{'='*70}")
    
    all_results = {}
    total_passed = 0
    total_cases = 0
    
    for category, cases in BENCHMARK_CASES.items():
        print(f"\n{'─'*60}")
        print(f"Category: {category.upper().replace('_', ' ')}")
        print(f"{'─'*60}")
        
        category_results = []
        category_passed = 0
        
        for i, case in enumerate(cases):
            print(f"  [{i+1}/{len(cases)}] {case['id']}: {case.get('category', 'General')}...", end=" ", flush=True)
            
            api_result = await call_llmhive_api(
                case["prompt"], 
                tier_config["reasoning_mode"]
            )
            
            if api_result["success"]:
                eval_result = evaluate_response(api_result["response"], case)
                
                # Extract actual cost from API response
                cost_info = api_result.get("cost_info", {})
                actual_cost = cost_info.get("total_cost", 0.0)
                
                result = {
                    "case_id": case["id"],
                    "category": case.get("category", "General"),
                    "success": True,
                    "passed": eval_result["passed"],
                    "score": eval_result["score"],
                    "latency_ms": api_result["latency_ms"],
                    "models_used": api_result.get("models_used", []),
                    "actual_cost": actual_cost,
                    "cost_info": cost_info,
                }
                
                if eval_result["passed"]:
                    category_passed += 1
                    cost_str = f", ${actual_cost:.4f}" if actual_cost > 0 else ""
                    print(f"✅ {eval_result['score']:.0%} ({api_result['latency_ms']:.0f}ms{cost_str})")
                else:
                    print(f"⚠️ {eval_result['score']:.0%} (missing: {eval_result.get('missing', [])})")
            else:
                result = {
                    "case_id": case["id"],
                    "category": case.get("category", "General"),
                    "success": False,
                    "passed": False,
                    "score": 0,
                    "error": api_result["error"],
                    "latency_ms": api_result["latency_ms"],
                    "actual_cost": 0.0,
                    "cost_info": {},
                }
                print(f"❌ Error")
            
            category_results.append(result)
            total_cases += 1
            if result["passed"]:
                total_passed += 1
        
        # Calculate category total cost
        category_cost = sum(c.get("actual_cost", 0) for c in category_results)
        
        all_results[category] = {
            "cases": category_results,
            "passed": category_passed,
            "total": len(cases),
            "pass_rate": category_passed / len(cases) if cases else 0,
            "total_cost": category_cost,
        }
    
    # Calculate total actual cost across all tests
    total_cost = sum(cat["total_cost"] for cat in all_results.values())
    avg_cost = total_cost / total_cases if total_cases > 0 else 0
    
    return {
        "tier": tier_key,
        "tier_name": tier_config["name"],
        "results": all_results,
        "total_passed": total_passed,
        "total_cases": total_cases,
        "overall_pass_rate": total_passed / total_cases if total_cases else 0,
        "total_cost": total_cost,
        "avg_cost_per_query": avg_cost,
    }


def generate_markdown_report(deep_results: Dict, standard_results: Dict) -> str:
    """Generate comprehensive markdown benchmark report."""
    timestamp = datetime.now().isoformat()
    
    report = f"""# 🏆 LLMHive Orchestration Benchmark — January 2026

## Test Configuration

- **Benchmark Date:** {timestamp}
- **API Endpoint:** {LLMHIVE_API_URL}
- **Test Method:** Live API calls with keyword/pattern evaluation
- **Orchestration Modes Tested:** DEEP (max quality), STANDARD (balanced)

---

## 📊 Executive Summary

| Mode | Pass Rate | Tests Passed | Actual Total Cost | Avg Cost/Query |
|------|-----------|--------------|-------------------|----------------|
| 🐝 **DEEP** | **{deep_results['overall_pass_rate']:.1%}** | {deep_results['total_passed']}/{deep_results['total_cases']} | ${deep_results.get('total_cost', 0):.4f} | ${deep_results.get('avg_cost_per_query', 0):.6f} |
| ⚡ **STANDARD** | **{standard_results['overall_pass_rate']:.1%}** | {standard_results['total_passed']}/{standard_results['total_cases']} | ${standard_results.get('total_cost', 0):.4f} | ${standard_results.get('avg_cost_per_query', 0):.6f} |

### 💰 Actual Cost Analysis (from API responses)

- **DEEP Total Cost:** ${deep_results.get('total_cost', 0):.4f} for {deep_results['total_cases']} queries
- **STANDARD Total Cost:** ${standard_results.get('total_cost', 0):.4f} for {standard_results['total_cases']} queries  
- **Cost Difference:** ${abs(deep_results.get('total_cost', 0) - standard_results.get('total_cost', 0)):.4f}
- **Quality Gap:** {abs(deep_results['overall_pass_rate'] - standard_results['overall_pass_rate']):.1%} pass rate difference

---

## Category Comparison

| Category | DEEP Score | DEEP Pass | STANDARD Score | STANDARD Pass |
|----------|------------|-----------|----------------|---------------|
"""
    
    category_names = {
        "general_reasoning": "General Reasoning",
        "coding": "Coding",
        "math": "Math",
        "multilingual": "Multilingual",
        "long_context": "Long-Context",
        "tool_use": "Tool Use",
        "rag": "RAG",
        "dialogue": "Dialogue",
    }
    
    for cat_key, cat_name in category_names.items():
        if cat_key in deep_results['results'] and cat_key in standard_results['results']:
            deep_cat = deep_results['results'][cat_key]
            standard_cat = standard_results['results'][cat_key]
            
            deep_score = sum(c['score'] for c in deep_cat['cases']) / len(deep_cat['cases']) if deep_cat['cases'] else 0
            standard_score = sum(c['score'] for c in standard_cat['cases']) / len(standard_cat['cases']) if standard_cat['cases'] else 0
            
            report += f"| {cat_name} | {deep_score:.1%} | {deep_cat['passed']}/{deep_cat['total']} | {standard_score:.1%} | {standard_cat['passed']}/{standard_cat['total']} |\n"
    
    report += "\n---\n\n"
    
    # Detailed results for each category
    for cat_key, cat_name in category_names.items():
        if cat_key not in deep_results['results']:
            continue
            
        deep_cat = deep_results['results'][cat_key]
        standard_cat = standard_results['results'][cat_key]
        
        deep_score = sum(c['score'] for c in deep_cat['cases']) / len(deep_cat['cases']) if deep_cat['cases'] else 0
        standard_score = sum(c['score'] for c in standard_cat['cases']) / len(standard_cat['cases']) if standard_cat['cases'] else 0
        
        deep_cost = deep_cat.get('total_cost', 0)
        standard_cost = standard_cat.get('total_cost', 0)
        
        report += f"""## {cat_name}

| Metric | DEEP | STANDARD |
|--------|------|----------|
| Pass Rate | {deep_cat['pass_rate']:.1%} ({deep_cat['passed']}/{deep_cat['total']}) | {standard_cat['pass_rate']:.1%} ({standard_cat['passed']}/{standard_cat['total']}) |
| Actual Cost | ${deep_cost:.4f} | ${standard_cost:.4f} |
| Avg Score | {deep_score:.1%} | {standard_score:.1%} |

<details>
<summary>Test Details</summary>

| Test ID | Category | DEEP | STANDARD |
|---------|----------|------|----------|
"""
        
        for i, (deep_case, standard_case) in enumerate(zip(deep_cat['cases'], standard_cat['cases'])):
            deep_status = "✅" if deep_case['passed'] else "⚠️"
            standard_status = "✅" if standard_case['passed'] else "⚠️"
            report += f"| {deep_case['case_id']} | {deep_case['category']} | {deep_status} {deep_case['score']:.0%} | {standard_status} {standard_case['score']:.0%} |\n"
        
        report += "\n</details>\n\n---\n\n"
    
    # Performance claims verification
    report += """## 🎯 Key Performance Claims

| Claim | Status | Evidence |
|-------|--------|----------|
"""
    
    # Check specific claims
    claims = []
    
    # Math claim
    deep_math = deep_results['results'].get('math', {})
    standard_math = standard_results['results'].get('math', {})
    if deep_math.get('pass_rate', 0) == 1.0 and standard_math.get('pass_rate', 0) == 1.0:
        claims.append(("BOTH modes achieve 100% in Math", "✅ VERIFIED", f"DEEP: {deep_math['pass_rate']:.0%}, STANDARD: {standard_math['pass_rate']:.0%}"))
    
    # Coding claim
    deep_coding = deep_results['results'].get('coding', {})
    standard_coding = standard_results['results'].get('coding', {})
    if deep_coding.get('pass_rate', 0) >= 0.8:
        claims.append(("DEEP achieves 80%+ in Coding", "✅ VERIFIED", f"DEEP: {deep_coding['pass_rate']:.0%}"))
    
    # RAG claim
    deep_rag = deep_results['results'].get('rag', {})
    standard_rag = standard_results['results'].get('rag', {})
    if deep_rag.get('pass_rate', 0) == 1.0:
        claims.append(("DEEP achieves 100% in RAG", "✅ VERIFIED", f"DEEP: {deep_rag['pass_rate']:.0%}"))
    
    # Standard mode quality
    if standard_results['overall_pass_rate'] >= 0.8:
        claims.append(("STANDARD mode delivers 80%+ overall quality", "✅ VERIFIED", f"STANDARD: {standard_results['overall_pass_rate']:.0%}"))
    
    for claim, status, evidence in claims:
        report += f"| {claim} | {status} | {evidence} |\n"
    
    report += f"""

---

## Test Procedure

1. **API Calls**: Each test makes a live HTTP POST to `{LLMHIVE_API_URL}/v1/chat`
2. **Authentication**: API key authentication via `X-API-Key` header
3. **Evaluation Method**: Keyword/pattern matching with alias support and numeric tolerance
4. **Pass Threshold**: 60% of expected keywords must be present
5. **Timeout**: 90 seconds per request

## Orchestration Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| 🐝 DEEP | Multi-model consensus with verification loops and deep reasoning | Maximum quality for critical tasks |
| ⚡ STANDARD | Balanced orchestration with single-model responses | Faster responses for everyday tasks |

**Note:** The models used depend on the user's subscription tier (FREE vs ELITE).
Both modes apply the same orchestration logic - the difference is the reasoning depth.

---

**Document Generated:** {timestamp}
**Test Source:** `scripts/run_elite_free_benchmarks.py`
"""
    
    return report


async def main():
    """Main benchmark runner."""
    if not API_KEY:
        print("❌ Error: API_KEY environment variable not set")
        print("   Set it with: export API_KEY='your-api-key'")
        return
    
    print(f"✅ API Key found ({len(API_KEY)} chars)")
    print(f"\n{'='*70}")
    print("🐝 LLMHive Orchestration Benchmark Suite")
    print(f"   Target: {LLMHIVE_API_URL}")
    print(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    
    # Run DEEP benchmarks (maximum quality)
    deep_results = await run_tier_benchmarks("deep", ORCHESTRATION_MODES["deep"])
    
    # Run STANDARD benchmarks (balanced)
    standard_results = await run_tier_benchmarks("standard", ORCHESTRATION_MODES["standard"])
    
    # Print summary
    print(f"\n{'='*70}")
    print("📊 FINAL RESULTS SUMMARY")
    print(f"{'='*70}")
    
    deep_cost = deep_results.get('total_cost', 0)
    standard_cost = standard_results.get('total_cost', 0)
    deep_avg = deep_results.get('avg_cost_per_query', 0)
    standard_avg = standard_results.get('avg_cost_per_query', 0)
    
    print(f"\n🐝 DEEP Mode: {deep_results['total_passed']}/{deep_results['total_cases']} passed ({deep_results['overall_pass_rate']:.1%})")
    print(f"   💰 Actual Cost: ${deep_cost:.4f} total | ${deep_avg:.6f}/query")
    print(f"\n⚡ STANDARD Mode:  {standard_results['total_passed']}/{standard_results['total_cases']} passed ({standard_results['overall_pass_rate']:.1%})")
    print(f"   💰 Actual Cost: ${standard_cost:.4f} total | ${standard_avg:.6f}/query")
    
    if deep_cost > 0 or standard_cost > 0:
        print(f"\n💵 COST DIFFERENCE: ${abs(deep_cost - standard_cost):.4f}")
    
    # Generate and save report
    report = generate_markdown_report(deep_results, standard_results)
    
    timestamp = datetime.now().strftime("%Y%m%d")
    report_path = Path(f"benchmark_reports/ORCHESTRATION_BENCHMARK_{timestamp}.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)
    print(f"\n📁 Report saved to: {report_path}")
    
    # Save JSON results
    json_path = Path(f"benchmark_reports/orchestration_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "deep": deep_results,
        "standard": standard_results,
    }
    json_path.write_text(json.dumps(json_data, indent=2, default=str))
    print(f"📁 JSON results saved to: {json_path}")


if __name__ == "__main__":
    asyncio.run(main())
