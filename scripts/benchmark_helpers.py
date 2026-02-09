"""
Benchmark Helper Functions - World-Class Implementation
Comprehensive improvements for ALL benchmark categories
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

# ============================================================================
# PHASE 1: HUMANEVAL - EDGE CASE TEMPLATES
# ============================================================================

@dataclass
class EdgeCase:
    """Represents an edge case pattern"""
    name: str
    condition: str
    return_value: str
    description: str

def extract_edge_cases_from_docstring(docstring: str, return_type: str) -> List[EdgeCase]:
    """Extract edge cases from function docstring"""
    edge_cases = []
    
    # Standard edge cases based on return type
    if "List" in return_type or "list" in return_type.lower():
        edge_cases.append(EdgeCase(
            name="empty_list",
            condition="not input_param or len(input_param) == 0",
            return_value="[]",
            description="Handle empty list input"
        ))
        edge_cases.append(EdgeCase(
            name="single_element",
            condition="len(input_param) == 1",
            return_value="# Handle single element case",
            description="Handle single element"
        ))
    
    # Check docstring for specific mentions
    doc_lower = docstring.lower()
    
    if "empty" in doc_lower:
        if "int" in return_type.lower():
            edge_cases.append(EdgeCase(
                name="empty_input",
                condition="not input_param",
                return_value="0",
                description="Handle empty input"
            ))
        elif "bool" in return_type.lower():
            edge_cases.append(EdgeCase(
                name="empty_input",
                condition="not input_param",
                return_value="False",
                description="Handle empty input"
            ))
    
    if "negative" in doc_lower or "< 0" in docstring:
        edge_cases.append(EdgeCase(
            name="negative_numbers",
            condition="# Check for negative numbers",
            return_value="# Handle appropriately",
            description="Handle negative numbers"
        ))
    
    return edge_cases

def generate_edge_case_template(problem: Dict[str, Any]) -> str:
    """Generate code template with mandatory edge case handling"""
    
    prompt = problem.get('prompt', '')
    entry_point = problem.get('entry_point', '')
    
    # Extract function signature
    func_match = re.search(r'def\s+(\w+)\s*\(([^)]*)\)\s*(?:->([^:]+))?:', prompt)
    if not func_match:
        return prompt
    
    func_name = func_match.group(1)
    params = func_match.group(2).strip()
    return_type = func_match.group(3).strip() if func_match.group(3) else "Any"
    
    # Extract docstring
    doc_match = re.search(r'"""(.*?)"""', prompt, re.DOTALL)
    docstring = doc_match.group(1) if doc_match else ""
    
    # Get parameter names
    param_names = []
    for param in params.split(','):
        if ':' in param:
            param_name = param.split(':')[0].strip()
        else:
            param_name = param.strip()
        if param_name:
            param_names.append(param_name)
    
    first_param = param_names[0] if param_names else "input_param"
    
    # Detect edge cases
    edge_cases = extract_edge_cases_from_docstring(docstring, return_type)
    
    # Build template
    template = f'''def {func_name}({params})'''
    if return_type and return_type != "Any":
        template += f' -> {return_type}'
    template += ':\n'
    template += f'    """{docstring}"""\n\n'
    
    # Add edge case handling
    if edge_cases:
        template += '    # EDGE CASE HANDLING (Critical for correctness)\n'
        
        for edge_case in edge_cases:
            if edge_case.name == "empty_list" or edge_case.name == "empty_input":
                template += f'    # {edge_case.description}\n'
                template += f'    if not {first_param}:\n'
                template += f'        return {edge_case.return_value}\n\n'
            
            elif edge_case.name == "single_element":
                template += f'    # {edge_case.description}\n'
                template += f'    if len({first_param}) == 1:\n'
                template += f'        # TODO: Implement single element logic\n'
                template += f'        pass\n\n'
    
    # Add main logic section
    template += '    # MAIN LOGIC\n'
    template += '    # TODO: Implement core algorithm here\n'
    template += '    # Remember to handle all cases from docstring examples\n\n'
    
    # Add type validation before return
    if "List" in return_type:
        template += '    # Type validation\n'
        template += '    if not isinstance(result, list):\n'
        template += '        result = list(result) if hasattr(result, "__iter__") else [result]\n\n'
    elif "int" in return_type.lower():
        template += '    # Type validation\n'
        template += '    if not isinstance(result, int):\n'
        template += '        result = int(result)\n\n'
    elif "bool" in return_type.lower():
        template += '    # Type validation\n'
        template += '    if not isinstance(result, bool):\n'
        template += '        result = bool(result)\n\n'
    
    template += '    return result\n'
    
    return template

# ============================================================================
# PHASE 1 & 3: HUMANEVAL - LOOP PATTERNS & SOLUTION TEMPLATES
# ============================================================================

LOOP_PATTERNS = {
    "compare_all_pairs": '''    # Compare all pairs pattern
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            if condition(arr[i], arr[j]):
                return True
    return False
''',
    "sliding_window": '''    # Sliding window pattern
    for i in range(len(arr) - window_size + 1):
        window = arr[i:i + window_size]
        if process(window):
            return result
''',
    "two_pointer": '''    # Two pointer pattern
    left, right = 0, len(arr) - 1
    while left < right:
        if condition(arr[left], arr[right]):
            left += 1
        else:
            right -= 1
''',
}

def detect_problem_pattern(docstring: str) -> Optional[str]:
    """Detect common algorithm pattern from problem description"""
    doc_lower = docstring.lower()
    
    if any(word in doc_lower for word in ["pairs", "two numbers", "compare", "combination"]):
        return "compare_all_pairs"
    elif any(word in doc_lower for word in ["substring", "subarray", "window", "consecutive"]):
        return "sliding_window"
    elif any(word in doc_lower for word in ["sorted", "two ends", "opposite"]):
        return "two_pointer"
    
    return None

# ============================================================================
# PHASE 1: GSM8K - EXPANDED MATH PATTERNS
# ============================================================================

COMPREHENSIVE_MATH_PATTERNS = [
    # Direct numeric operations
    r'\d+\s*[\+\-\*/\^]\s*\d+',
    
    # Relational math
    r'(?:more|less|fewer|greater|larger|smaller)\s+than',
    r'(?:times|double|triple|half)\s+(?:as|the)',
    r'\d+\s*times\s+(?:more|less|as)',
    
    # Percentage/ratio
    r'\d+\s*(?:%|percent|percentage)',
    r'ratio\s+(?:of|between)',
    r'proportion\s+of',
    
    # Comparative quantities
    r'(?:how\s+)?(?:many|much)\s+(?:more|less)',
    r'(?:increase|decrease)(?:d)?\s+by',
    r'total\s+(?:of|cost|price|amount)',
    
    # Unit conversions
    r'\d+\s*(?:miles?|km|hours?|minutes?|seconds?|dollars?|pounds?|kg|feet|meters?)',
    r'convert\s+(?:from|to)',
    
    # Sequential operations
    r'(?:first|then|next|finally|after\s+that)',
    
    # Financial
    r'(?:profit|loss|revenue|cost|price|discount|sale|tax|interest)',
    
    # Fractions and decimals
    r'\d+/\d+',
    r'\d+\.\d+',
]

MATH_KEYWORDS = [
    "calculate", "compute", "solve", "total", "sum", "difference",
    "how many", "how much", "what is", "find the", "determine",
    "cost", "price", "age", "years", "hours", "minutes",
    "percent", "ratio", "fraction", "decimal", "average", "mean",
    "more than", "less than", "times as", "divided by", "product",
    "area", "volume", "perimeter", "distance", "speed", "rate",
]

def should_force_calculator(question: str) -> bool:
    """Ultra-aggressive calculator detection"""
    
    question_lower = question.lower()
    
    # 1. Direct numeric operations
    if re.search(r'\d+\s*[\+\-\*/\^]', question):
        return True
    
    # 2. Math keywords
    if any(keyword in question_lower for keyword in MATH_KEYWORDS):
        return True
    
    # 3. Comprehensive patterns
    for pattern in COMPREHENSIVE_MATH_PATTERNS:
        if re.search(pattern, question, re.IGNORECASE):
            return True
    
    return False

def decompose_math_steps(question: str) -> List[str]:
    """Decompose multi-step math problem into atomic steps"""
    
    # Look for sequential indicators
    sequential_indicators = ["first", "then", "next", "after", "finally"]
    
    steps = []
    sentences = re.split(r'[.!?]', question)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # Check if this sentence contains a calculation
        has_numbers = bool(re.search(r'\d+', sentence))
        has_operation = any(op in sentence.lower() for op in [
            "add", "subtract", "multiply", "divide", "times", "plus", "minus",
            "more", "less", "total", "sum", "difference", "product"
        ])
        
        if has_numbers and (has_operation or any(ind in sentence.lower() for ind in sequential_indicators)):
            steps.append(sentence)
    
    return steps if steps else [question]

# ============================================================================
# PHASE 2: MMLU - MULTI-HOP REASONING & DOMAIN ROUTING
# ============================================================================

DOMAIN_KEYWORDS = {
    "chemistry": ["molecule", "element", "reaction", "compound", "bond", "atom", "chemical", "periodic"],
    "physics": ["force", "velocity", "energy", "mass", "momentum", "acceleration", "gravity", "motion"],
    "biology": ["cell", "organism", "evolution", "DNA", "enzyme", "protein", "species", "mutation"],
    "history": ["century", "war", "empire", "treaty", "dynasty", "revolution", "ancient", "medieval"],
    "literature": ["author", "novel", "poem", "character", "narrative", "plot", "metaphor", "symbolism"],
    "math": ["equation", "theorem", "proof", "derivative", "integral", "function", "variable", "algebra"],
    "economics": ["supply", "demand", "market", "inflation", "GDP", "trade", "fiscal", "monetary"],
    "computer_science": ["algorithm", "data structure", "complexity", "recursion", "binary", "programming"],
}

DOMAIN_EXPERT_MODELS = {
    "chemistry": "anthropic/claude-opus-4.6",
    "physics": "google/gemini-3-pro",
    "biology": "anthropic/claude-opus-4.6",
    "history": "openai/gpt-5.2",
    "literature": "openai/gpt-5.2",
    "math": "deepseek/deepseek-v3.2-thinking",
    "economics": "openai/gpt-5.2",
    "computer_science": "openai/gpt-5.3-codex",
    "general": "google/gemini-3-pro",
}

def detect_domain(question: str) -> str:
    """Detect question domain from keywords"""
    question_lower = question.lower()
    
    domain_scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in question_lower)
        if score > 0:
            domain_scores[domain] = score
    
    if domain_scores:
        return max(domain_scores, key=domain_scores.get)
    
    return "general"

def has_negation(question: str) -> bool:
    """Detect negation in question"""
    negation_patterns = [
        r'\bNOT\b', r'\bnot\b', r'\bexcept\b', r'\bEXCEPT\b',
        r'\bfalse\b', r'\bFALSE\b', r'\bincorrect\b', r'\bINCORRECT\b',
        r'\bneither\b', r'\bNEITHER\b', r'\bwithout\b', r'\bWITHOUT\b',
    ]
    return any(re.search(pattern, question) for pattern in negation_patterns)

# ============================================================================
# PHASE 1 & 2: MS MARCO - FORMAT FORCING & TWO-STAGE RETRIEVAL
# ============================================================================

def extract_passage_ids_robust(response: str, valid_ids: List[int]) -> List[int]:
    """Ultra-robust passage ID extraction with multiple strategies"""
    
    # Strategy 1: Direct comma-separated numbers
    if re.match(r'^\s*\d+(?:\s*,\s*\d+)*\s*$', response.strip()):
        extracted = [int(x.strip()) for x in response.split(',')]
        # Validate
        if all(id in valid_ids for id in extracted):
            return extracted
    
    # Strategy 2: Find all numbers in order of appearance
    numbers = re.findall(r'\b\d+\b', response)
    if numbers:
        extracted = []
        for num in numbers:
            id_val = int(num)
            if id_val in valid_ids and id_val not in extracted:
                extracted.append(id_val)
        if len(extracted) >= 3:  # At least 3 IDs
            return extracted[:10]
    
    # Strategy 3: Look for patterns like "[7]", "(3)", "ID: 1"
    pattern_matches = re.findall(r'[\[\(]?(\d+)[\]\)]?', response)
    if pattern_matches:
        extracted = []
        for match in pattern_matches:
            id_val = int(match)
            if id_val in valid_ids and id_val not in extracted:
                extracted.append(id_val)
        if len(extracted) >= 3:
            return extracted[:10]
    
    # Fallback: Return valid IDs in original order (worst case)
    return valid_ids[:10]

def compute_keyword_matches(passage: str, query_keywords: List[str]) -> int:
    """Count keyword matches in passage"""
    passage_lower = passage.lower()
    return sum(1 for keyword in query_keywords if keyword in passage_lower)

def compute_length_normalized_score(passage: str, query_keywords: List[str]) -> float:
    """Compute length-normalized relevance score"""
    
    matches = compute_keyword_matches(passage, query_keywords)
    if matches == 0:
        return 0.0
    
    # Normalize by passage length (per 100 words)
    word_count = len(passage.split())
    base_score = matches / max(1, word_count / 100)
    
    # Boost if matches appear early (first 100 words)
    first_100_words = ' '.join(passage.split()[:100])
    early_matches = compute_keyword_matches(first_100_words, query_keywords)
    early_boost = 1 + (early_matches * 0.2)  # 20% boost per early match
    
    return base_score * early_boost

def extract_query_keywords(query: str) -> List[str]:
    """Extract important keywords from query"""
    
    # Remove stop words
    stop_words = {"a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
                  "have", "has", "had", "do", "does", "did", "will", "would", "could",
                  "should", "may", "might", "can", "of", "in", "on", "at", "to", "for",
                  "with", "by", "from", "about", "as", "into", "through", "during"}
    
    # Tokenize and filter
    words = re.findall(r'\w+', query.lower())
    keywords = [w for w in words if w not in stop_words and len(w) > 2]
    
    return keywords

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_ranking(ranked_ids: List[int], valid_ids: List[int]) -> bool:
    """Validate that ranking is usable"""
    if not ranked_ids:
        return False
    
    # Check all IDs are valid
    if not all(rid in valid_ids for rid in ranked_ids):
        return False
    
    # Check no duplicates
    if len(set(ranked_ids)) != len(ranked_ids):
        return False
    
    # At least 3 IDs
    if len(ranked_ids) < 3:
        return False
    
    return True

def infer_empty_return(return_type: str) -> str:
    """Infer appropriate empty return value"""
    if "List" in return_type or "list" in return_type:
        return "[]"
    elif "int" in return_type.lower():
        return "0"
    elif "float" in return_type.lower():
        return "0.0"
    elif "bool" in return_type.lower():
        return "False"
    elif "str" in return_type.lower():
        return '""'
    else:
        return "None"
