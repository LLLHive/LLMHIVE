# LLMHive User Guide

Welcome to LLMHive - an enterprise-grade AI assistant with multi-model orchestration, multimodal capabilities, and intelligent tool use.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Basic Usage](#basic-usage)
3. [Advanced Features](#advanced-features)
4. [Multimodal Capabilities](#multimodal-capabilities)
5. [Tools](#tools)
6. [Memory](#memory)
7. [Billing & Tiers](#billing--tiers)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Getting Started

### 1. Create an Account

Visit [llmhive.io/signup](https://llmhive.io/signup) to create your account.

### 2. Get Your API Key

Navigate to **Settings > API Keys** and generate a new API key.

### 3. Install the SDK

**Python:**
```bash
pip install llmhive
```

**JavaScript:**
```bash
npm install @llmhive/sdk
```

### 4. Make Your First Request

```python
from llmhive import LLMHive

client = LLMHive(api_key="your-api-key")

response = client.chat("What is the capital of France?")
print(response)  # Paris is the capital of France.
```

---

## Basic Usage

### Simple Chat

```python
# Simple question
response = client.chat("Explain quantum computing in simple terms")

# With conversation history
messages = [
    {"role": "user", "content": "Hi, I'm learning Python"},
    {"role": "assistant", "content": "Great! Python is a wonderful language to learn."},
    {"role": "user", "content": "What should I learn first?"}
]
response = client.chat(messages=messages)
```

### Adjusting Response Quality

LLMHive offers **accuracy levels** from 1-5:

| Level | Description | Use Case |
|-------|-------------|----------|
| 1 | Fast, single model | Quick answers, low latency |
| 2 | Balanced | General use |
| 3 | Standard (default) | Most questions |
| 4 | High accuracy | Important decisions |
| 5 | Maximum accuracy | Critical, complex queries |

```python
# Quick answer
response = client.chat("What's 2+2?", accuracy_level=1)

# Critical decision
response = client.chat(
    "Compare investment strategies for retirement",
    accuracy_level=5
)
```

---

## Advanced Features

### Hierarchical Role Management (HRM)

For complex queries, LLMHive can break down tasks into sub-tasks handled by specialist models:

```python
response = client.chat(
    "Compare the economic, environmental, and social impacts of electric vehicles",
    use_hrm=True  # Enable hierarchical planning
)
```

**How it works:**
1. Executive agent analyzes the query
2. Tasks are delegated to specialists (economic analyst, environmental expert, etc.)
3. Results are synthesized into a coherent answer

### Multi-Model Consensus

Get answers validated by multiple models for increased confidence:

```python
response = client.chat(
    "What are the key causes of climate change?",
    use_consensus=True,
    accuracy_level=4
)

print(f"Consensus score: {response.metadata.consensus_score}")
```

### Autonomous Tool Use

Let LLMHive automatically use tools to solve complex problems:

```python
response = client.chat(
    "Calculate the compound interest on $10,000 at 5% annual rate for 10 years, "
    "then search for current savings account rates and compare",
    tools=["calculator", "web_search"]
)
```

---

## Multimodal Capabilities

### Image Analysis

Upload images for analysis:

```python
# Analyze an image
with open("photo.jpg", "rb") as f:
    image_data = f.read()

response = client.chat(
    "What's in this image?",
    images=[image_data]
)

# Or use a URL
response = client.chat(
    "Describe this image",
    image_urls=["https://example.com/image.jpg"]
)
```

**Capabilities:**
- Object detection
- Scene description
- Text extraction (OCR)
- Landmark identification
- Technical diagram analysis

### Image Generation

Generate images from descriptions (Pro tier and above):

```python
response = client.generate_image(
    "A serene mountain landscape at sunset with a lake in the foreground",
    style="photorealistic",
    size="1024x1024"
)

image_url = response.images[0].url
```

### Audio Processing

**Speech to Text:**
```python
with open("audio.mp3", "rb") as f:
    audio_data = f.read()

response = client.transcribe(audio_data)
print(response.text)
```

**Text to Speech:**
```python
audio = client.synthesize_speech(
    "Hello! Welcome to LLMHive.",
    voice="nova"
)
audio.save("output.mp3")
```

---

## Tools

LLMHive has built-in tools for various tasks:

### Available Tools

| Tool | Description | Tier |
|------|-------------|------|
| `calculator` | Mathematical calculations | Free |
| `datetime` | Date/time operations | Free |
| `web_search` | Search the web | Pro |
| `knowledge_lookup` | Query knowledge base | Free |
| `code_execution` | Run Python code | Enterprise |
| `image_generation` | Generate images | Pro |
| `translate` | Language translation | Pro |

### Using Tools

```python
# Automatic tool selection
response = client.chat(
    "What's the square root of 144 plus today's date?",
    tools=["calculator", "datetime"]
)

# The system automatically decides which tools to use
```

### Custom Tools (Enterprise)

Register custom tools for your organization:

```python
client.register_tool(
    name="inventory_lookup",
    description="Look up product inventory",
    endpoint="https://your-api.com/inventory",
    parameters={
        "product_id": {"type": "string", "required": True}
    }
)
```

---

## Memory

LLMHive remembers context across conversations:

### Automatic Memory

User preferences and important facts are automatically remembered:

```python
# First conversation
client.chat("I prefer responses in bullet points")

# Later conversation - preferences are applied
client.chat("Explain machine learning")
# Response will use bullet points
```

### Manual Memory

```python
# Store a memory
client.memory.store(
    content="My favorite programming language is Python",
    category="preference"
)

# Retrieve memories
memories = client.memory.list(category="preference")

# Delete a memory
client.memory.delete(memory_id="mem_123")
```

### Memory Categories

- **preference**: User preferences (response style, topics of interest)
- **fact**: Important facts about the user
- **context**: Conversation context
- **knowledge**: Domain-specific knowledge

---

## Billing & Tiers

### Tier Comparison

| Feature | Free | Pro ($29/mo) | Enterprise |
|---------|------|--------------|------------|
| Requests/month | 100 | 10,000 | Unlimited |
| Tokens/month | 50K | 1M | Unlimited |
| Models | Basic | All | All + Custom |
| HRM | ❌ | ✅ | ✅ |
| Consensus | ❌ | ✅ | ✅ |
| Image Analysis | ❌ | ✅ | ✅ |
| Image Generation | ❌ | ✅ | ✅ |
| Audio | ❌ | ✅ | ✅ |
| Priority Support | ❌ | ✅ | ✅ |
| SLA | ❌ | 99.9% | 99.99% |
| SSO | ❌ | ❌ | ✅ |

### Check Usage

```python
usage = client.get_usage()
print(f"Requests: {usage.requests_used}/{usage.requests_limit}")
print(f"Tokens: {usage.tokens_used}/{usage.tokens_limit}")
```

### Upgrade

```python
client.upgrade_to("pro")
# Or visit the dashboard: llmhive.io/billing
```

---

## Best Practices

### 1. Optimize for Latency

```python
# For quick responses
response = client.chat(
    "Quick question...",
    accuracy_level=1,  # Fast
    max_tokens=100     # Limit response
)
```

### 2. Use Appropriate Accuracy

```python
# Simple factual questions
response = client.chat("What year was Python released?", accuracy_level=2)

# Complex analysis
response = client.chat("Analyze market trends...", accuracy_level=4)
```

### 3. Provide Context

```python
# Include relevant context
response = client.chat(
    messages=[
        {"role": "system", "content": "You are helping a software developer."},
        {"role": "user", "content": "How do I optimize this?"}
    ]
)
```

### 4. Handle Errors Gracefully

```python
from llmhive.exceptions import RateLimitError, ContentPolicyError

try:
    response = client.chat("...")
except RateLimitError:
    # Wait and retry
    time.sleep(60)
    response = client.chat("...")
except ContentPolicyError:
    # Content was blocked
    print("Request blocked by content policy")
```

### 5. Use Streaming for Long Responses

```python
# Stream response for better UX
for chunk in client.chat_stream("Write a story about..."):
    print(chunk, end="", flush=True)
```

---

## Troubleshooting

### Common Issues

#### "Rate limit exceeded"

You've hit your tier's rate limit. Wait and retry, or upgrade your plan.

```python
from llmhive.exceptions import RateLimitError
import time

try:
    response = client.chat("...")
except RateLimitError as e:
    wait_time = e.retry_after
    time.sleep(wait_time)
    response = client.chat("...")
```

#### "Tier limit exceeded"

You've used your monthly allocation. Upgrade or wait for reset.

#### "Model unavailable"

A specific model is temporarily down. LLMHive will automatically fall back to alternatives.

#### "Content policy violation"

Your request was blocked by safety filters. Rephrase your question.

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("llmhive").setLevel(logging.DEBUG)

client = LLMHive(api_key="...", debug=True)
```

### Support

- **Documentation**: [docs.llmhive.io](https://docs.llmhive.io)
- **Community**: [community.llmhive.io](https://community.llmhive.io)
- **Email**: support@llmhive.io
- **Enterprise**: enterprise@llmhive.io

---

## Next Steps

1. Explore the [API Reference](./API_REFERENCE.md)
2. Read the [Plugin Development Guide](./PLUGIN_GUIDE.md)
3. Check out [Example Projects](./EXAMPLES.md)
4. Join our [Community Forum](https://community.llmhive.io)

Happy building with LLMHive! 🐝

