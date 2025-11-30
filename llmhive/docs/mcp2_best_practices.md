# MCP 2.0 Best Practices

This document provides guidelines for writing safe, efficient code for the MCP 2.0 Code-Executor System.

## Security Best Practices

### 1. Avoid Forbidden Modules

**Never use:**
- `os`, `subprocess`, `sys` - System access
- `shutil`, `socket`, `urllib` - File system and network
- `eval`, `exec`, `__import__` - Code execution

**Use instead:**
- `json` - Data serialization
- `pathlib` - File paths (restricted to workspace)
- `datetime`, `collections` - Standard utilities

### 2. File Access

**Always:**
- Use workspace-relative paths
- Clean up temporary files
- Validate file paths before access

**Example:**
```python
# Good
with open('workspace/temp_data.json', 'w') as f:
    json.dump(data, f)

# Bad
with open('/etc/passwd', 'r') as f:  # Blocked!
    content = f.read()
```

### 3. Error Handling

**Always handle errors gracefully:**
```python
try:
    result = await callMCPTool('getDocument', {'id': doc_id})
    return result
except Exception as e:
    # Return user-friendly error
    return {"error": f"Failed to fetch document: {str(e)}"}
```

## Token Usage Optimization

### 1. Filter Large Outputs

**Before returning data to LLM:**
```python
# Bad: Returns entire dataset
data = await callMCPTool('getAllRecords', {})
return data  # Could be 50k+ tokens

# Good: Filter in sandbox
data = await callMCPTool('getAllRecords', {})
summary = {
    "count": len(data),
    "sample": data[:5],  # First 5 items
    "summary": "Processed in sandbox"
}
return summary  # ~500 tokens
```

### 2. Use Single-Step Workflows

**Combine multiple operations:**
```python
# Bad: Multiple tool calls (each adds context)
doc1 = await callMCPTool('getDocument', {'id': '1'})
doc2 = await callMCPTool('getDocument', {'id': '2'})
# Both doc1 and doc2 in context

# Good: Single execution
code = """
doc1 = await callMCPTool('getDocument', {'id': '1'})
doc2 = await callMCPTool('getDocument', {'id': '2'})
combined = f"Doc1: {doc1['title']}, Doc2: {doc2['title']}"
print(combined)
"""
# Only final result in context
```

### 3. Summarize Instead of Returning Raw Data

```python
# Process data in sandbox
data = await callMCPTool('queryDatabase', {'sql': 'SELECT * FROM table'})

# Summarize
summary = {
    "row_count": len(data),
    "columns": list(data[0].keys()) if data else [],
    "sample": data[:3]  # First 3 rows
}

return summary  # Instead of entire dataset
```

## Code Quality

### 1. Clean Up Resources

```python
# Always clean up temporary files
try:
    with open('temp_file.json', 'w') as f:
        json.dump(data, f)
    # Process file
finally:
    import os
    if os.path.exists('temp_file.json'):
        os.remove('temp_file.json')
```

### 2. Validate Inputs

```python
def process_data(data):
    if not isinstance(data, dict):
        raise ValueError("Expected dictionary")
    if 'required_field' not in data:
        raise ValueError("Missing required_field")
    # Process...
```

### 3. Use Type Hints (for Python stubs)

```python
async def my_tool(param1: str, param2: int) -> dict:
    """Tool description."""
    result = await call_mcp_tool("myTool", {
        "param1": param1,
        "param2": param2
    })
    return result
```

## Performance Tips

### 1. Batch Operations

```python
# Process multiple items in one execution
items = await callMCPTool('listItems', {})
results = []
for item in items[:10]:  # Limit to 10
    processed = process_item(item)
    results.append(processed)
return {"results": results}
```

### 2. Cache When Appropriate

```python
# Use workspace to cache expensive operations
cache_file = 'workspace/cache.json'
if os.path.exists(cache_file):
    with open(cache_file, 'r') as f:
        cached = json.load(f)
    return cached

# Expensive operation
result = expensive_operation()
with open(cache_file, 'w') as f:
    json.dump(result, f)
return result
```

### 3. Limit Data Size

```python
# Always limit large datasets
data = await callMCPTool('getLargeDataset', {})
# Limit to reasonable size
limited = data[:100]  # First 100 items
return limited
```

## Common Patterns

### Pattern 1: Fetch and Summarize

```python
# Fetch data
data = await callMCPTool('fetchData', {'query': query})

# Summarize in sandbox
summary = {
    "count": len(data),
    "key_points": [item['key'] for item in data[:5]]
}

print(json.dumps(summary))
```

### Pattern 2: Multi-Tool Chain

```python
# Chain multiple tools
step1 = await callMCPTool('tool1', {})
step2 = await callMCPTool('tool2', {'input': step1['output']})
final = await callMCPTool('tool3', {'input': step2['output']})

# Return only final result
print(final['result'])
```

### Pattern 3: Error Recovery

```python
try:
    result = await callMCPTool('primaryTool', {})
except Exception as e:
    # Fallback
    result = await callMCPTool('fallbackTool', {})
    result['note'] = 'Used fallback due to error'

return result
```

## Security Checklist

Before deploying tool code, verify:

- [ ] No forbidden imports (`os`, `subprocess`, `sys`, etc.)
- [ ] File access restricted to workspace
- [ ] Input validation for all parameters
- [ ] Error handling doesn't leak sensitive info
- [ ] Large outputs are filtered/summarized
- [ ] Temporary files are cleaned up
- [ ] No hardcoded credentials or secrets
- [ ] Code passes AST validation

## Performance Checklist

- [ ] Large outputs filtered to <500 tokens
- [ ] Multi-tool workflows combined when possible
- [ ] Unnecessary data not returned to LLM
- [ ] Caching used for expensive operations
- [ ] Batch operations instead of loops
- [ ] Resource limits respected (timeout, memory)

## Testing Your Tool Code

1. **Test locally:**
   ```python
   from llmhive.app.mcp2 import CodeSandbox, SandboxConfig
   
   sandbox = CodeSandbox(SandboxConfig(), "test")
   result = await sandbox.execute_python(your_code)
   assert result["status"] == "success"
   ```

2. **Test security:**
   ```python
   from llmhive.app.mcp2 import SecurityValidator
   
   validator = SecurityValidator()
   is_safe, violations = validator.validate_code(your_code)
   assert is_safe, f"Violations: {violations}"
   ```

3. **Test token savings:**
   ```python
   from llmhive.app.mcp2 import ContextOptimizer
   
   optimizer = ContextOptimizer(max_output_tokens=500)
   filtered = optimizer.filter_large_output(your_output)
   savings = optimizer.calculate_token_savings(len(str(your_output)), len(filtered))
   assert savings["savings_percent"] > 90
   ```

