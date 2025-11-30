# Answer Formatting Implementation

This document describes the implementation of answer formatting with format styles and confidence indicators.

## Overview

The answer formatting system allows users to choose how answers are presented (bullet points or paragraphs) and automatically includes confidence indicators based on verification and quality metrics.

## Implementation Details

### 1. Refiner Module (`llmhive/src/llmhive/app/refiner.py`)

**New Module Created** with the following functions:

#### `format_answer(answer_text, format_style, confidence_score, confidence_level)`
- Formats answer text according to user preferences
- Supports two format styles:
  - **"bullet"**: Converts text to bullet points
    - Splits text into sentences or key points
    - Prefixes each with "- "
    - Handles long sentences by splitting into concise bullets
    - Preserves existing bullet formatting
  - **"paragraph"**: Formats as well-structured paragraph
    - Cleans up extra whitespace
    - Ensures proper spacing around punctuation
    - Removes excessive newlines

#### `compute_confidence_level(...)`
- Computes confidence score (0.0-1.0) and level ("High", "Medium", "Low")
- Factors considered:
  1. **Fact check verification**: Uses `verification_score` or `is_valid` from fact check result
  2. **Quality assessments**: Averages quality scores from all models
  3. **Consensus score**: Uses DeepConf consensus score if available
  4. **Loop-back penalty**: Reduces confidence by 0.2 if loop-back refinement was needed
  5. **Verification bonus**: Adds 0.9 score if verification passed

#### Confidence Indicator Format
- Shows both level and score: `**Confidence: High** (8/10)`
- Or just level if score unavailable: `**Confidence: Medium**`

### 2. Orchestrator Integration

**File**: `llmhive/src/llmhive/app/orchestrator.py`

- Added `format_style` parameter to `orchestrate()` method
- Formats final answer before returning:
  - Extracts consensus score from consensus notes (if DeepConf was used)
  - Computes confidence using `compute_confidence_level()`
  - Formats answer using `format_answer()`
  - Updates `final_response` with formatted content

**Location**: Formatting happens right before returning `OrchestrationArtifacts`, after all processing is complete.

### 3. API Schema Updates

**File**: `llmhive/src/llmhive/app/schemas.py`

Added to `OrchestrationRequest`:
```python
format_style: Optional[str] = Field(
    default="paragraph",
    description="Answer formatting style: 'bullet' for bullet points or 'paragraph' for paragraph format (default: 'paragraph').",
)
```

### 4. API Route Updates

**File**: `llmhive/src/llmhive/app/api/orchestration.py`

- Extracts `format_style` from payload
- Validates format_style (must be "bullet" or "paragraph")
- Passes `format_style` to orchestrator

### 5. Frontend Integration

**Files**: 
- `ui/components/chat-area.tsx`
- `ui/components/chat-header.tsx`
- `ui/app/api/chat/route.ts`

#### Chat Area
- Added `formatStyle` state (default: "paragraph")
- Sends `formatStyle` in API request

#### Chat Header
- Added "Answer Style" dropdown with options:
  - Paragraph (default)
  - Bullet Points
- Dropdown shows current selection: "Style: Paragraph" or "Style: Bullets"

#### API Route
- Extracts `formatStyle` from request
- Forwards as `format_style` to backend

## Format Styles

### Bullet Format
- Converts sentences to bullet points
- Handles existing bullets and numbered lists
- Splits long sentences intelligently
- Example:
  ```
  - First key point about the topic.
  - Second important aspect to consider.
  - Final conclusion or summary.
  ```

### Paragraph Format
- Well-structured paragraph
- Proper spacing and punctuation
- Clean formatting
- Example:
  ```
  This is a well-structured paragraph that provides a comprehensive answer. 
  It maintains proper spacing and punctuation throughout.
  ```

## Confidence Indicator

The confidence indicator is automatically appended to formatted answers:

```
---
**Confidence: High** (8/10)
```

Or:

```
---
**Confidence: Medium**
```

### Confidence Levels

- **High** (≥0.8): All verification passed, high quality, strong consensus
- **Medium** (0.6-0.8): Some verification passed, moderate quality
- **Low** (<0.6): Verification issues, low quality, or conflicts

### Confidence Computation

The confidence score is computed as an average of:
1. Fact check verification score (if available)
2. Average quality assessment scores
3. Consensus score from DeepConf (if available)
4. Verification passed bonus (0.9 if passed)
5. Loop-back penalty (reduces all scores by 0.2 if loop-back occurred)

## Testing

### Manual Testing Steps

1. **Bullet Format**:
   - Select "Bullet Points" from Answer Style dropdown
   - Submit a query
   - Verify answer is formatted as bullet points
   - Check that confidence indicator is appended

2. **Paragraph Format**:
   - Select "Paragraph" from Answer Style dropdown
   - Submit a query
   - Verify answer is formatted as a paragraph
   - Check that confidence indicator is appended

3. **Confidence Indicator**:
   - Submit queries with different verification outcomes
   - Verify confidence level reflects:
     - High: When verification passes and quality is high
     - Medium: When some verification passes
     - Low: When verification fails or quality is low

4. **Format Preservation**:
   - Submit a query with existing bullet points
   - Verify existing formatting is preserved
   - Verify new content is formatted according to style

## Files Modified

### Backend
- `llmhive/src/llmhive/app/refiner.py`: **NEW FILE** - Answer formatting module
- `llmhive/src/llmhive/app/orchestrator.py`: Added formatting integration
- `llmhive/src/llmhive/app/schemas.py`: Added `format_style` parameter
- `llmhive/src/llmhive/app/api/orchestration.py`: Added format_style handling

### Frontend
- `ui/components/chat-area.tsx`: Added formatStyle state
- `ui/components/chat-header.tsx`: Added Answer Style dropdown
- `ui/app/api/chat/route.ts`: Added formatStyle forwarding

## Future Enhancements

1. **Additional Format Styles**:
   - JSON format for structured data
   - Markdown format with headers
   - Table format for tabular data

2. **Tone Adjustment**:
   - Formal vs. casual tone
   - Technical vs. simple language
   - Professional vs. friendly

3. **Custom Formatting**:
   - User-defined format templates
   - Custom confidence thresholds
   - Format-specific confidence indicators

4. **LLM-Assisted Formatting**:
   - Use LLM to improve formatting quality
   - Better sentence splitting for bullets
   - Intelligent summarization for concise bullets

## Notes

- Formatting only affects presentation, not content
- Confidence indicator is always appended when confidence can be computed
- Default format is "paragraph" if not specified
- Format style is validated on backend (invalid styles default to "paragraph")
- Confidence computation is heuristic-based and may be refined based on feedback

