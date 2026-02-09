# API Key Intermittent Error: Root Cause & Solution

## 🔍 Problem Analysis

You're experiencing intermittent "API key not found" errors even though all environment variables are correctly configured in your deployment platform (Vercel/GCP/etc.).

### Root Cause

**Class-Level Environment Variable Loading (Anti-Pattern)**

In `llmhive/src/llmhive/app/config.py`, the `Settings` class loads environment variables at the **class definition time**:

```python
class Settings:
    # ❌ PROBLEM: These are loaded when the module is imported
    api_key: str | None = os.getenv("API_KEY")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    # ... etc.
```

### Why This Causes Intermittent Failures

1. **Serverless Cold Starts**: In serverless environments (Cloud Run, Lambda, Vercel Functions), environment variables may not be fully injected when Python modules are first imported

2. **Import Order Race Condition**: If `config.py` is imported before the runtime fully loads environment variables, `os.getenv()` returns `None`

3. **Module Caching**: Once the module is imported with `None` values, Python caches the module, so subsequent requests in the same container use the cached (broken) instance

4. **Intermittent**: Works fine after a "warm" container (where env vars were loaded), fails on cold starts

---

## 🔬 Research Evidence

Based on web research:

### 1. **Vercel Environment Variables**
- Issue: "Erratic Behavior with Environment Variables in Production" ([Vercel Community](https://community.vercel.com/t/erratic-behavior-with-environment-variables-in-production-on-vercel/2698))
- Variables may not be available at module import time
- Requires redeployment after adding/modifying variables

### 2. **Python os.getenv() Behavior**
- Environment variables must be set **before** the Python process starts
- Child processes (like Python modules) inherit env vars from parent process
- If env vars aren't in the parent process when Python starts importing, `os.getenv()` returns `None`

### 3. **FastAPI Best Practices**
- Recommended: Use **Pydantic BaseSettings** for lazy loading
- Environment variables should be read at **runtime**, not import time
- [FastAPI Docs on Settings](https://fastapi.tiangolo.com/advanced/settings)

---

## ✅ Solutions

### Solution 1: Use Pydantic BaseSettings (Recommended)

**Why**: Lazy loading, type validation, better error messages, production-ready

**Implementation**:

```python
# llmhive/src/llmhive/app/config.py

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List

class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    Uses Pydantic BaseSettings for lazy loading and validation.
    Environment variables are loaded when Settings() is instantiated,
    not when the module is imported.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars
    )
    
    # API Keys
    api_key: Optional[str] = Field(default=None, alias="API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    claude_api_key: Optional[str] = Field(default=None, alias="CLAUDE_API_KEY")
    grok_api_key: Optional[str] = Field(default=None, alias="GROK_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    deepseek_api_key: Optional[str] = Field(default=None, alias="DEEPSEEK_API_KEY")
    manus_api_key: Optional[str] = Field(default=None, alias="MANUS_API_KEY")
    together_api_key: Optional[str] = Field(default=None, alias="TOGETHERAI_API_KEY")
    
    # Pinecone
    pinecone_api_key: Optional[str] = Field(default=None, alias="PINECONE_API_KEY")
    pinecone_environment: str = Field(default="us-west1-gcp", alias="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field(default="llmhive-memory", alias="PINECONE_INDEX_NAME")
    
    # Stripe
    stripe_api_key: Optional[str] = Field(default=None, alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: Optional[str] = Field(default=None, alias="STRIPE_WEBHOOK_SECRET")
    stripe_publishable_key: Optional[str] = Field(default=None, alias="STRIPE_PUBLISHABLE_KEY")
    
    # Stripe Price IDs
    stripe_price_id_basic_monthly: Optional[str] = None
    stripe_price_id_basic_annual: Optional[str] = None
    stripe_price_id_pro_monthly: Optional[str] = None
    stripe_price_id_pro_annual: Optional[str] = None
    stripe_price_id_enterprise_monthly: Optional[str] = None
    stripe_price_id_enterprise_annual: Optional[str] = None
    
    # Google Cloud
    google_cloud_project: Optional[str] = Field(default=None, alias="GOOGLE_CLOUD_PROJECT")
    
    # Application Config
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    
    # Embedding Config
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=1536, alias="EMBEDDING_DIMENSION")
    
    # Memory Config
    memory_namespace_per_user: bool = Field(default=True, alias="MEMORY_NAMESPACE_PER_USER")
    memory_ttl_days: int = Field(default=90, alias="MEMORY_TTL_DAYS")
    memory_max_results: int = Field(default=10, alias="MEMORY_MAX_RESULTS")
    memory_min_score: float = Field(default=0.7, alias="MEMORY_MIN_SCORE")
    
    # Parse CORS origins into list
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    # Fallback for anthropic_api_key (support both env var names)
    def get_anthropic_key(self) -> Optional[str]:
        return self.anthropic_api_key or self.claude_api_key


# Create a singleton instance getter (NOT at module level!)
_settings_instance = None

def get_settings() -> Settings:
    """Get or create Settings singleton instance.
    
    This ensures settings are loaded lazily (at runtime, not import time).
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


# Backwards compatibility: expose settings instance
# But this will be lazy-loaded when accessed
def __getattr__(name):
    """Module-level attribute access for backwards compatibility."""
    if name == "settings":
        return get_settings()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
```

**Update usage throughout codebase**:

```python
# OLD WAY (breaks):
from llmhive.app.config import Settings
openai_key = Settings.openai_api_key

# NEW WAY (works):
from llmhive.app.config import get_settings
settings = get_settings()
openai_key = settings.openai_api_key
```

---

### Solution 2: Lazy Property Loading (Simpler, No Dependencies)

**Why**: Minimal changes, no new dependencies, preserves current structure

**Implementation**:

```python
# llmhive/src/llmhive/app/config.py

import os
from typing import Optional
from functools import cached_property

class Settings:
    """Application settings loaded from environment variables.
    
    Uses lazy loading via @cached_property to read env vars at runtime,
    not at module import time.
    """
    
    # Default models for orchestration
    default_models: list[str] = ["gpt-4o-mini", "claude-3-haiku"]
    
    # Lazy-loaded API keys (read on first access, not at import time)
    @cached_property
    def api_key(self) -> Optional[str]:
        return os.getenv("API_KEY")
    
    @cached_property
    def openai_api_key(self) -> Optional[str]:
        return os.getenv("OPENAI_API_KEY")
    
    @cached_property
    def anthropic_api_key(self) -> Optional[str]:
        return os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
    
    @cached_property
    def claude_api_key(self) -> Optional[str]:
        return os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    
    @cached_property
    def grok_api_key(self) -> Optional[str]:
        return os.getenv("GROK_API_KEY")
    
    @cached_property
    def gemini_api_key(self) -> Optional[str]:
        return os.getenv("GEMINI_API_KEY")
    
    @cached_property
    def deepseek_api_key(self) -> Optional[str]:
        return os.getenv("DEEPSEEK_API_KEY")
    
    @cached_property
    def manus_api_key(self) -> Optional[str]:
        return os.getenv("MANUS_API_KEY")
    
    @cached_property
    def together_api_key(self) -> Optional[str]:
        return os.getenv("TOGETHERAI_API_KEY") or os.getenv("TOGETHER_API_KEY")
    
    # Pinecone
    @cached_property
    def pinecone_api_key(self) -> Optional[str]:
        return os.getenv("PINECONE_API_KEY")
    
    @cached_property
    def pinecone_environment(self) -> str:
        return os.getenv("PINECONE_ENVIRONMENT", "us-west1-gcp")
    
    @cached_property
    def pinecone_index_name(self) -> str:
        return os.getenv("PINECONE_INDEX_NAME", "llmhive-memory")
    
    # Stripe
    @cached_property
    def stripe_api_key(self) -> Optional[str]:
        return os.getenv("STRIPE_SECRET_KEY")
    
    @cached_property
    def stripe_webhook_secret(self) -> Optional[str]:
        return os.getenv("STRIPE_WEBHOOK_SECRET")
    
    @cached_property
    def stripe_publishable_key(self) -> Optional[str]:
        return os.getenv("STRIPE_PUBLISHABLE_KEY")
    
    # ... repeat for all other config values
    
# Create a singleton instance
_settings = None

def get_settings() -> Settings:
    """Get or create Settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

# For backwards compatibility
settings = get_settings()
```

**Benefits**:
- ✅ Environment variables loaded at runtime (first access)
- ✅ Cached after first access (via `@cached_property`)
- ✅ No new dependencies
- ✅ Minimal code changes

---

### Solution 3: Quick Fix (Temporary Workaround)

**For immediate relief** while implementing a proper solution:

```python
# At the START of main.py, BEFORE any imports of config.py:

import os
import time

# Force environment variable loading with retry
def ensure_env_vars_loaded(max_retries=3, retry_delay=0.5):
    """Ensure critical env vars are loaded before proceeding."""
    required_vars = [
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
        "DEEPSEEK_API_KEY", "GROQ_API_KEY"
    ]
    
    for attempt in range(max_retries):
        loaded = [var for var in required_vars if os.getenv(var)]
        
        if loaded:  # At least one provider key is loaded
            return True
        
        # Wait and retry
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
    
    return False

# Call this BEFORE importing config
if not ensure_env_vars_loaded():
    import logging
    logging.warning("Environment variables not fully loaded on startup")

# NOW import config (after env vars are confirmed)
from .config import Settings
```

---

## 🎯 Recommended Implementation Plan

### Phase 1: Immediate (Quick Fix) ⚡
1. Add retry logic to `main.py` (Solution 3)
2. Deploy immediately to reduce intermittent errors
3. **Estimated time**: 15 minutes

### Phase 2: Proper Fix (Within 1 Week) 🔧
1. Implement Solution 1 (Pydantic BaseSettings) OR Solution 2 (Lazy Properties)
2. Update all imports throughout codebase
3. Test thoroughly in staging
4. Deploy to production
5. **Estimated time**: 2-4 hours

### Phase 3: Validation 📊
1. Monitor error rates for 48 hours
2. Check logs for "API key not found" errors
3. Verify all providers working consistently
4. Document the fix

---

## 📋 Additional Recommendations

### 1. Add Health Check Endpoint

```python
# In llmhive/src/llmhive/app/api/status.py

@router.get("/health/config")
async def config_health():
    """Check if environment variables are properly loaded."""
    from ..config import get_settings
    settings = get_settings()
    
    return {
        "status": "healthy",
        "api_keys_loaded": {
            "openai": bool(settings.openai_api_key),
            "anthropic": bool(settings.anthropic_api_key),
            "gemini": bool(settings.gemini_api_key),
            "deepseek": bool(settings.deepseek_api_key),
            "groq": bool(settings.grok_api_key),
            "pinecone": bool(settings.pinecone_api_key),
            "stripe": bool(settings.stripe_api_key),
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
```

Hit this endpoint after deployment to verify env vars loaded correctly.

### 2. Add Startup Logging

```python
# In startup_checks.py

def log_env_var_status():
    """Log which env vars are available (without exposing values)."""
    import logging
    logger = logging.getLogger(__name__)
    
    vars_to_check = [
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
        "DEEPSEEK_API_KEY", "GROQ_API_KEY", "PINECONE_API_KEY",
        "STRIPE_SECRET_KEY"
    ]
    
    for var in vars_to_check:
        value = os.getenv(var)
        if value:
            # Show first 4 and last 4 chars for confirmation
            masked = f"{value[:4]}...{value[-4:]}"
            logger.info(f"✓ {var} loaded: {masked}")
        else:
            logger.warning(f"✗ {var} NOT loaded")
```

### 3. Add Error Recovery

```python
# In provider clients (e.g., google_ai_client.py)

def get_api_key_with_fallback() -> str:
    """Get API key with fallback to fresh environment read."""
    from .config import get_settings
    
    # Try settings first
    settings = get_settings()
    key = settings.gemini_api_key
    
    # Fallback: Re-read from environment directly
    if not key:
        key = os.getenv("GEMINI_API_KEY")
        if key:
            logging.warning("API key not in settings but found in env - possible cold start issue")
    
    if not key:
        raise ValueError("GEMINI_API_KEY not found in settings or environment")
    
    return key
```

---

## 🔬 Debugging Commands

If the issue persists, add these to your deployment:

```bash
# Check if env vars are set in the container
printenv | grep -E "OPENAI|ANTHROPIC|GEMINI|DEEPSEEK|GROQ"

# Check Python can see them
python3 -c "import os; print('OPENAI:', bool(os.getenv('OPENAI_API_KEY')))"

# Check timing issue
python3 -c "import time; import os; time.sleep(1); print('After delay:', bool(os.getenv('OPENAI_API_KEY')))"
```

---

## 📊 Expected Results

After implementing Solution 1 or 2:

✅ **Zero** "API key not found" errors  
✅ **Consistent** environment variable loading  
✅ **Reliable** cold start behavior  
✅ **Better** error messages when keys are actually missing  

---

## 🎯 Summary

**Problem**: Class-level `os.getenv()` in Settings creates race condition on cold starts  
**Root Cause**: Environment variables not fully loaded at module import time  
**Solution**: Use lazy loading (Pydantic BaseSettings or @cached_property)  
**Impact**: Eliminates intermittent API key errors permanently  

**Recommended**: Implement Solution 1 (Pydantic BaseSettings) for production-grade reliability.
