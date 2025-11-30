# Knowledge & Memory Optimization Implementation

This document describes the implementation of enhanced knowledge base integration and memory management optimizations in LLMHive.

## Overview

The knowledge and memory optimization enhances LLMHive's ability to:
- Retrieve relevant information using multi-hop retrieval and re-ranking
- Maintain conversational context efficiently through summarization
- Filter memory to include only relevant past messages
- Share knowledge across sessions for persistent user-specific information
- Attribute sources for retrieved information

## Implementation Details

### 1. Enhanced Knowledge Base (`llmhive/src/llmhive/app/knowledge/enhanced_retrieval.py`)

**New Module Created** with the following components:

#### `EnhancedKnowledgeBase` Class
- **Purpose**: Enhanced knowledge base with multi-hop retrieval, re-ranking, and source attribution
- **Features**:
  - Multi-hop retrieval for complex queries
  - Re-ranking of retrieved passages
  - Source attribution for citations
  - Caching of retrieval results

#### Key Components:

##### `MultiHopRetrieval` Class
- **Purpose**: Perform multi-hop retrieval for complex queries
- **Workflow**:
  1. Initial retrieval (Hop 1) with the original query
  2. Extract key information from initial results
  3. Build follow-up queries based on initial results
  4. Perform targeted retrieval (Hops 2+) with follow-up queries
  5. Combine results from all hops, avoiding duplicates

##### `Reranker` Class
- **Purpose**: Re-rank retrieved passages based on relevance
- **Scoring Factors**:
  - Base vector similarity score (from vector DB)
  - Keyword overlap boost
  - Length penalty (prefers medium-length passages)
  - Verified fact boost
- **Returns**: Top K re-ranked results

##### `SourceAttribution` Dataclass
- **Purpose**: Store source metadata for retrieved knowledge
- **Fields**:
  - `title`: Document title
  - `url`: Source URL
  - `document_id`: Document identifier
  - `domain`: Domain/category
  - `verified`: Whether fact is verified
  - `timestamp`: When fact was recorded
  - `metadata`: Additional metadata

##### `EnhancedKnowledgeHit` Dataclass
- **Purpose**: Enhanced knowledge hit with source attribution
- **Extends**: `KnowledgeHit` with:
  - `source`: SourceAttribution object
  - `rerank_score`: Re-ranking score
  - `hop`: Which retrieval hop this came from

#### Methods:
- `search_enhanced()`: Enhanced search with multi-hop and re-ranking
- `get_sources()`: Extract source attributions from hits
- `_single_hop_search()`: Single-hop search with source attribution

### 2. Enhanced Memory Manager (`llmhive/src/llmhive/app/memory/enhanced_memory.py`)

**New Module Created** with the following components:

#### `EnhancedMemoryManager` Class
- **Purpose**: Enhanced memory manager with summarization and relevance filtering
- **Features**:
  - Automatic conversation summarization
  - Relevance-based message filtering
  - Shared memory loading across sessions

#### Key Components:

##### `SummarizedContext` Dataclass
- **Purpose**: Context with summarization applied
- **Fields**:
  - `summary`: Conversation summary
  - `recent_messages`: Recent messages (last N)
  - `relevant_past_messages`: Relevant past messages (filtered)
  - `total_messages`: Total message count
  - `summarized_count`: Number of messages summarized

#### Methods:
- `fetch_context_with_summarization()`: Fetch context with automatic summarization
- `load_shared_memory()`: Load shared memory from past interactions
- `_summarize_messages()`: Summarize messages using LLM
- `_simple_summary()`: Generate simple summary without LLM
- `_filter_relevant_messages()`: Filter messages by relevance to current query

### 3. Integration Points

#### API Integration (`llmhive/src/llmhive/app/api/orchestration.py`)

**Enhanced Knowledge Base Integration**:
- Uses `EnhancedKnowledgeBase` when `enable_enhanced_knowledge` is True
- Calls `search_enhanced()` for multi-hop retrieval and re-ranking
- Extracts source attributions for citations
- Logs retrieval statistics

**Enhanced Memory Manager Integration**:
- Uses `EnhancedMemoryManager` when `enable_enhanced_memory` is True
- Calls `fetch_context_with_summarization()` for context with summarization
- Calls `load_shared_memory()` to load user-specific knowledge
- Combines summarized context, recent messages, and relevant past messages

### 4. Configuration Settings

**File**: `llmhive/src/llmhive/app/config.py`

#### New Settings:
- `enable_enhanced_knowledge`: Enable enhanced knowledge base (default: True)
- `enable_enhanced_memory`: Enable enhanced memory manager (default: True)
- `knowledge_enable_multihop`: Enable multi-hop retrieval (default: True)
- `knowledge_enable_reranking`: Enable re-ranking (default: True)
- `memory_summarization_threshold`: Messages before summarization (default: 20)
- `memory_max_recent_messages`: Max recent messages to keep (default: 10)
- `memory_enable_relevance_filtering`: Enable relevance filtering (default: True)

## Features

### 1. Multi-Hop Retrieval

**Purpose**: Handle complex queries requiring reasoning over multiple pieces of information

**Workflow**:
1. **Hop 1**: Initial retrieval with original query
2. **Hop 2+**: Extract key information from initial results
3. Build follow-up queries based on extracted information
4. Perform targeted retrieval with follow-up queries
5. Combine results, avoiding duplicates

**Example**:
- Query: "What are the symptoms of diabetes and how is it treated?"
- Hop 1: Retrieve general diabetes information
- Hop 2: Retrieve specific treatment information based on Hop 1 results

### 2. Re-Ranking

**Purpose**: Prioritize most relevant passages from retrieved results

**Scoring Factors**:
- Base vector similarity (40% weight)
- Keyword overlap boost (up to 30% boost)
- Length penalty (prefers 50-2000 chars)
- Verified fact boost (10% boost)

**Benefits**:
- Improves relevance of retrieved passages
- Reduces noise from less relevant results
- Prioritizes verified facts

### 3. Source Attribution

**Purpose**: Track sources for retrieved information

**Metadata Stored**:
- Document title
- Source URL
- Document ID
- Domain/category
- Verification status
- Timestamp

**Use Cases**:
- Citations in responses
- Fact verification
- Source tracking for audit

### 4. Conversation Summarization

**Purpose**: Prevent context from growing too large in long conversations

**Workflow**:
1. Monitor message count
2. When threshold exceeded (default: 20 messages):
   - Keep recent N messages (default: 10)
   - Summarize older messages using LLM
   - Update conversation summary
3. Use summary + recent messages for context

**Benefits**:
- Reduces token usage
- Maintains important context
- Scales to long conversations

### 5. Relevance Filtering

**Purpose**: Include only relevant past messages in context

**Workflow**:
1. Generate embedding of current query
2. Search knowledge base for relevant content
3. Match retrieved content to past messages
4. Include only matching messages in context

**Benefits**:
- Reduces irrelevant context
- Improves focus on relevant information
- Reduces token usage

### 6. Shared Memory Across Sessions

**Purpose**: Retain user-specific knowledge across sessions

**Workflow**:
1. At conversation start, search user's past interactions
2. Retrieve relevant verified facts and preferences
3. Load into context for new conversation
4. Automatically available for all queries

**Benefits**:
- Persistent user knowledge
- Better personalization
- Context continuity across sessions

## Performance Considerations

### Caching
- **Retrieval Cache**: In-memory cache for retrieval results (cleared after 100 entries)
- **Cache Key**: `{user_id}:{query}`
- **Benefits**: Reduces redundant vector DB queries

### Vector DB Optimization
- **Filtering**: User-specific filtering to reduce search space
- **Top-K Limiting**: Limit initial retrieval to reasonable size
- **Score Thresholds**: Filter low-relevance results early

### Summarization Optimization
- **Threshold-Based**: Only summarize when needed (20+ messages)
- **LLM Fallback**: Falls back to simple summary if LLM fails
- **Async Handling**: Proper async handling for LLM calls

## Testing

### Manual Testing Steps

1. **Multi-Hop Retrieval Test**:
   - Send complex query requiring multiple pieces of info
   - Verify: Multiple retrieval hops occur
   - Check logs for hop information

2. **Re-Ranking Test**:
   - Send query that returns many results
   - Verify: Results are re-ranked by relevance
   - Check logs for re-ranking scores

3. **Summarization Test**:
   - Create conversation with 25+ messages
   - Verify: Summarization triggers at threshold
   - Verify: Summary is generated and stored
   - Verify: Recent messages are preserved

4. **Relevance Filtering Test**:
   - Create conversation with many messages
   - Send query on specific topic
   - Verify: Only relevant past messages included
   - Verify: Irrelevant messages excluded

5. **Shared Memory Test**:
   - Create verified fact in one session
   - Start new conversation
   - Verify: Shared memory loaded
   - Verify: Verified fact available in context

### Unit Tests (To Be Implemented)

```python
def test_multihop_retrieval():
    kb = EnhancedKnowledgeBase(session)
    hits = kb.search_enhanced("complex query", user_id="test", use_multihop=True)
    assert any(h.hop > 1 for h in hits)

def test_reranking():
    kb = EnhancedKnowledgeBase(session)
    hits = kb.search_enhanced("query", user_id="test", use_reranking=True)
    assert all(h.rerank_score is not None for h in hits)
    # Verify scores are in descending order
    scores = [h.rerank_score for h in hits]
    assert scores == sorted(scores, reverse=True)

def test_summarization():
    manager = EnhancedMemoryManager(session, providers)
    # Create conversation with 25 messages
    context = manager.fetch_context_with_summarization(conversation, current_query="test")
    assert context.summarized_count > 0
    assert len(context.recent_messages) <= 10

def test_relevance_filtering():
    manager = EnhancedMemoryManager(session, providers)
    context = manager.fetch_context_with_summarization(
        conversation,
        current_query="specific topic",
        knowledge_base=kb,
    )
    assert len(context.relevant_past_messages) > 0
    # Verify messages are relevant to query
```

## Files Created/Modified

### New Files
- `llmhive/src/llmhive/app/knowledge/__init__.py` - Knowledge module init
- `llmhive/src/llmhive/app/knowledge/enhanced_retrieval.py` - Enhanced retrieval implementation
- `llmhive/src/llmhive/app/memory/enhanced_memory.py` - Enhanced memory implementation

### Modified Files
- `llmhive/src/llmhive/app/api/orchestration.py` - Integration of enhanced knowledge and memory
- `llmhive/src/llmhive/app/config.py` - Configuration settings

## Configuration

### Environment Variables
- `ENABLE_ENHANCED_KNOWLEDGE`: Enable enhanced knowledge (default: True)
- `ENABLE_ENHANCED_MEMORY`: Enable enhanced memory (default: True)
- `KNOWLEDGE_ENABLE_MULTIHOP`: Enable multi-hop (default: True)
- `KNOWLEDGE_ENABLE_RERANKING`: Enable re-ranking (default: True)
- `MEMORY_SUMMARIZATION_THRESHOLD`: Summarization threshold (default: 20)
- `MEMORY_MAX_RECENT_MESSAGES`: Max recent messages (default: 10)
- `MEMORY_ENABLE_RELEVANCE_FILTERING`: Enable relevance filtering (default: True)

## Future Enhancements

1. **ML-Based Re-Ranker**: Replace heuristic re-ranking with ML model
2. **Adaptive Summarization**: Adjust summarization threshold based on conversation complexity
3. **Semantic Message Matching**: Use embeddings for better relevance filtering
4. **Persistent Cache**: Store retrieval cache in database or Redis
5. **Source Citation UI**: Display sources in frontend
6. **Multi-Domain Knowledge**: Better handling of cross-domain queries
7. **Knowledge Graph**: Build knowledge graph from retrieved facts
8. **Query Expansion**: Expand queries for better retrieval

## Notes

- Enhanced features are optional and can be disabled via configuration
- Falls back to standard knowledge/memory if enhanced features fail
- Vector DB is optional (works without it, but with reduced functionality)
- Summarization uses lightweight model (gpt-4o-mini) to reduce cost
- Caching is simple in-memory (can be enhanced with Redis)
- Source attribution metadata is stored but not yet displayed in UI
- Multi-hop retrieval is limited to 2 hops by default (configurable)

