# Security Features Implementation

This document summarizes the security and privacy features implemented in LLMHive.

## Overview

LLMHive now includes comprehensive security features for production deployments:
1. **Field-level encryption** for data at rest
2. **Sensitive data filtering** for outbound requests
3. **API authentication** for access control

## 1. Field-Level Encryption

### Implementation

- **Algorithm**: AES-256-GCM (Galois/Counter Mode) for authenticated encryption
- **Scope**: Encrypts `content` fields in:
  - `MemoryEntry` model (conversation history)
  - `KnowledgeDocument` model (knowledge base entries)
- **Transparency**: Encryption/decryption is transparent via SQLAlchemy property accessors
- **Backwards Compatibility**: System gracefully handles unencrypted data from before encryption was enabled

### Configuration

```bash
# Enable encryption (required for production)
export ENCRYPTION_KEY="your-secure-encryption-key-here"

# If not set, system logs warning and stores plaintext (dev only)
```

### Key Management

- Encryption key can be:
  - A password string (derived via PBKDF2 with 100,000 iterations)
  - A base64-encoded 32-byte key (for Fernet compatibility)
- Key is loaded from `ENCRYPTION_KEY` environment variable
- If key is missing, system logs warning and continues without encryption (for development)

### Key Rotation

To rotate encryption keys:
1. Decrypt existing data with old key (automatic on read)
2. Set new `ENCRYPTION_KEY` environment variable
3. Re-encrypt data with new key (automatic on next write)

### Database Schema

- Added `content_encrypted` boolean flag to both `memory_entries` and `knowledge_documents` tables
- Migration: `005_add_knowledge_encryption.py`

## 2. Sensitive Data Filtering

### Implementation

- **Detection**: Regex-based pattern matching for:
  - Credit card numbers (16-digit patterns)
  - Social Security Numbers (SSN) - 9 digits
  - Email addresses
  - API keys (common patterns: `sk-`, `pk_`, `ghp_`, `xoxb-`, etc.)
  - Phone numbers
  - IP addresses
  - Password indicators

### Configuration

```bash
# Redact sensitive data (default)
export STRICT_PRIVACY_MODE=false

# Block requests with sensitive data
export STRICT_PRIVACY_MODE=true
```

### Behavior

- **Non-strict mode** (default): Sensitive data is replaced with `[REDACTED]` placeholder
- **Strict mode**: Requests containing sensitive data are blocked with HTTP 400 error
- Only applies to external/untrusted LLM providers (local models bypass filtering)

### Integration Points

- API endpoint (`/api/v1/orchestration/`) filters prompts before processing
- Orchestrator filters prompts before sending to external providers
- All filtering is logged for audit purposes

## 3. API Authentication

### Implementation

- **Method**: API key authentication via HTTP headers
- **Headers Supported**:
  - `X-API-Key: <key>`
  - `Authorization: Bearer <key>`
- **FastAPI Integration**: Uses FastAPI `Security` dependency system

### Configuration

```bash
# Set API key
export API_KEY="your-secure-api-key-here"

# Require authentication (blocks unauthenticated requests)
export REQUIRE_AUTH=true

# Optional authentication (allows anonymous but validates if key provided)
export REQUIRE_AUTH=false  # default
```

### Behavior

- If `REQUIRE_AUTH=true` and `API_KEY` is set:
  - All requests must include valid API key
  - Invalid or missing keys return HTTP 401 Unauthorized
- If `REQUIRE_AUTH=false`:
  - Authentication is optional
  - If key is provided, it must be valid
  - If no key provided, request proceeds as anonymous

### Endpoints Protected

- `POST /api/v1/orchestration/` - Main orchestration endpoint (requires auth if configured)

## 4. Cloud Run Deployment

### Security Configuration

When deploying to Cloud Run, ensure authentication is enforced:

```bash
gcloud run deploy llmhive-orchestrator \
  --platform=managed \
  --no-allow-unauthenticated \
  --set-env-vars API_KEY=...,ENCRYPTION_KEY=...,REQUIRE_AUTH=true
```

**Important**: Remove `--allow-unauthenticated` flag to enforce authentication at the Cloud Run level.

### Environment Variables

Required for production:
- `ENCRYPTION_KEY` - Encryption key for data at rest
- `API_KEY` - API key for authentication
- `REQUIRE_AUTH=true` - Enforce authentication

Optional:
- `STRICT_PRIVACY_MODE=true` - Block requests with sensitive data

## 5. Testing

Comprehensive test suite in `llmhive/tests/test_security_features.py`:

- **Encryption Tests**:
  - AES-256-GCM encryption/decryption
  - Encryption manager disabled state
  - MemoryEntry and KnowledgeDocument encryption

- **Sensitive Data Filtering Tests**:
  - Credit card detection
  - SSN detection
  - Email detection
  - API key detection
  - Strict mode blocking
  - No false positives

- **Authentication Tests**:
  - Valid API key
  - Invalid API key
  - Missing key (when required)
  - Bearer token format
  - Optional authentication

## 6. Migration Guide

### Enabling Encryption on Existing Data

1. Set `ENCRYPTION_KEY` environment variable
2. Restart application
3. Existing data will be decrypted on read (if unencrypted)
4. Data will be encrypted on next write

### Enabling Authentication

1. Set `API_KEY` environment variable
2. Set `REQUIRE_AUTH=true` (optional, for strict enforcement)
3. Update clients to include API key in headers
4. Restart application

### Database Migration

Run Alembic migration to add encryption support:

```bash
alembic upgrade head
```

This adds `content_encrypted` column to `knowledge_documents` table.

## 7. Security Best Practices

1. **Encryption Key Management**:
   - Use strong, randomly generated keys (32+ characters)
   - Store keys in secure secret management (e.g., Google Secret Manager)
   - Rotate keys periodically
   - Never commit keys to version control

2. **API Key Management**:
   - Use strong, randomly generated API keys
   - Store keys securely
   - Rotate keys if compromised
   - Use different keys for different environments

3. **Sensitive Data Handling**:
   - Enable strict mode in production
   - Monitor logs for sensitive data detection
   - Educate users about data privacy

4. **Deployment**:
   - Always use `--no-allow-unauthenticated` in production
   - Enable encryption for all production deployments
   - Use HTTPS/TLS for all communications
   - Monitor authentication failures

## 8. Troubleshooting

### Encryption Issues

- **Warning: No encryption key provided**: Set `ENCRYPTION_KEY` environment variable
- **Decryption fails**: Data may be unencrypted (backwards compatibility), or key mismatch
- **Performance**: Encryption overhead is minimal (<1ms per field)

### Authentication Issues

- **401 Unauthorized**: Check that `API_KEY` matches and header is correct
- **Anonymous requests**: Set `REQUIRE_AUTH=true` to enforce authentication

### Sensitive Data Filtering

- **False positives**: Adjust regex patterns in `guardrails.py` if needed
- **Requests blocked**: Check `STRICT_PRIVACY_MODE` setting and remove sensitive data from prompts

## 9. Compliance

These security features help meet requirements for:
- **GDPR**: Encryption of personal data at rest
- **HIPAA**: Encryption and access controls
- **SOC 2**: Access controls and data protection
- **PCI DSS**: Sensitive data filtering (credit cards)

## 10. Future Enhancements

Potential future improvements:
- OAuth 2.0 / OpenID Connect integration
- Role-based access control (RBAC)
- Audit logging for all security events
- Key rotation automation
- Advanced PII detection (ML-based)
- Data loss prevention (DLP) integration

