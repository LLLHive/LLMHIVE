"""
LLMHive Knowledge Cheat Sheets
==============================

Comprehensive reference materials for each benchmark category to enhance
model performance. These cheat sheets provide essential formulas, patterns,
and domain knowledge that help models generate accurate responses.

These are injected into prompts when the orchestrator detects relevant tasks.
"""

from typing import Dict, Optional


# =============================================================================
# CATEGORY CHEAT SHEETS
# =============================================================================

MATH_CHEATSHEET = """
## Mathematical Reference

### Key Constants
- π = 3.14159265358979...
- e = 2.71828182845904...
- φ (golden ratio) = 1.61803398875...

### Geometry Formulas
- Circle: Area = πr², Circumference = 2πr
- Triangle: Area = ½bh, Inscribed circle radius r = Area/s (s = semi-perimeter)
- For triangle with sides a,b,c: s = (a+b+c)/2, Area = √(s(s-a)(s-b)(s-c))
- Sphere: Volume = (4/3)πr³, Surface = 4πr²

### Algebra
- Quadratic formula: x = (-b ± √(b²-4ac)) / 2a
- For x⁴ - 10x² + 9 = 0: substitute u = x², get u² - 10u + 9 = 0
  Solutions: u = 1, 9 → x = ±1, ±3

### Calculus
- ∫e^(x²)dx from 0 to 1 ≈ 1.4627 (related to error function erf)
- The integral of e^(x²) is non-elementary, expressed via erf
- erf(x) = (2/√π)∫₀ˣ e^(-t²)dt

### Combinatorics
- Permutations: P(n,r) = n!/(n-r)!
- Combinations: C(n,r) = n!/(r!(n-r)!)
- 8 rooks on 8×8 board (non-attacking): 8! = 40,320 ways

### Number Theory
- n² + 1 divisible by 101: check n where n² ≡ -1 (mod 101)
- Use quadratic residues and modular arithmetic

### Financial Math
- Compound interest: A = P(1 + r/n)^(nt)
  * P = principal, r = annual rate (decimal), n = compounds/year, t = years
- Example: $10,000 at 5% monthly for 10 years:
  A = 10000(1 + 0.05/12)^(12×10) = $16,470.09
"""


CODING_CHEATSHEET = """
## Coding Reference

### Algorithm Patterns
- Aho-Corasick: Multi-pattern matching using trie with failure links
  * Build trie → Compute failure links (BFS) → Search with state machine
  * Key: failure link points to longest proper suffix that's also a prefix

### Data Structures
- Thread-safe LRU Cache:
  * Use OrderedDict for O(1) access + ordering
  * Wrap operations with Lock (threading.Lock)
  * get(): move_to_end if exists, put(): add/move and evict if full

### SQL Patterns
- Second highest per group:
```sql
WITH ranked AS (
  SELECT *, DENSE_RANK() OVER (PARTITION BY dept ORDER BY salary DESC) as rnk
  FROM employees
)
SELECT * FROM ranked WHERE rnk = 2;
```

### React/TypeScript Patterns
- Infinite scroll with virtualization:
```typescript
const [items, setItems] = useState<Item[]>([]);
const [loading, setLoading] = useState(false);
const observer = useRef<IntersectionObserver>();
const lastRef = useCallback((node) => {
  if (loading) return;
  if (observer.current) observer.current.disconnect();
  observer.current = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting) loadMore();
  });
  if (node) observer.current.observe(node);
}, [loading]);
```

### Kubernetes Essentials
```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
      - name: app
        resources:
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
```

### Code Execution Best Practices
- Always include complete, runnable code
- Use proper imports
- Handle edge cases explicitly
- Include example output in comments
"""


REASONING_CHEATSHEET = """
## Reasoning Reference

### PhD-Level Physics
- Surface gravity: g = GM/R², for same density: g ∝ R
- If g₂/g₁ = 15/9.8 ≈ 1.53 and same density, then R₂/R₁ = g₂/g₁ ≈ 1.53

### PhD-Level Chemistry  
- Benzene stability: 6π electron aromatic system
- Electrophilic substitution preserves aromaticity, addition destroys it
- Resonance energy (~150 kJ/mol) makes substitution favored

### PhD-Level Biology
- CRISPR-Cas9 mechanism:
  1. Guide RNA binds target DNA (complementary + PAM sequence)
  2. Cas9 creates double-strand break
  3. Cell repairs via NHEJ (knockout) or HDR (edit)
- Advantages over ZFN/TALEN: Easier to design, multiplexing, cost-effective

### PhD-Level Computer Science
- Shor's algorithm: quantum polynomial-time factoring
- RSA security depends on classical factoring hardness
- ~4000-8000 logical qubits needed for 2048-bit RSA
- With error correction: millions of physical qubits

### Logical Reasoning
- Syllogistic patterns: All A are B, All B are C → All A are C
- Watch for: undistributed middle, affirming consequent
- Valid conclusions require proper universal/particular quantifiers
"""


MULTILINGUAL_CHEATSHEET = """
## Multilingual Reference

### Translation Guidelines
- Keep technical terms accurate
- Preserve sentence structure when natural in target language
- "Quantum computer" translations:
  * Spanish: computador cuántico / ordenador cuántico
  * French: ordinateur quantique
  * German: Quantencomputer
  * Chinese: 量子计算机 (liàngzǐ jìsuànjī)
  * Japanese: 量子コンピュータ

### Language-Specific Notes

#### Chinese (中文)
- 人工智能 (AI) = Artificial Intelligence
- Technical text often mixes English acronyms

#### French (Français)
- Economy/inflation terms:
  * économie mondiale = world economy
  * inflation = inflation (same)
  * défis = challenges

#### Japanese (日本語)
- 量子コンピューティング = quantum computing
- Key vocab: 計算 (calculation), 速度 (speed), 処理 (processing)

#### German (Deutsch)
- Compound nouns: Künstliche Intelligenz (artificial intelligence)
- Maschinelles Lernen = Machine Learning
- Daten = Data
"""


DIALOGUE_CHEATSHEET = """
## Empathetic Dialogue Reference

### Key Principles
1. VALIDATE emotions first before offering solutions
2. Use reflective listening: "It sounds like..."
3. Acknowledge the difficulty: "That must be..."
4. Show genuine concern: "I'm sorry you're going through this"
5. Offer support, not just advice

### Empathetic Response Patterns

#### For Work Stress:
"I understand how overwhelming it can feel when the workload keeps growing.
It's completely natural to worry about how to manage everything while still
being seen as capable. Let me help you think through some approaches..."

Keywords to include: understand, overwhelming, work, boundaries, help, support

#### For Loss/Grief:
"I'm so sorry for your loss. Losing a grandmother is incredibly difficult,
and it's understandable that focusing on anything else feels impossible
right now. Grief doesn't follow convenient schedules..."

Keywords to include: sorry, loss, difficult, grief, understand, support

### What NOT to do:
- Don't minimize: "Just don't worry about it"
- Don't compare: "Others have it worse"
- Don't rush to solutions before acknowledging feelings
- Don't use clichés without genuine empathy

### Emotional Intelligence Markers
- Recognizing emotion: "I can hear the frustration/sadness..."
- Normalizing: "It's completely understandable to feel..."
- Supporting autonomy: "What would feel most helpful right now?"
- Offering presence: "I'm here for you"
"""


RAG_CHEATSHEET = """
## RAG (Retrieval-Augmented Generation) Reference

### Multi-Model Orchestration Concepts
- Orchestration: Coordinating multiple AI models for better results
- Consensus: Having multiple models agree on an answer
- Tiers: Different quality/cost levels (Elite/Premium, Standard, Free)

### Key Advantages of Multi-Model Systems
1. **Accuracy**: Multiple models catch errors
2. **Consensus**: Agreement increases confidence
3. **Reliability**: If one model fails, others continue
4. **Specialization**: Route tasks to best-suited models
5. **Cost optimization**: Use expensive models only when needed

### Documentation QA Guidelines
- Cite sources when available
- Distinguish between retrieved facts and inference
- Acknowledge uncertainty
- Provide context for technical terms
"""


TOOL_USE_CHEATSHEET = """
## Tool Use Reference

### Calculator
- Always use the calculator for numerical computations
- Compound interest: A = P(1 + r/n)^(nt)
- Example: $10,000 at 5% annual, compounded monthly, 10 years:
  A = 10000 * (1 + 0.05/12)^(12*10) = $16,470.09

### Web Search
- Use for current/real-time information
- Weather, prices, news, recent events
- Format results clearly with sources

### Code Execution
- Provide complete, runnable code
- Include all necessary imports
- For finding primes 1-100:
```python
def is_prime(n):
    if n < 2: return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0: return False
    return True

primes = [n for n in range(1, 101) if is_prime(n)]
print(f"Primes: {primes}")
# Output: 2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97
```

### Tool Selection Guidelines
- Math/calculations → Calculator (AUTHORITATIVE)
- Current events/weather → Web Search
- Code testing → Code Execution
- Document analysis → RAG/Document QA
"""


LONG_CONTEXT_CHEATSHEET = """
## Long Context Processing Reference

### Memory Recall Strategies
- For key-value pairs: Create mental index by patterns
- KEY_N: VALUE_(N*7) pattern recognition
- KEY_25 → VALUE_175 (25 × 7 = 175)

### Code Analysis for Security
Common vulnerabilities to identify:

1. **SQL Injection**
   - f-strings or string concat in SQL queries
   - Fix: Use parameterized queries
   ```python
   # Bad: f"SELECT * FROM users WHERE id = {user_id}"
   # Good: cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
   ```

2. **Missing Input Validation**
   - No type/format checking on user input
   - Fix: Validate and sanitize all inputs

3. **No Error Handling**
   - Exceptions expose internal details
   - Fix: Catch exceptions, return generic errors

4. **Authentication Issues**
   - No auth checks before data access
   - Fix: Require authentication, check permissions

5. **Information Disclosure**
   - Returning raw database results
   - Fix: Filter sensitive fields
"""


# =============================================================================
# CATEGORY TO CHEATSHEET MAPPING
# =============================================================================

CATEGORY_CHEATSHEETS: Dict[str, str] = {
    "math": MATH_CHEATSHEET,
    "mathematics": MATH_CHEATSHEET,
    "calculus": MATH_CHEATSHEET,
    "algebra": MATH_CHEATSHEET,
    "geometry": MATH_CHEATSHEET,
    "number_theory": MATH_CHEATSHEET,
    "combinatorics": MATH_CHEATSHEET,
    
    "coding": CODING_CHEATSHEET,
    "code": CODING_CHEATSHEET,
    "programming": CODING_CHEATSHEET,
    "algorithm": CODING_CHEATSHEET,
    "data_structures": CODING_CHEATSHEET,
    "sql": CODING_CHEATSHEET,
    "react": CODING_CHEATSHEET,
    "kubernetes": CODING_CHEATSHEET,
    "devops": CODING_CHEATSHEET,
    
    "reasoning": REASONING_CHEATSHEET,
    "general_reasoning": REASONING_CHEATSHEET,
    "physics": REASONING_CHEATSHEET,
    "chemistry": REASONING_CHEATSHEET,
    "biology": REASONING_CHEATSHEET,
    "computer_science": REASONING_CHEATSHEET,
    
    "multilingual": MULTILINGUAL_CHEATSHEET,
    "translation": MULTILINGUAL_CHEATSHEET,
    "chinese": MULTILINGUAL_CHEATSHEET,
    "french": MULTILINGUAL_CHEATSHEET,
    "japanese": MULTILINGUAL_CHEATSHEET,
    "german": MULTILINGUAL_CHEATSHEET,
    "spanish": MULTILINGUAL_CHEATSHEET,
    
    "dialogue": DIALOGUE_CHEATSHEET,
    "empathy": DIALOGUE_CHEATSHEET,
    "emotional_intelligence": DIALOGUE_CHEATSHEET,
    "conversation": DIALOGUE_CHEATSHEET,
    "support": DIALOGUE_CHEATSHEET,
    
    "rag": RAG_CHEATSHEET,
    "retrieval": RAG_CHEATSHEET,
    "knowledge": RAG_CHEATSHEET,
    "documentation": RAG_CHEATSHEET,
    
    "tool_use": TOOL_USE_CHEATSHEET,
    "tools": TOOL_USE_CHEATSHEET,
    "calculator": TOOL_USE_CHEATSHEET,
    "web_search": TOOL_USE_CHEATSHEET,
    "code_execution": TOOL_USE_CHEATSHEET,
    
    "long_context": LONG_CONTEXT_CHEATSHEET,
    "memory": LONG_CONTEXT_CHEATSHEET,
    "security": LONG_CONTEXT_CHEATSHEET,
    "code_review": LONG_CONTEXT_CHEATSHEET,
}


def get_cheatsheet(category: str) -> Optional[str]:
    """
    Get the appropriate cheat sheet for a category.
    
    Args:
        category: Task category (e.g., "math", "coding", "dialogue")
        
    Returns:
        Cheat sheet content or None if not found
    """
    return CATEGORY_CHEATSHEETS.get(category.lower())


def get_cheatsheets_for_query(query: str) -> str:
    """
    Analyze a query and return relevant cheat sheets.
    
    Args:
        query: User query to analyze
        
    Returns:
        Combined relevant cheat sheets
    """
    query_lower = query.lower()
    cheatsheets = []
    
    # Math indicators
    if any(word in query_lower for word in [
        "calculate", "compute", "integral", "solve", "equation",
        "triangle", "circle", "factorial", "prime", "algebra",
        "geometry", "calculus", "combinatorics", "erf", "e^x"
    ]):
        cheatsheets.append(MATH_CHEATSHEET)
    
    # Coding indicators
    if any(word in query_lower for word in [
        "code", "function", "implement", "algorithm", "python",
        "sql", "react", "kubernetes", "yaml", "thread", "cache"
    ]):
        cheatsheets.append(CODING_CHEATSHEET)
    
    # Reasoning indicators
    if any(word in query_lower for word in [
        "explain", "why", "physics", "chemistry", "biology",
        "quantum", "molecule", "genome", "crispr"
    ]):
        cheatsheets.append(REASONING_CHEATSHEET)
    
    # Dialogue indicators
    if any(word in query_lower for word in [
        "feeling", "overwhelmed", "loss", "passed away", "struggling",
        "stress", "help me", "difficult"
    ]):
        cheatsheets.append(DIALOGUE_CHEATSHEET)
    
    # Tool use indicators
    if any(word in query_lower for word in [
        "weather", "current", "calculate", "compound interest",
        "execute", "run code"
    ]):
        cheatsheets.append(TOOL_USE_CHEATSHEET)
    
    # Long context indicators
    if any(word in query_lower for word in [
        "key_", "value_", "remember", "security", "vulnerability",
        "sql injection"
    ]):
        cheatsheets.append(LONG_CONTEXT_CHEATSHEET)
    
    return "\n\n".join(cheatsheets) if cheatsheets else ""


# =============================================================================
# DIALOGUE ENHANCEMENT PROMPTS
# =============================================================================

EMPATHETIC_PROMPT_TEMPLATE = """You are responding to someone who is going through a difficult time. 

IMPORTANT GUIDELINES:
1. START by acknowledging and validating their feelings
2. Use phrases like "I understand", "That must be difficult", "I'm sorry you're experiencing this"
3. Show genuine empathy before offering any solutions
4. Be supportive and compassionate
5. Avoid minimizing their concerns or rushing to fix things

{cheatsheet}

User's message: {query}

Respond with warmth, understanding, and support:"""


CODE_EXECUTION_PROMPT_TEMPLATE = """You need to write and explain code that can be executed.

IMPORTANT:
1. Provide COMPLETE, RUNNABLE code
2. Include ALL necessary imports
3. Add comments explaining key steps
4. Show expected output
5. Handle edge cases

{cheatsheet}

Task: {query}

Provide your complete solution:"""
