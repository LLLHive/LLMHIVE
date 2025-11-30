# MCP Server Integration Proposal for LLMHive

**Date:** November 17, 2025  
**Status:** Proposal for Review

---

## 🎯 **EXECUTIVE SUMMARY**

Integrating an MCP (Model Context Protocol) server into LLMHive would enable our orchestration agents to use external tools, access data sources, and perform actions autonomously. This aligns perfectly with our multi-agent architecture and would significantly enhance agent capabilities.

---

## 💡 **WHAT IS MCP (MODEL CONTEXT PROTOCOL)?**

MCP is a protocol developed by Anthropic that standardizes how AI assistants connect to external tools and data sources. It enables:

- **Tool Calling**: Agents can invoke external tools (APIs, databases, file systems, etc.)
- **Resource Access**: Agents can read from data sources (databases, files, web APIs)
- **Prompts**: Pre-defined prompt templates for common tasks
- **Standardized Interface**: Unified protocol for tool integration

**Key Benefits:**
- ✅ Agents can perform actions, not just generate text
- ✅ Access to real-time data and external services
- ✅ Standardized tool integration
- ✅ Secure, scoped access to resources

---

## 🏗️ **ARCHITECTURE INTEGRATION**

### **Current LLMHive Architecture:**
```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  FastAPI    │
│   Server    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Orchestrator│
│  (Agents)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Providers  │
│  (LLMs)     │
└─────────────┘
```

### **With MCP Server Integration:**
```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  FastAPI    │
│   Server    │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌──────────────┐
│ Orchestrator│◄────►│  MCP Server  │
│  (Agents)   │      │  (Tools)     │
└──────┬──────┘      └──────┬───────┘
       │                    │
       │                    ▼
       │            ┌──────────────┐
       │            │   External   │
       │            │   Services   │
       │            │  (APIs, DBs) │
       │            └──────────────┘
       ▼
┌─────────────┐
│  Providers  │
│  (LLMs)     │
└─────────────┘
```

---

## 🎯 **USE CASES FOR LLMHIVE**

### **1. Agent Tool Usage**
Our orchestration agents (Researcher, Critic, Editor, etc.) could use tools:

- **Researcher Agent**: Web search, database queries, API calls
- **Fact Checker**: Real-time data verification, source validation
- **Analyst Agent**: Data analysis tools, chart generation
- **Editor Agent**: File operations, document formatting

### **2. Real-Time Data Access**
- Database queries (user data, knowledge base)
- API integrations (weather, stocks, news)
- File system access (document retrieval)
- Web scraping (with proper permissions)

### **3. Action Execution**
- Send emails/notifications
- Create calendar events
- Update databases
- Trigger workflows

### **4. Enhanced Orchestration**
- Agents can gather real-time context before responding
- Multi-step workflows with tool usage
- Dynamic data-driven responses

---

## 🏗️ **IMPLEMENTATION ARCHITECTURE**

### **Option A: MCP Server as Separate Service (Recommended)**

**Structure:**
```
llmhive/
├── src/llmhive/app/
│   ├── orchestrator.py      # Existing
│   ├── mcp/                 # NEW: MCP Integration
│   │   ├── __init__.py
│   │   ├── client.py         # MCP client for agents
│   │   ├── tool_registry.py  # Tool registration
│   │   └── handlers.py       # Tool handlers
│   └── tools/                # NEW: Tool implementations
│       ├── __init__.py
│       ├── web_search.py
│       ├── database.py
│       ├── file_system.py
│       └── api_client.py
└── mcp_server/              # NEW: Standalone MCP server
    ├── __init__.py
    ├── server.py             # MCP server implementation
    ├── tools/                # Tool definitions
    └── resources/            # Resource providers
```

**Pros:**
- ✅ Separation of concerns
- ✅ Can scale independently
- ✅ Standard MCP protocol
- ✅ Can be used by other clients

**Cons:**
- ⚠️ Additional service to maintain
- ⚠️ Network latency

---

### **Option B: Embedded MCP Server (Simpler)**

**Structure:**
```
llmhive/
├── src/llmhive/app/
│   ├── orchestrator.py
│   ├── mcp/                 # NEW: Embedded MCP
│   │   ├── __init__.py
│   │   ├── server.py         # Embedded MCP server
│   │   ├── tools.py          # Tool implementations
│   │   └── registry.py       # Tool registry
```

**Pros:**
- ✅ Simpler deployment
- ✅ No network overhead
- ✅ Direct integration

**Cons:**
- ⚠️ Less flexible
- ⚠️ Harder to scale

---

## 📋 **RECOMMENDED IMPLEMENTATION**

### **Phase 1: MCP Client Integration (Embedded)**

Start with embedded MCP client that agents can use:

**File:** `llmhive/src/llmhive/app/mcp/__init__.py`
```python
"""MCP (Model Context Protocol) integration for LLMHive agents."""
from .client import MCPClient
from .tool_registry import ToolRegistry, register_tool

__all__ = ["MCPClient", "ToolRegistry", "register_tool"]
```

**File:** `llmhive/src/llmhive/app/mcp/client.py`
```python
"""MCP client for agent tool usage."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for interacting with MCP servers and tools."""
    
    def __init__(self, server_url: Optional[str] = None):
        """Initialize MCP client.
        
        Args:
            server_url: Optional MCP server URL. If None, uses embedded tools.
        """
        self.server_url = server_url
        self.tools: Dict[str, Dict] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize client and discover available tools."""
        if self._initialized:
            return
        
        if self.server_url:
            # Connect to external MCP server
            await self._connect_to_server()
        else:
            # Use embedded tools
            await self._load_embedded_tools()
        
        self._initialized = True
        logger.info(f"MCP client initialized with {len(self.tools)} tools")
    
    async def _load_embedded_tools(self) -> None:
        """Load embedded tool implementations."""
        from .tools import get_embedded_tools
        self.tools = await get_embedded_tools()
    
    async def _connect_to_server(self) -> None:
        """Connect to external MCP server."""
        # TODO: Implement MCP protocol client
        # This would use stdio or HTTP transport
        pass
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Call a tool by name.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        if not self._initialized:
            await self.initialize()
        
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        tool = self.tools[tool_name]
        handler = tool.get("handler")
        
        if not handler:
            raise ValueError(f"Tool '{tool_name}' has no handler")
        
        try:
            result = await handler(**arguments)
            return {
                "tool": tool_name,
                "result": result,
                "success": True,
            }
        except Exception as exc:
            logger.error(f"Tool '{tool_name}' failed: {exc}")
            return {
                "tool": tool_name,
                "error": str(exc),
                "success": False,
            }
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools."""
        return [
            {
                "name": name,
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {}),
            }
            for name, tool in self.tools.items()
        ]
```

**File:** `llmhive/src/llmhive/app/mcp/tools/__init__.py`
```python
"""Embedded tool implementations for MCP."""
from .web_search import web_search_tool
from .database import database_query_tool
from .file_system import file_read_tool, file_write_tool
from .api_client import api_call_tool

async def get_embedded_tools() -> Dict[str, Dict]:
    """Get all embedded tools."""
    return {
        "web_search": {
            "name": "web_search",
            "description": "Search the web for information",
            "parameters": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "default": 5},
            },
            "handler": web_search_tool,
        },
        "database_query": {
            "name": "database_query",
            "description": "Query the database",
            "parameters": {
                "query": {"type": "string", "description": "SQL query"},
            },
            "handler": database_query_tool,
        },
        "read_file": {
            "name": "read_file",
            "description": "Read a file from the file system",
            "parameters": {
                "path": {"type": "string", "description": "File path"},
            },
            "handler": file_read_tool,
        },
        "write_file": {
            "name": "write_file",
            "description": "Write content to a file",
            "parameters": {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "File content"},
            },
            "handler": file_write_tool,
        },
        "api_call": {
            "name": "api_call",
            "description": "Make an API call",
            "parameters": {
                "url": {"type": "string", "description": "API URL"},
                "method": {"type": "string", "default": "GET"},
                "headers": {"type": "object", "default": {}},
                "body": {"type": "object", "default": None},
            },
            "handler": api_call_tool,
        },
    }
```

**File:** `llmhive/src/llmhive/app/mcp/tools/web_search.py`
```python
"""Web search tool for MCP."""
from __future__ import annotations

import logging
from typing import Any, Dict

from ...services.web_research import WebResearchService

logger = logging.getLogger(__name__)


async def web_search_tool(
    query: str,
    max_results: int = 5,
) -> Dict[str, Any]:
    """Search the web for information.
    
    Args:
        query: Search query
        max_results: Maximum number of results
        
    Returns:
        Search results
    """
    try:
        web_research = WebResearchService()
        results = await web_research.search(query)
        
        return {
            "query": query,
            "results": [
                {
                    "title": doc.title,
                    "url": doc.url,
                    "snippet": doc.snippet,
                }
                for doc in results[:max_results]
            ],
            "count": len(results),
        }
    except Exception as exc:
        logger.error(f"Web search failed: {exc}")
        return {
            "query": query,
            "error": str(exc),
            "results": [],
        }
```

### **Phase 2: Agent Integration**

Modify agents to use MCP tools:

**File:** `llmhive/src/llmhive/app/agents/base.py` (Enhanced)
```python
"""Base agent with MCP tool support."""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Optional

from ..mcp.client import MCPClient
from ..services.model_gateway import model_gateway

class Agent(ABC):
    def __init__(
        self,
        model_id: str,
        role: str,
        mcp_client: Optional[MCPClient] = None,
    ):
        self.model_id = model_id
        self.role = role
        self.gateway = model_gateway
        self.mcp_client = mcp_client or MCPClient()
    
    async def use_tool(
        self,
        tool_name: str,
        arguments: Dict,
    ) -> Dict:
        """Use an MCP tool.
        
        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            
        Returns:
            Tool result
        """
        if not self.mcp_client._initialized:
            await self.mcp_client.initialize()
        
        return await self.mcp_client.call_tool(tool_name, arguments)
    
    @abstractmethod
    def _create_prompt(self, task: str, context: str) -> List[Dict[str, str]]:
        pass
    
    async def execute(self, task: str, context: str = "") -> str:
        messages = self._create_prompt(task, context)
        
        # Add tool information to context if available
        if self.mcp_client._initialized:
            tools = self.mcp_client.list_tools()
            context += f"\n\nAvailable tools: {', '.join([t['name'] for t in tools])}"
        
        response = await self.gateway.call(model_id=self.model_id, messages=messages)
        return response.content
    
    async def execute_stream(self, task: str, context: str = "") -> AsyncGenerator[str, None]:
        messages = self._create_prompt(task, context)
        async for token in self.gateway.call(model_id=self.model_id, messages=messages, stream=True):
            yield token
```

### **Phase 3: Orchestrator Integration**

Integrate MCP into orchestrator:

**File:** `llmhive/src/llmhive/app/orchestrator.py` (Enhanced)
```python
# Add to imports
from .mcp.client import MCPClient

class Orchestrator:
    def __init__(self, providers: Dict[str, LLMProvider] | None = None) -> None:
        # ... existing init ...
        
        # Initialize MCP client
        mcp_server_url = getattr(settings, "mcp_server_url", None)
        self.mcp_client = MCPClient(server_url=mcp_server_url)
        
        # Initialize agents with MCP client
        # (modify agent creation to pass mcp_client)
    
    async def orchestrate(
        self,
        prompt: str,
        models: Iterable[str] | None = None,
        *,
        context: str | None = None,
        knowledge_snippets: Sequence[str] | None = None,
        protocol: str | None = None,
        user_id: str | None = None,
        db_session: Session | None = None,
        use_tools: bool = True,  # NEW: Enable tool usage
    ) -> OrchestrationArtifacts:
        # Initialize MCP if tools are enabled
        if use_tools:
            await self.mcp_client.initialize()
            
            # Add available tools to context
            tools = self.mcp_client.list_tools()
            if tools:
                tool_context = f"\n\nAvailable tools: {', '.join([t['name'] for t in tools])}"
                context = (context or "") + tool_context
        
        # ... rest of orchestration logic ...
        
        # Agents can now use tools during execution
        # Example: Researcher agent can call web_search tool
```

---

## 🛠️ **TOOL IMPLEMENTATIONS**

### **Core Tools to Implement:**

1. **Web Search Tool**
   - Uses existing `WebResearchService`
   - Returns search results
   - Already partially implemented

2. **Database Query Tool**
   - Query knowledge base
   - Query user data (with permissions)
   - Safe SQL execution

3. **File System Tool**
   - Read files (with path restrictions)
   - Write files (with permissions)
   - List directories

4. **API Client Tool**
   - Make HTTP requests
   - With authentication
   - Rate limiting

5. **Knowledge Base Tool**
   - Search knowledge base
   - Add to knowledge base
   - Update knowledge base

6. **Billing Tool**
   - Check usage limits
   - Get subscription info
   - (Read-only for agents)

---

## 🔒 **SECURITY CONSIDERATIONS**

### **Tool Permissions:**
- **Agent Role-Based Access**: Different agents have different tool permissions
- **User Context**: Tools respect user permissions
- **Sandboxing**: File system tools restricted to safe paths
- **Rate Limiting**: API tools respect rate limits
- **Audit Logging**: All tool calls logged

### **Implementation:**
```python
class ToolPermission:
    """Tool permission system."""
    
    AGENT_PERMISSIONS = {
        "researcher": ["web_search", "database_query", "api_call"],
        "critic": ["database_query", "read_file"],
        "editor": ["read_file", "write_file"],
        "fact_checker": ["web_search", "database_query"],
    }
    
    @classmethod
    def can_use_tool(cls, agent_role: str, tool_name: str) -> bool:
        """Check if agent can use tool."""
        allowed = cls.AGENT_PERMISSIONS.get(agent_role, [])
        return tool_name in allowed
```

---

## 📊 **VALUE ASSESSMENT**

### **High Value:**
- ✅ **Enhanced Agent Capabilities** - Agents can perform actions
- ✅ **Real-Time Data** - Access to live data sources
- ✅ **Workflow Automation** - Multi-step agent workflows
- ✅ **Competitive Advantage** - Advanced agent capabilities

### **Medium Value:**
- ⚠️ **Complexity** - Additional system to maintain
- ⚠️ **Security** - Need careful permission management
- ⚠️ **Testing** - Tool integration testing required

### **Low Risk:**
- ✅ Can start with embedded tools (no external service)
- ✅ Can add tools incrementally
- ✅ Standard protocol (MCP)

---

## 🎯 **RECOMMENDATION**

### **✅ YES - Implement MCP Integration (Phased Approach)**

**Phase 1 (Immediate):**
- Embedded MCP client
- Core tools (web search, database, file system)
- Agent integration
- **Effort: 2-3 weeks**

**Phase 2 (Future):**
- Standalone MCP server
- Additional tools
- External MCP server support
- **Effort: 2-3 weeks**

**Total: 4-6 weeks**

---

## 📝 **NEXT STEPS**

1. **Review this proposal**
2. **Approve approach** (Embedded vs Standalone)
3. **Prioritize tools** (Which tools first?)
4. **Define permissions** (Agent tool access)
5. **Create implementation tickets**
6. **Begin Phase 1**

---

## ✅ **DECISION POINTS**

**Questions to Answer:**
1. Embedded or standalone MCP server?
2. Which tools are highest priority?
3. What are the security/permission requirements?
4. Should we use existing MCP libraries or implement from scratch?
5. How should tools be discovered and registered?

---

**Status:** Ready for Review & Authorization  
**Prepared by:** AI Assistant  
**Date:** November 17, 2025

