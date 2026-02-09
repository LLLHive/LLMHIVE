# Coding Test (HumanEval) 0% Failure - Root Cause Analysis

## Problem
All 50 HumanEval tests failed (0% accuracy) with no error samples recorded.

## Investigation
- ✓ API calls succeeded (no errors)
- ✓ Code generation succeeded (no timeout/failures)
- ✗ ALL tests failed `check_correctness` execution

## Root Cause: Code Extraction Bug

Found in `_completion_from_response()` at line 238:

```python
# BUGGY CODE:
if entry_point:
    pattern = re.compile(rf"def\s+{re.escape(entry_point)}\s*\([^)]*\):", re.MULTILINE)
    match = pattern.search(text)
    if match:
        # Found full function definition - use it as-is
        return text.strip() + "\n"  # ❌ BUG: Returns ENTIRE text!
```

### The Issue

When the LLM generates a response like:

```
Here's the solution with edge case handling:

def has_close_elements(numbers: List[float], threshold: float) -> bool:
    if len(numbers) < 2:
        return False
    
    for i in range(len(numbers)):
        for j in range(i + 1, len(numbers)):
            if abs(numbers[i] - numbers[j]) < threshold:
                return True
    return False

This handles empty lists and single elements correctly.
```

The current code returns **THE ENTIRE TEXT** including:
- Explanation before the function
- Explanation after the function
- Potentially broken Python syntax

This causes:
1. Syntax errors (non-code text)
2. Import errors (missing `from typing import List`)
3. Execution failures

## The Fix

Extract ONLY the function code, not the surrounding text:

```python
def _completion_from_response(problem: Dict[str, Any], response: str) -> str:
    """Extract and format code completion for HumanEval - FIXED VERSION"""
    text = _strip_code_fences(response)
    
    # If response contains the full function, extract ONLY the function
    entry_point = problem.get("entry_point", "")
    if entry_point:
        pattern = re.compile(
            rf"(def\s+{re.escape(entry_point)}\s*\([^)]*\).*?)(?=\n(?:def|class|$))",
            re.MULTILINE | re.DOTALL
        )
        match = pattern.search(text)
        if match:
            function_code = match.group(1).strip()
            # Ensure it has proper imports if needed
            if "List[" in function_code or "Dict[" in function_code:
                if "from typing import" not in function_code:
                    function_code = "from typing import List, Dict, Optional\n\n" + function_code
            return function_code + "\n"
    
    # Otherwise, try to extract just the body and combine with prompt
    prompt = problem.get("prompt", "")
    if prompt and prompt in text:
        text = text.split(prompt, 1)[1]

    text = _strip_non_code_trailers(text)
    if not text.strip():
        return prompt.strip() + "\n    pass\n"

    # Ensure proper indentation for function body
    lines = text.splitlines()
    for line in lines:
        if line.strip():
            if not line.startswith((" ", "\t")):
                lines = [f"    {ln}" if ln.strip() else ln for ln in lines]
            break
    
    return prompt.strip() + "\n" + "\n".join(lines).rstrip() + "\n"
```

## Expected Impact

With this fix:
- **Before**: 0% (0/50)
- **After**: 40-60% expected (based on prompt improvements + extraction fix)

The combination of:
1. ✅ Enhanced prompts (edge case awareness)
2. ✅ TDD instructions
3. ✅ FIXED extraction (only function code)
4. ✅ Import handling (typing imports)

Should bring HumanEval from 0% to competitive levels.

## Next Steps

1. Apply the fix to `run_category_benchmarks.py`
2. Re-run coding category only
3. Verify improvement
4. Document successful pattern

## Additional Improvements Needed

Even with the extraction fix, we may need:
1. **Better import detection** - Add common imports automatically
2. **Syntax validation** - Check code is valid Python before submission
3. **Test-driven prompting** - Show expected test cases in prompt
4. **Type hint enforcement** - Ensure type hints match docstring

But the extraction bug is the **critical blocker** causing 100% failure.
