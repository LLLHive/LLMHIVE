# Clarification Loop Implementation

This document describes the implementation of the user clarification loop feature in LLMHive.

## Overview

The clarification loop detects ambiguous or underspecified queries and engages users with follow-up questions to clarify their intent before generating a final answer. This improves answer quality by ensuring the system understands exactly what the user is asking.

## Implementation Details

### 1. Ambiguity Detection Module (`llmhive/src/llmhive/app/clarification.py`)

**New Module Created** with the following components:

#### `AmbiguityDetector`
- Analyzes queries for ambiguity using multiple heuristics:
  - **Query Length**: Queries shorter than 10 characters are flagged
  - **Generic Patterns**: Detects number-only queries (e.g., "42"), very short words, or just question words
  - **Ambiguous References**: Detects pronouns and references without context ("it", "this", "that", etc.)
  - **Broad Questions**: Identifies questions without specific subjects ("what is", "tell me about")
  - **Special Cases**: Handles known ambiguous queries (e.g., "42" has multiple cultural meanings)

- Returns `AmbiguityAnalysis` with:
  - `is_ambiguous`: Boolean flag
  - `ambiguity_score`: 0.0-1.0 (higher = more ambiguous)
  - `reasons`: List of ambiguity reasons
  - `possible_interpretations`: List of possible meanings
  - `suggested_clarification`: Generated clarification question

#### `ClarificationGenerator`
- Generates clarification questions using templates (default) or LLM (optional)
- Incorporates user's clarification response into the original query
- Methods:
  - `generate_clarification()`: Main method to generate clarification requests
  - `_generate_template()`: Template-based clarification generation
  - `_generate_with_llm()`: LLM-based clarification generation (optional)
  - `incorporate_clarification()`: Merges clarification into original query

### 2. Orchestrator Integration

**File**: `llmhive/src/llmhive/app/orchestrator.py`

#### New Parameters
- `clarification_response`: User's response to clarification question
- `is_clarification_response`: Flag indicating this is a clarification response
- `original_query`: Original ambiguous query (for context)
- `interactive_mode`: Whether to request clarifications (True for UI, False for API-only)

#### Clarification Flow
1. **Check for Clarification Response**: If `is_clarification_response` is True, incorporate the clarification into the prompt
2. **Detect Ambiguity**: In interactive mode, check if query is ambiguous
3. **Request Clarification**: If ambiguous, return special `OrchestrationArtifacts` with model="clarification"
4. **Non-Interactive Mode**: In API-only mode, log ambiguity but proceed with default interpretation

### 3. API Integration

**File**: `llmhive/src/llmhive/app/api/orchestration.py`

- Extracts clarification parameters from request payload
- Passes parameters to orchestrator
- Detects clarification requests in response (checks if `final_response.model == "clarification"`)
- Extracts clarification question and possible interpretations from `supporting_notes`
- Returns clarification fields in `OrchestrationResponse`

### 4. Schema Updates

**File**: `llmhive/src/llmhive/app/schemas.py`

#### `OrchestrationRequest` - New Fields:
- `clarification_response`: User's response to clarification
- `is_clarification_response`: Flag for clarification responses
- `original_query`: Original ambiguous query

#### `OrchestrationResponse` - New Fields:
- `requires_clarification`: Boolean flag
- `clarification_question`: The clarifying question
- `possible_interpretations`: List of possible query meanings

### 5. Frontend Integration

**Files**: 
- `ui/components/chat-area.tsx`
- `ui/app/api/chat/route.ts`
- `ui/lib/types.ts`

#### Chat Area
- Added `pendingClarification` state to track clarification context
- Detects clarification requests in responses
- Displays clarification questions as assistant messages
- Stores original query and interpretations in message metadata
- Handles clarification responses by sending them with original query context

#### API Route
- Extracts clarification parameters from frontend
- Forwards them to backend API

#### Message Type
- Added `metadata` field to `Message` interface for clarification context

## User Flow

### Interactive Mode (UI)

1. **User sends ambiguous query** (e.g., "42")
2. **System detects ambiguity** and generates clarification question
3. **UI displays clarification question** as an assistant message
4. **User responds** with clarification (e.g., "The number from Hitchhiker's Guide")
5. **System incorporates clarification** into original query
6. **System generates final answer** with clarified context

### Non-Interactive Mode (API)

1. **API receives ambiguous query**
2. **System detects ambiguity** but doesn't request clarification
3. **System proceeds with default interpretation** and logs ambiguity
4. **System generates answer** based on best guess

## Ambiguity Detection Examples

### High Ambiguity (Score ≥ 0.4)
- **"42"**: Multiple cultural meanings (mathematics, pop culture, sports)
- **"it"**: Pronoun without context
- **"what is"**: Broad question without subject
- **Very short queries**: Less than 10 characters

### Medium Ambiguity
- **"tell me about"**: Broad question with minimal context
- **Queries with ambiguous references**: "this", "that", "recent", "latest"

### Low Ambiguity
- **Specific questions**: "What is the capital of France?"
- **Clear queries**: "Explain quantum computing in simple terms"
- **Queries with context**: "Based on our previous discussion, explain..."

## Clarification Question Examples

### Number-Only Query
```
I see you asked about '42'. Could you clarify what you mean? 
For example: The number 42 in mathematics (answer to life, universe, everything), 
The number 42 as a pop culture reference (Hitchhiker's Guide), 
or something else?
```

### Short Query
```
Your query seems incomplete. Could you provide more details about 
what you're looking for? For example, what specific aspect of 
'[query]' would you like to know about?
```

### Ambiguous Reference
```
Your query contains some references that could mean different things. 
Could you provide more context or be more specific about what you're asking?
```

## Testing

### Manual Testing Steps

1. **Ambiguous Query Test**:
   - Send query: "42"
   - Verify clarification question appears
   - Verify no final answer is given yet
   - Respond with clarification
   - Verify final answer is generated

2. **Clear Query Test**:
   - Send query: "What is the capital of France?"
   - Verify no clarification is requested
   - Verify answer is generated directly

3. **Clarification Response Test**:
   - Send ambiguous query
   - Respond to clarification
   - Verify original query context is preserved
   - Verify answer addresses clarified intent

4. **API Non-Interactive Test**:
   - Send ambiguous query via API (without UI)
   - Verify system proceeds without waiting
   - Verify answer is generated (may be based on default interpretation)
   - Check logs for ambiguity detection

### Unit Tests (To Be Implemented)

```python
def test_ambiguity_detection():
    detector = AmbiguityDetector()
    
    # Test number-only query
    analysis = detector.analyze("42")
    assert analysis.is_ambiguous == True
    assert analysis.ambiguity_score >= 0.4
    
    # Test clear query
    analysis = detector.analyze("What is the capital of France?")
    assert analysis.is_ambiguous == False
    
    # Test short query
    analysis = detector.analyze("it")
    assert analysis.is_ambiguous == True

def test_clarification_generation():
    generator = ClarificationGenerator()
    
    # Test clarification request
    req = generator.generate_clarification("42")
    assert req is not None
    assert req.clarification_question is not None
    assert len(req.possible_interpretations) > 0
    
    # Test clear query (no clarification needed)
    req = generator.generate_clarification("What is Python?")
    assert req is None

def test_clarification_incorporation():
    generator = ClarificationGenerator()
    
    enhanced = generator.incorporate_clarification(
        "42",
        "The number from Hitchhiker's Guide to the Galaxy"
    )
    assert "42" in enhanced
    assert "Hitchhiker" in enhanced
```

## Files Modified

### Backend
- `llmhive/src/llmhive/app/clarification.py`: **NEW FILE** - Ambiguity detection and clarification generation
- `llmhive/src/llmhive/app/orchestrator.py`: Added clarification handling
- `llmhive/src/llmhive/app/schemas.py`: Added clarification fields
- `llmhive/src/llmhive/app/api/orchestration.py`: Added clarification handling

### Frontend
- `ui/components/chat-area.tsx`: Added clarification UI handling
- `ui/app/api/chat/route.ts`: Added clarification parameter forwarding
- `ui/lib/types.ts`: Added metadata field to Message interface

## Configuration

### Environment Variables
- `ENABLE_CLARIFICATION_LOOP`: Enable/disable clarification loop (default: True)
- `CLARIFICATION_USE_LLM`: Use LLM for clarification generation (default: False, uses templates)
- `CLARIFICATION_AMBIGUITY_THRESHOLD`: Minimum ambiguity score to trigger clarification (default: 0.4)

### Settings
Can be configured in `llmhive/src/llmhive/app/config.py`:
```python
enable_clarification_loop: bool = True
clarification_use_llm: bool = False
clarification_ambiguity_threshold: float = 0.4
clarification_min_query_length: int = 10
```

## Future Enhancements

1. **LLM-Based Clarification**: Use LLM to generate more natural clarification questions
2. **Multi-Round Clarification**: Support multiple clarification rounds for complex queries
3. **Context-Aware Detection**: Use conversation history to reduce false positives
4. **Domain-Specific Detection**: Custom ambiguity rules for different domains (medical, legal, etc.)
5. **Learning from Feedback**: Improve ambiguity detection based on user responses
6. **Confidence-Based Thresholds**: Adjust ambiguity threshold based on query complexity

## Notes

- Clarification loop only activates in interactive mode (UI requests)
- Non-interactive mode (API-only) proceeds with default interpretation
- Ambiguity detection uses heuristics; can be enhanced with ML models
- Clarification questions are generated using templates by default (fast, no LLM cost)
- LLM-based clarification generation is optional and can be enabled for better quality
- Original query context is preserved throughout the clarification process

