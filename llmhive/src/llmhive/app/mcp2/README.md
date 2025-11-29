# MCP 2.0 Code-Executor System

## Overview

The MCP 2.0 Code-Executor System is a production-grade implementation of the Model Context Protocol 2.0 architecture that uses code execution instead of direct tool calls. This approach dramatically reduces token usage (up to ~98% savings) by having the model write and run code to use tools instead of calling tools directly.

## Quick Start

### Prerequisites

- Python 3.10+
- Docker (optional, for containerized deployment)
- MCP client configured (see main LLMHive documentation)

### Running Locally

1. **Install dependencies:**
   ```bash
   pip install -e "llmhive[dev]"
   ```

2. **Start the MCP 2.0 orchestrator:**
   ```python
   from llmhive.app.mcp2 import MCP2Orchestrator, SandboxConfig
   from llmhive.app.mcp.client import MCPClient
   
   # Initialize MCP client
   mcp_client = MCPClient()
   await mcp_client.initialize()
   
   # Create orchestrator
   orchestrator = MCP2Orchestrator(
       mcp_client=mcp_client,
       sandbox_config=SandboxConfig(timeout_seconds=5.0),
   )
   
   await orchestrator.initialize_tools()
   ```

3. **Configure LLMHive to use MCP 2.0:**
   ```python
   # In orchestrator.py or main.py
   orchestrator.mcp2_enabled = True
   orchestrator.mcp2_orchestrator = orchestrator
   ```

## Architecture

### Core Components

1. **Virtual File System** (`filesystem.py`)
   - Emulated file system for sandboxed code execution
   - Tool abstraction as files (servers as directories, tools as files)
   - Workspace directory for state persistence

2. **Secure Sandbox** (`sandbox.py`)
   - Isolated execution environment
   - Resource limits (timeout, memory, CPU)
   - Network control and security restrictions

3. **Code Executor** (`executor.py`)
   - Coordinates code execution in sandbox
   - Handles tool calls from within executed code
   - Manages execution lifecycle

4. **Context Optimizer** (`context_optimizer.py`)
   - Filters and summarizes large outputs
   - Reduces token usage by processing data in sandbox
   - Supports multiple filtering strategies

5. **Tool Abstraction** (`tool_abstraction.py`)
   - File-based tool API
   - Credential security (agent never sees raw secrets)
   - Tool stub generation

6. **Orchestrator** (`orchestrator.py`)
   - Main integration point
   - Session management
   - Tool initialization and discovery

7. **Monitoring** (`monitoring.py`)
   - Execution logging
   - Metrics collection
   - Anomaly detection

8. **Security** (`security.py`)
   - Code validation
   - Security auditing
   - Path sanitization

## Usage

### Basic Setup

```python
from llmhive.app.mcp2 import (
    MCP2Orchestrator,
    SandboxConfig,
    MCPToolClient,
)

# Initialize MCP client (existing)
mcp_client = MCPClient()

# Create orchestrator
sandbox_config = SandboxConfig(
    timeout_seconds=5.0,
    memory_limit_mb=512,
    allow_network=False,
)

orchestrator = MCP2Orchestrator(
    mcp_client=mcp_client,
    sandbox_config=sandbox_config,
    max_output_tokens=500,
)

# Initialize tools
await orchestrator.initialize_tools()

# Create session
session_token = orchestrator.create_session()

# Execute agent code
code = """
# Agent writes code to use tools
result = await callMCPTool('getDocument', {'documentId': '123'})
print(f"Document: {result}")
"""

result = await orchestrator.execute_agent_code(
    code=code,
    session_token=session_token,
    language="python",
)

print(f"Success: {result.success}")
print(f"Output: {result.output}")
print(f"Tokens saved: {result.tokens_saved}")
```

### Tool Discovery

The agent can discover tools by browsing the file system:

```python
# List available servers
servers = orchestrator.tool_fs.list_servers()
# ['google-drive', 'salesforce', ...]

# List tools for a server
tools = orchestrator.tool_fs.list_tools('google-drive')
# ['getDocument', 'updateDocument', ...]

# Read tool code
tool_code = orchestrator.tool_fs.get_tool_code('google-drive', 'getDocument')
# Shows TypeScript stub with usage example
```

### Context Optimization

Large outputs are automatically filtered:

```python
from llmhive.app.mcp2 import ContextOptimizer

optimizer = ContextOptimizer(max_output_tokens=500)

# Large data (10,000 rows)
large_data = {"rows": [{"id": i} for i in range(10000)]}

# Filter to summary
filtered = optimizer.filter_large_output(large_data, strategy="summarize")
# Returns: "List with 10000 items: First 3: [...], Last 3: [...]"

# Calculate savings
savings = optimizer.calculate_token_savings(
    original_size=len(str(large_data)),
    filtered_size=len(filtered)
)
# savings["tokens_saved"] ≈ 24,000 tokens
```

## Security

### Sandbox Isolation

- Each execution runs in an isolated workspace
- Resource limits prevent resource exhaustion
- Network access is restricted by default
- Dangerous operations are blocked

### Code Validation

```python
from llmhive.app.mcp2 import SecurityValidator

validator = SecurityValidator()
is_safe, violations = validator.validate_code(code)

if not is_safe:
    print(f"Security violations: {violations}")
```

### Security Auditing

```python
from llmhive.app.mcp2 import SecurityAuditor

auditor = SecurityAuditor()
auditor.record_violation(
    violation_type="dangerous_import",
    details="Attempted to import subprocess",
    session_token=session_token,
    code_snippet=code
)

report = auditor.get_security_report()
```

## Monitoring

### Execution Logging

```python
from llmhive.app.mcp2 import MCP2Monitor

monitor = MCP2Monitor(enable_debug=True)

monitor.log_execution(
    session_token=session_token,
    execution_id="exec-1",
    code=code,
    language="python",
    result=result,
    execution_time_ms=100.0,
    tokens_saved=500,
)

# Get metrics
metrics = monitor.get_metrics()
print(f"Total executions: {metrics['total_executions']}")
print(f"Success rate: {metrics['success_rate']}")
print(f"Total tokens saved: {metrics['total_tokens_saved']}")
```

### Metrics

The monitor tracks:
- Total executions
- Success/failure rates
- Token savings
- Average execution time
- Tools called

## Performance

### Token Savings

The system achieves significant token savings by:
1. **On-demand tool loading**: Agent reads only needed tool files (~2k tokens) instead of all tools (~150k tokens)
2. **Data filtering**: Large outputs are processed in sandbox and only summaries returned (~500 tokens instead of 50k+)
3. **Single-step workflows**: Multiple tools called in one execution, avoiding intermediate context

### Benchmarking

```python
# Track performance
result = await orchestrator.execute_agent_code(...)

print(f"Execution time: {result.execution_time_ms}ms")
print(f"Tokens saved: {result.tokens_saved}")
print(f"Tools called: {result.tools_called}")
```

## Configuration

### Sandbox Configuration

```python
config = SandboxConfig(
    timeout_seconds=5.0,          # Max execution time
    memory_limit_mb=512,           # Memory limit
    cpu_limit_percent=50.0,        # CPU limit
    allow_network=False,           # Network access
    allowed_hosts=[],              # Whitelist of hosts
    allowed_modules=[              # Allowed Python modules
        "json",
        "os",
        "pathlib",
        # ...
    ],
    workspace_size_mb=100,         # Workspace size limit
    max_file_size_mb=10,           # Max file size
)
```

## CI/CD

The system includes automated testing and deployment:

- **Unit Tests**: Test individual components
- **Integration Tests**: Test full execution flow
- **Security Scans**: Bandit and safety checks
- **Performance Benchmarks**: Track token savings and latency

See `.github/workflows/mcp2-ci.yml` for CI/CD configuration.

## Best Practices

1. **Always validate code** before execution
2. **Use context optimization** for large outputs
3. **Monitor executions** for anomalies
4. **Keep sandbox config strict** in production
5. **Audit security events** regularly
6. **Version control prompts** and code templates

## Troubleshooting

### Execution Timeouts

If executions timeout frequently:
- Increase `timeout_seconds` in sandbox config
- Check for infinite loops in agent code
- Review resource limits

### Token Usage Regression

If token savings decrease:
- Check context optimizer settings
- Verify filtering strategies are applied
- Review tool discovery patterns

### Security Violations

If violations are detected:
- Review agent prompts
- Check tool call patterns
- Update security validator patterns

## Virtual File System Structure

The sandbox uses a virtual file system for tool discovery and workspace isolation:

```
/tmp/mcp2_vfs/
├── servers/              # MCP server tool stubs
│   ├── google-drive/
│   │   ├── .server.json  # Server metadata
│   │   ├── getDocument.ts
│   │   └── updateDocument.ts
│   └── salesforce/
│       ├── .server.json
│       ├── getRecord.ts
│       └── updateRecord.ts
└── workspace/            # Agent workspace (per session)
    ├── session-abc123/
    │   ├── temp_data.json
    │   └── results.txt
    └── session-def456/
        └── ...
```

### Tool Discovery Flow

1. Agent lists `servers/` directory to find available services
2. Reads specific tool files (e.g., `servers/google-drive/getDocument.ts`)
3. Each tool file contains:
   - Function signature with TypeScript types
   - Usage example
   - Description and parameter schema
4. Agent writes code using the tool function
5. Code executes in sandbox, calling `callMCPTool()` internally

### Workspace Isolation

Each session gets an isolated workspace directory:
- Files written in one session are not visible to others
- Workspace is cleaned up after session ends
- Agent can persist state within a session using the workspace

## Step-by-Step Example

### User Query
```
"Fetch the document with ID 'doc123' from Google Drive and summarize it"
```

### Agent Workflow

1. **Tool Discovery:**
   ```python
   # Agent code (generated by LLM)
   # List available servers
   servers = list_directory('servers/')
   # ['google-drive', 'salesforce', ...]
   
   # Read tool file
   tool_code = read_file('servers/google-drive/getDocument.ts')
   # Shows: export async function getDocument(params: {documentId: string})
   ```

2. **Code Generation:**
   ```python
   # Agent writes code to use the tool
   code = """
   # Fetch document
   doc = await callMCPTool('getDocument', {'documentId': 'doc123'})
   
   # Process in sandbox (not sent to LLM)
   content = doc['content']
   summary = content[:500]  # First 500 chars
   
   # Return concise result
   print(f"Summary: {summary}")
   """
   ```

3. **Execution:**
   ```python
   result = await orchestrator.execute_agent_code(
       code=code,
       session_token=session_token,
       language="python",
   )
   ```

4. **Result:**
   - Original document: ~50,000 tokens
   - Returned summary: ~500 tokens
   - **Token savings: 99%**

## Testing Guide

### Running Tests

```bash
# Run all MCP 2.0 tests
pytest llmhive/tests/test_mcp2_*.py -v

# Run specific test suite
pytest llmhive/tests/test_mcp2_system.py -v
pytest llmhive/tests/test_mcp2_security_edge_cases.py -v

# Run with coverage
pytest llmhive/tests/test_mcp2_*.py --cov=llmhive/app/mcp2 --cov-report=html
```

### Test Configuration

Some tests require environment variables:
```bash
export MCP2_ENABLE_DEBUG=true  # Enable debug logging
export MCP2_SANDBOX_TIMEOUT=5  # Override default timeout
```

### Adding New Tests

1. **Unit Test Example:**
   ```python
   def test_new_feature():
       from llmhive.app.mcp2 import YourModule
       # Test implementation
   ```

2. **Integration Test Example:**
   ```python
   @pytest.mark.asyncio
   async def test_end_to_end_workflow():
       orchestrator = MCP2Orchestrator(...)
       # Test full workflow
   ```

3. **Security Test Example:**
   ```python
   @pytest.mark.asyncio
   async def test_security_violation():
       sandbox = CodeSandbox(...)
       result = await sandbox.execute_python("import os")
       assert result["status"] != "success"
   ```

## Adding New Tools

### 1. Create Tool Stub

```python
from llmhive.app.mcp2 import ToolStubGenerator

tool_definition = {
    "name": "myNewTool",
    "description": "Does something useful",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
            "param2": {"type": "number"}
        },
        "required": ["param1"]
    }
}

# Generate TypeScript stub
ts_stub = ToolStubGenerator.generate_typescript_stub(tool_definition)

# Generate Python stub
py_stub = ToolStubGenerator.generate_python_stub(tool_definition)
```

### 2. Register Tool

```python
# In orchestrator initialization
tools = [tool_definition]
orchestrator.tool_fs.register_server("my-server", tools)
```

### 3. Update Tool Registry

If using MCP tool registry:
```python
from llmhive.app.mcp.tool_registry import get_tool_registry
registry = get_tool_registry()
registry.register("my-server", "myNewTool", tool_definition)
```

## Best Practices

See `docs/mcp2_best_practices.md` for detailed guidelines on:
- Writing safe tool code
- Optimizing for token usage
- Handling errors gracefully
- Security considerations
- Performance optimization

## Future Enhancements

- TypeScript/Node.js sandbox support
- Container-based isolation (Docker/gVisor)
- Advanced code analysis
- Multi-language execution
- Distributed execution

