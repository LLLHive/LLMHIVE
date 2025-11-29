# MCP (Model Context Protocol) Integration

This directory contains the MCP server implementation for LLMHive, enabling agents to use external tools and resources.

## Overview

The MCP integration allows LLMHive orchestration agents to:
- Use external tools (web search, database queries, file operations, etc.)
- Access real-time data sources
- Perform actions (send emails, create calendar events, etc.)
- Track tool usage and metrics

## Architecture

```
Orchestrator
    ↓
MCP Client
    ↓
Tool Registry (10+ tools)
    ↓
Tool Execution
    ↓
Usage Tracking
```

## Available Tools

### Core Tools
- `web_search` - Search the web for information
- `database_query` - Query knowledge base/database
- `read_file` - Read files from safe directories
- `write_file` - Write files to safe directories
- `list_files` - List directory contents
- `api_call` - Make HTTP API calls (HTTPS only)
- `knowledge_search` - Search knowledge base
- `knowledge_add` - Add content to knowledge base

### Communication Tools
- `send_email` - Send emails (requires email service)
- `create_calendar_event` - Create calendar events (requires calendar service)
- `list_calendar_events` - List calendar events (requires calendar service)

## Tool Permissions

Tools are restricted by agent role:
- **Researcher**: web_search, database_query, api_call, knowledge_search
- **Critic**: database_query, read_file, knowledge_search
- **Editor**: read_file, write_file, list_files, knowledge_search
- **Fact Checker**: web_search, database_query, api_call, knowledge_search
- **Analyst**: database_query, api_call, read_file, knowledge_search
- **Lead**: All tools (full access)

## Usage

### In Orchestration

Tools are automatically available to agents during orchestration. Agents can include tool calls in their responses:

```
TOOL_CALL: {"tool": "web_search", "arguments": {"query": "quantum computing", "max_results": 5}}
```

The orchestrator will:
1. Detect tool calls
2. Check permissions
3. Execute tools
4. Incorporate results into responses

### API Endpoints

- `GET /api/v1/mcp/tools` - List all tools
- `GET /api/v1/mcp/tools/stats` - Get usage statistics
- `GET /api/v1/mcp/tools/{tool_name}/stats` - Get specific tool stats
- `GET /api/v1/mcp/agents/{agent_role}/stats` - Get agent tool usage

## Configuration

Set `MCP_SERVER_URL` environment variable to connect to external MCP server (optional).

## Security

- Role-based tool permissions
- Safe file system paths
- HTTPS-only for external API calls
- File size limits
- Path validation

## Files

- `client.py` - MCP client for tool usage
- `tool_registry.py` - Tool registration system
- `permissions.py` - Permission management
- `tool_parser.py` - Tool call parsing
- `tool_usage_tracker.py` - Usage tracking
- `agent_helper.py` - Agent tool helper
- `server.py` - MCP server (external connections)
- `tools/` - Tool implementations

