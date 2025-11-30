# SDK Server Proposal for LLMHive

**Date:** November 17, 2025  
**Status:** Proposal for Review

---

## 🎯 **EXECUTIVE SUMMARY**

Adding an SDK server to LLMHive would significantly improve developer experience and adoption. This document outlines the value proposition, architecture options, and implementation recommendations.

---

## 💡 **WHY AN SDK SERVER?**

### **Current State:**
- REST API with complex orchestration endpoints
- Multiple protocols (hrm, prompt-diffusion, deep-conf, adaptive-ensemble)
- Billing/subscription APIs
- Usage tracking APIs
- Requires developers to understand REST, authentication, request/response formats

### **Benefits of SDK Server:**

1. **Improved Developer Experience**
   - Simple, intuitive API calls instead of complex REST requests
   - Type-safe interfaces (especially for TypeScript/Python)
   - Auto-completion and IDE support
   - Built-in error handling

2. **Faster Integration**
   - Developers can start using LLMHive in minutes, not hours
   - Reduced learning curve
   - Example code and documentation built-in

3. **Multi-Language Support**
   - Python SDK (most important for AI/ML developers)
   - JavaScript/TypeScript SDK (for web developers)
   - Go SDK (for backend services)
   - Ruby SDK (for Rails developers)

4. **Version Management**
   - SDK can handle API versioning gracefully
   - Backward compatibility management
   - Deprecation warnings

5. **Enhanced Features**
   - Streaming support (built-in)
   - Retry logic (automatic)
   - Rate limiting (transparent)
   - Request/response validation

---

## 🏗️ **ARCHITECTURE OPTIONS**

### **Option A: SDK Generation Server (Recommended)**

**Concept:** A server that generates and serves SDKs dynamically based on OpenAPI schema.

**Architecture:**
```
┌─────────────────┐
│  OpenAPI Schema │
│   (FastAPI)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SDK Generator  │
│   (Server)      │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│ Python │ │   JS   │
│  SDK   │ │  SDK   │
└────────┘ └────────┘
```

**Implementation:**
- Use OpenAPI Generator or custom generator
- Generate SDKs on-demand or pre-build
- Serve via package registries (PyPI, npm) or direct download

**Pros:**
- ✅ Always in sync with API
- ✅ Supports multiple languages
- ✅ Automated updates
- ✅ Standard tooling (OpenAPI Generator)

**Cons:**
- ⚠️ Requires OpenAPI schema maintenance
- ⚠️ Generated code may be less idiomatic

---

### **Option B: SDK Wrapper Server (Simpler)**

**Concept:** A lightweight server that wraps the REST API with a simplified interface.

**Architecture:**
```
┌──────────────┐
│   Client     │
│  (Python)    │
└──────┬───────┘
       │
       │ SDK Protocol
       │ (gRPC/GraphQL/HTTP)
       ▼
┌──────────────┐
│  SDK Server  │
│  (Wrapper)   │
└──────┬───────┘
       │
       │ REST API
       ▼
┌──────────────┐
│  LLMHive API │
└──────────────┘
```

**Implementation:**
- gRPC server (type-safe, efficient)
- GraphQL server (flexible queries)
- Simplified HTTP API (easier, less efficient)

**Pros:**
- ✅ Can optimize/transform requests
- ✅ Can add caching, batching
- ✅ Can simplify complex operations
- ✅ Language-agnostic protocol

**Cons:**
- ⚠️ Additional server to maintain
- ⚠️ Potential latency overhead
- ⚠️ More infrastructure complexity

---

### **Option C: Direct SDK Libraries (Most Common)**

**Concept:** Traditional approach - ship SDK libraries directly (no server).

**Architecture:**
```
┌──────────────┐
│   Client     │
│  (Python)    │
└──────┬───────┘
       │
       │ HTTP/REST
       ▼
┌──────────────┐
│  LLMHive API │
└──────────────┘
```

**Implementation:**
- Python package (`llmhive-python`)
- JavaScript package (`@llmhive/sdk`)
- Published to PyPI, npm, etc.

**Pros:**
- ✅ No additional server
- ✅ Direct API access
- ✅ Standard approach
- ✅ Full control over SDK design

**Cons:**
- ⚠️ Manual maintenance
- ⚠️ Need to update SDKs when API changes
- ⚠️ Multiple codebases to maintain

---

## 🎯 **RECOMMENDED APPROACH: Hybrid (A + C)**

**Best of both worlds:**
1. **Generate SDKs** from OpenAPI schema (automated)
2. **Ship as packages** to PyPI/npm (standard)
3. **Optional SDK server** for advanced features (future)

**Phase 1: Direct SDK Libraries (Immediate)**
- Python SDK (`llmhive-python`)
- JavaScript/TypeScript SDK (`@llmhive/sdk`)
- Generated from OpenAPI schema
- Published to package registries

**Phase 2: SDK Server (Future Enhancement)**
- Add gRPC/GraphQL server for advanced use cases
- Streaming, batching, caching
- Real-time features

---

## 📋 **IMPLEMENTATION PLAN**

### **Phase 1: OpenAPI Schema & SDK Generation**

#### **Step 1: Enhance OpenAPI Schema**
**File:** `llmhive/src/llmhive/app/main.py`

```python
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="LLMHive API",
        version="1.0.0",
        description="Multi-model orchestration platform",
        routes=app.routes,
    )
    # Add custom schemas, examples, etc.
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

#### **Step 2: SDK Generation Setup**
**New Directory:** `llmhive/sdk/`

```
llmhive/sdk/
├── generator/
│   ├── __init__.py
│   ├── openapi_generator.py  # Wrapper for OpenAPI Generator
│   └── templates/            # Custom templates
├── python/
│   ├── llmhive/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── orchestration.py
│   │   ├── billing.py
│   │   └── models.py
│   ├── setup.py
│   └── README.md
└── javascript/
    ├── src/
    │   ├── index.ts
    │   ├── client.ts
    │   ├── orchestration.ts
    │   └── billing.ts
    ├── package.json
    └── README.md
```

#### **Step 3: Python SDK Implementation**

**File:** `llmhive/sdk/python/llmhive/client.py`

```python
"""LLMHive Python SDK - Main Client"""
from typing import Optional, List, Dict, Any
import httpx

class LLMHiveClient:
    """Main client for LLMHive API."""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.llmhive.com",
        timeout: int = 300,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=self.timeout,
        )
    
    async def orchestrate(
        self,
        prompt: str,
        models: Optional[List[str]] = None,
        protocol: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Orchestrate multiple LLMs for a prompt.
        
        Args:
            prompt: The prompt to orchestrate
            models: Optional list of model IDs
            protocol: Optional protocol (hrm, prompt-diffusion, deep-conf, adaptive-ensemble)
            user_id: Optional user identifier for billing
            
        Returns:
            Orchestration response with artifacts
        """
        response = await self.client.post(
            "/api/v1/orchestration/",
            json={
                "prompt": prompt,
                "models": models,
                "protocol": protocol,
                "user_id": user_id,
                **kwargs
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def stream_orchestrate(
        self,
        prompt: str,
        models: Optional[List[str]] = None,
        protocol: Optional[str] = None,
        **kwargs
    ):
        """Stream orchestration results."""
        async with self.client.stream(
            "POST",
            "/api/v1/orchestration/",
            json={
                "prompt": prompt,
                "models": models,
                "protocol": protocol,
                **kwargs
            }
        ) as response:
            async for chunk in response.aiter_text():
                yield chunk
    
    # Billing methods
    async def get_subscription(self, user_id: str):
        """Get user's subscription."""
        response = await self.client.get(f"/api/v1/billing/subscriptions/user/{user_id}")
        response.raise_for_status()
        return response.json()
    
    async def get_usage(self, user_id: str):
        """Get user's usage summary."""
        response = await self.client.get(f"/api/v1/billing/usage/{user_id}")
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()
```

**Usage Example:**
```python
import asyncio
from llmhive import LLMHiveClient

async def main():
    async with LLMHiveClient(api_key="your-api-key") as client:
        # Simple orchestration
        result = await client.orchestrate(
            "Explain quantum computing",
            models=["gpt-4o", "claude-3-opus"],
            protocol="adaptive-ensemble"
        )
        print(result["final_response"]["content"])
        
        # Stream results
        async for chunk in client.stream_orchestrate(
            "Write a story",
            protocol="hrm"
        ):
            print(chunk, end="")

asyncio.run(main())
```

#### **Step 4: JavaScript/TypeScript SDK**

**File:** `llmhive/sdk/javascript/src/client.ts`

```typescript
/** LLMHive TypeScript SDK - Main Client */
export interface OrchestrationRequest {
  prompt: string;
  models?: string[];
  protocol?: 'hrm' | 'prompt-diffusion' | 'deep-conf' | 'adaptive-ensemble';
  user_id?: string;
}

export interface OrchestrationResponse {
  final_response: {
    content: string;
    model: string;
  };
  plan: any;
  quality_assessments: any;
  // ... other fields
}

export class LLMHiveClient {
  private baseUrl: string;
  private apiKey: string;
  
  constructor(apiKey: string, baseUrl: string = 'https://api.llmhive.com') {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
  }
  
  async orchestrate(request: OrchestrationRequest): Promise<OrchestrationResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/orchestration/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  async *streamOrchestrate(request: OrchestrationRequest): AsyncGenerator<string> {
    const response = await fetch(`${this.baseUrl}/api/v1/orchestration/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    
    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      yield new TextDecoder().decode(value);
    }
  }
  
  async getSubscription(userId: string) {
    const response = await fetch(
      `${this.baseUrl}/api/v1/billing/subscriptions/user/${userId}`,
      {
        headers: { 'Authorization': `Bearer ${this.apiKey}` },
      }
    );
    return response.json();
  }
}
```

---

## 🚀 **RECOMMENDED IMPLEMENTATION STRUCTURE**

### **Directory Structure:**
```
llmhive/
├── src/llmhive/app/          # Existing API
├── sdk/                      # NEW: SDK code
│   ├── generator/            # SDK generation tools
│   ├── python/               # Python SDK
│   ├── javascript/           # JavaScript/TypeScript SDK
│   └── scripts/              # Build/publish scripts
└── tests/
    └── sdk/                  # SDK tests
```

### **Key Files to Create:**

1. **`llmhive/sdk/generator/openapi_generator.py`**
   - Wraps OpenAPI Generator CLI
   - Generates SDKs for multiple languages
   - Customizes templates

2. **`llmhive/sdk/python/setup.py`**
   - Python package configuration
   - Dependencies (httpx, pydantic)
   - Entry points

3. **`llmhive/sdk/javascript/package.json`**
   - npm package configuration
   - Dependencies (axios, typescript)
   - Build scripts

4. **`llmhive/sdk/scripts/build_sdks.sh`**
   - Builds all SDKs
   - Runs tests
   - Generates documentation

5. **`llmhive/sdk/scripts/publish_sdks.sh`**
   - Publishes to PyPI/npm
   - Version management
   - Release notes

---

## 📊 **VALUE ASSESSMENT**

### **High Value:**
- ✅ **Developer Adoption** - Easier integration = more users
- ✅ **Time to First Value** - Developers productive faster
- ✅ **Support Burden** - Fewer API questions
- ✅ **Competitive Advantage** - Most AI platforms lack good SDKs

### **Medium Value:**
- ⚠️ **Maintenance Overhead** - Need to keep SDKs updated
- ⚠️ **Documentation** - Need SDK-specific docs
- ⚠️ **Testing** - Need SDK test suite

### **Low Risk:**
- ✅ Can start simple (Python only)
- ✅ Can use OpenAPI Generator (proven tooling)
- ✅ Can iterate based on feedback

---

## 🎯 **RECOMMENDATION**

### **✅ YES - Implement SDK Server (Phase 1: Direct SDKs)**

**Rationale:**
1. **High ROI** - Significant developer experience improvement
2. **Low Risk** - Start with Python SDK, expand later
3. **Standard Practice** - All major APIs have SDKs
4. **Competitive** - Differentiates LLMHive from competitors

**Implementation Priority:**
1. **Phase 1 (Immediate):** Python SDK + TypeScript SDK
2. **Phase 2 (Future):** SDK generation server
3. **Phase 3 (Future):** gRPC/GraphQL server for advanced features

**Estimated Effort:**
- Python SDK: 1-2 weeks
- TypeScript SDK: 1 week
- SDK Generation: 1 week
- **Total: 3-4 weeks**

---

## 📝 **NEXT STEPS**

1. **Review this proposal**
2. **Approve approach** (Direct SDKs vs SDK Server)
3. **Prioritize languages** (Python first, then TypeScript)
4. **Create implementation tickets**
5. **Begin Phase 1 implementation**

---

## ✅ **DECISION POINTS**

**Questions to Answer:**
1. Which languages are highest priority? (Python, TypeScript, Go, Ruby?)
2. Should we use OpenAPI Generator or custom implementation?
3. Should SDKs be generated or hand-written?
4. What's the release cadence? (With each API version?)
5. Where to host? (PyPI, npm, GitHub Releases?)

---

**Status:** Ready for Review & Authorization  
**Prepared by:** AI Assistant  
**Date:** November 17, 2025

