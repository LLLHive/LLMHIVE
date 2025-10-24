# LLMHive Enhancements: LLM-Driven Intelligence & Streaming

This document describes the major enhancements implemented to transform LLMHive into an intelligent, asynchronous multi-agent orchestration platform.

## Overview

The platform has been upgraded with the following key capabilities:

1. **Dynamic, LLM-driven Planning** - Plans are now generated dynamically using GPT-4
2. **Shared State Management** - A Blackboard system enables agent collaboration
3. **Real-time Streaming** - Token-by-token response streaming for better UX
4. **Real API Integration** - Actual OpenAI and Anthropic API calls replace stubs
5. **Advanced Orchestration** - Support for parallel execution and iterative refinement

## New Components

### 1. Blackboard (`app/orchestration/blackboard.py`)

A thread-safe shared scratchpad that allows agents to:
- Store intermediate results
- Share reasoning steps
- Collaborate on complex tasks

**Example Usage:**
```python
blackboard = Blackboard("User's original prompt")
blackboard.set("research_findings", "Data gathered...")
findings = blackboard.get("research_findings")
```

### 2. Enhanced Planner (`app/orchestration/planner.py`)

The planner now uses GPT-4 to dynamically generate structured execution plans in JSON format.

**Plan Structure:**
```json
{
  "reasoning": "Why this plan was chosen",
  "steps": [
    {
      "type": "sequential",
      "steps": [
        {"role": "researcher", "task": "Gather information"},
        {"role": "lead", "task": "Analyze and draft answer"},
        {"role": "critic", "task": "Review for accuracy"},
        {"role": "editor", "task": "Polish final response"}
      ]
    }
  ],
  "synthesis_strategy": "llm_merge"
}
```

The planner supports:
- **Sequential execution**: Steps happen in order
- **Parallel execution**: Multiple tasks run simultaneously
- **Fallback logic**: Simple rule-based plan if LLM parsing fails

### 3. Streaming Support

All agents and the synthesizer now support token-by-token streaming:

**Agent Base Class:**
```python
async def execute_stream(self, prompt: str, context: str = "") -> AsyncGenerator[str, None]:
    """Streams the response token by token"""
    async for token in self.provider.generate_stream(...):
        yield token
```

### 4. Real LLM Provider Integration

Replaced stub implementations with actual API clients:

**OpenAI Provider:**
- Uses `AsyncOpenAI` client
- Supports both full response and streaming
- Includes error handling

**Anthropic Provider:**
- Uses `AsyncAnthropic` client
- Supports both full response and streaming
- Includes error handling

### 5. Advanced Orchestration

The orchestrator now supports:

**Parallel Execution:**
```python
if block['type'] == 'parallel':
    tasks = [self._execute_step(step, blackboard, dream_team) 
             for step in block['steps']]
    await asyncio.gather(*tasks)
```

**Iterative Refinement:**
```python
critic_feedback = blackboard.get("results.critic")
if critic_feedback:
    # Editor incorporates feedback to produce final draft
    final_draft = await editor_agent.execute(refinement_task, ...)
    blackboard.set("results.final_draft", final_draft)
```

### 6. Streaming API Endpoint

The `/api/prompt` endpoint now returns a streaming response:

```python
@router.post("/prompt")
async def process_prompt_stream(request: PromptRequest):
    orchestrator = Orchestrator(user_id=request.user_id)
    response_stream = orchestrator.run(request.prompt)
    return StreamingResponse(response_stream, media_type="text/plain")
```

## Configuration

### Environment Variables

Set these environment variables for API access:

```bash
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### Model Pool

Currently supported models:
- `gpt-4` - OpenAI's most capable model for reasoning and coding
- `gpt-4-turbo` - Faster GPT-4 with larger context window
- `claude-3-opus` - Anthropic's most capable model for writing and analysis
- `claude-3-sonnet` - Faster Claude with excellent performance

## Usage Examples

### Basic Usage

```python
from app.orchestration.orchestrator import Orchestrator

orchestrator = Orchestrator(user_id="user123")

# Stream the response
async for token in orchestrator.run("Explain quantum computing"):
    print(token, end="", flush=True)
```

### API Usage

```bash
curl -X POST http://localhost:8000/api/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "prompt": "Explain quantum computing"
  }' \
  --no-buffer
```

## Architecture Benefits

1. **Flexibility**: Plans adapt dynamically to user prompts
2. **Collaboration**: Agents share state through the blackboard
3. **Performance**: Parallel execution for independent tasks
4. **Quality**: Iterative refinement improves final outputs
5. **UX**: Real-time streaming provides immediate feedback

## Future Enhancements

Potential areas for expansion:
- Add Google Gemini provider
- Implement cost tracking and optimization
- Add plan caching for similar prompts
- Enhanced memory management with vector stores
- Support for tool-augmented agents (web search, code execution)
- Multi-modal support (images, audio)

## Testing

Run the test suite to verify functionality:

```bash
# Run unit tests
pytest app/tests/

# Manual verification with stub providers
python -c "
from app.orchestration.orchestrator import Orchestrator
import asyncio

async def test():
    orchestrator = Orchestrator('test')
    async for token in orchestrator.run('Test prompt'):
        print(token, end='')

asyncio.run(test())
"
```

## Security Considerations

- API keys are loaded from environment variables
- Internal errors are logged but not exposed to users
- Content validation checks remain in place
- PII detection warnings are included in responses

## Dependencies

New dependencies added:
- `openai>=1.12.0` - OpenAI API client
- `anthropic` - Anthropic API client

All dependencies are specified in `requirements.txt`.
