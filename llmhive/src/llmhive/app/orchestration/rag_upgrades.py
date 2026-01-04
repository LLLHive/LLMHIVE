"""RAG Upgrades for LLMHive Stage 4.

This module implements Section 4 of Stage 4 upgrades:
- Chunked document retrieval with ranking
- Improved answer merging with preserved order
- Multi-hop reasoning with tracing
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ==============================================================================
# DOCUMENT CHUNKING
# ==============================================================================

@dataclass
class DocumentChunk:
    """A chunk of a document with metadata."""
    chunk_id: str
    document_id: str
    content: str
    start_offset: int
    end_offset: int
    chunk_index: int
    total_chunks: int
    embedding: Optional[List[float]] = None
    score: float = 0.0
    
    def __hash__(self):
        return hash(self.chunk_id)


class DocumentChunker:
    """Chunks documents for better retrieval.
    
    Implements Stage 4 Section 4: Chunked document retrieval.
    """
    
    def __init__(
        self,
        chunk_size: int = 300,  # words
        overlap: int = 50,  # words overlap between chunks
        min_chunk_size: int = 50,  # minimum words for a chunk
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size
    
    def chunk_document(
        self,
        document_id: str,
        content: str,
    ) -> List[DocumentChunk]:
        """
        Split a document into overlapping chunks.
        
        Args:
            document_id: Unique document identifier
            content: Document text content
            
        Returns:
            List of DocumentChunk objects
        """
        words = content.split()
        chunks = []
        
        if len(words) <= self.chunk_size:
            # Document is small enough to be one chunk
            chunk = DocumentChunk(
                chunk_id=self._generate_chunk_id(document_id, 0),
                document_id=document_id,
                content=content,
                start_offset=0,
                end_offset=len(content),
                chunk_index=0,
                total_chunks=1,
            )
            return [chunk]
        
        # Create overlapping chunks
        step = self.chunk_size - self.overlap
        total_chunks = (len(words) + step - 1) // step
        
        for i, start in enumerate(range(0, len(words), step)):
            end = min(start + self.chunk_size, len(words))
            chunk_words = words[start:end]
            
            if len(chunk_words) < self.min_chunk_size and chunks:
                # Append to previous chunk if too small
                chunks[-1].content += " " + " ".join(chunk_words)
                continue
            
            chunk_content = " ".join(chunk_words)
            start_offset = len(" ".join(words[:start])) if start > 0 else 0
            end_offset = start_offset + len(chunk_content)
            
            chunk = DocumentChunk(
                chunk_id=self._generate_chunk_id(document_id, i),
                document_id=document_id,
                content=chunk_content,
                start_offset=start_offset,
                end_offset=end_offset,
                chunk_index=i,
                total_chunks=total_chunks,
            )
            chunks.append(chunk)
        
        # Update total_chunks to actual count
        for chunk in chunks:
            chunk.total_chunks = len(chunks)
        
        logger.debug(
            "Chunked document %s into %d chunks (avg %d words)",
            document_id, len(chunks), sum(len(c.content.split()) for c in chunks) // len(chunks)
        )
        
        return chunks
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate a unique chunk ID."""
        combined = f"{document_id}::{chunk_index}"
        return hashlib.md5(combined.encode()).hexdigest()[:16]


# ==============================================================================
# CHUNK RANKING
# ==============================================================================

class ChunkRanker:
    """Ranks document chunks by relevance to query.
    
    Uses both keyword overlap and embedding similarity.
    """
    
    def __init__(self, embedding_weight: float = 0.7):
        self.embedding_weight = embedding_weight
        self.keyword_weight = 1.0 - embedding_weight
    
    def rank_chunks(
        self,
        query: str,
        chunks: List[DocumentChunk],
        query_embedding: Optional[List[float]] = None,
        top_k: int = 5,
    ) -> List[DocumentChunk]:
        """
        Rank chunks by relevance to query.
        
        Args:
            query: Search query
            chunks: List of chunks to rank
            query_embedding: Optional query embedding
            top_k: Number of top chunks to return
            
        Returns:
            Top-k chunks sorted by relevance
        """
        query_words = set(query.lower().split())
        
        for chunk in chunks:
            chunk_words = set(chunk.content.lower().split())
            
            # Keyword overlap score
            overlap = len(query_words & chunk_words)
            keyword_score = overlap / max(len(query_words), 1)
            
            # Embedding similarity (if available)
            embedding_score = 0.0
            if query_embedding and chunk.embedding:
                embedding_score = self._cosine_similarity(query_embedding, chunk.embedding)
            
            # Combined score
            chunk.score = (
                self.keyword_weight * keyword_score +
                self.embedding_weight * embedding_score
            )
        
        # Sort by score and return top-k
        ranked = sorted(chunks, key=lambda c: c.score, reverse=True)
        return ranked[:top_k]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = sum(a * a for a in vec1) ** 0.5
        mag2 = sum(b * b for b in vec2) ** 0.5
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot_product / (mag1 * mag2)


# ==============================================================================
# ANSWER MERGING WITH ORDER PRESERVATION
# ==============================================================================

@dataclass
class SubAnswer:
    """An answer to a sub-question."""
    question_index: int
    question: str
    answer: str
    sources: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class MergedAnswer:
    """A merged answer from multiple sub-answers."""
    full_answer: str
    sub_answers: List[SubAnswer]
    total_sources: List[str]
    order_preserved: bool = True


class OrderedAnswerMerger:
    """Merges answers while preserving query order.
    
    Implements Stage 4 Section 4: Improved answer merging.
    """
    
    def __init__(self, number_answers: bool = True):
        self.number_answers = number_answers
    
    def merge(self, sub_answers: List[SubAnswer]) -> MergedAnswer:
        """
        Merge sub-answers in original query order.
        
        Args:
            sub_answers: List of SubAnswer objects
            
        Returns:
            MergedAnswer with combined content
        """
        if not sub_answers:
            return MergedAnswer(
                full_answer="",
                sub_answers=[],
                total_sources=[],
            )
        
        # Sort by original question index
        sorted_answers = sorted(sub_answers, key=lambda a: a.question_index)
        
        # Collect all sources
        all_sources = []
        seen_sources = set()
        for ans in sorted_answers:
            for src in ans.sources:
                if src not in seen_sources:
                    all_sources.append(src)
                    seen_sources.add(src)
        
        # Build merged answer
        parts = []
        for i, ans in enumerate(sorted_answers, 1):
            if self.number_answers and len(sorted_answers) > 1:
                # Add numbering for multiple answers
                part = f"({i}) {ans.answer}"
            else:
                part = ans.answer
            
            # Add source citations inline
            if ans.sources:
                citations = ", ".join(f"【{src}†】" for src in ans.sources[:3])
                part += f" {citations}"
            
            parts.append(part)
        
        # Join with appropriate separators
        if len(parts) == 1:
            full_answer = parts[0]
        elif len(parts) == 2:
            full_answer = f"{parts[0]}\n\n{parts[1]}"
        else:
            full_answer = "\n\n".join(parts)
        
        return MergedAnswer(
            full_answer=full_answer,
            sub_answers=sorted_answers,
            total_sources=all_sources,
            order_preserved=True,
        )
    
    def detect_compound_query(self, query: str) -> List[str]:
        """
        Detect and split compound queries.
        
        Args:
            query: User query that may have multiple parts
            
        Returns:
            List of individual sub-queries
        """
        # Common patterns for compound questions
        patterns = [
            r'(?<=\?)\s+(?=[A-Z])',  # Questions separated by ?
            r'\s+and\s+(?:also\s+)?(?=what|how|when|where|who|why)',  # "and also what/how..."
            r'\.\s+(?=[A-Z][a-z]*\s+)',  # Sentences separated by period
            r';\s+',  # Semicolon separation
        ]
        
        parts = [query]
        for pattern in patterns:
            new_parts = []
            for part in parts:
                splits = re.split(pattern, part, flags=re.IGNORECASE)
                new_parts.extend(s.strip() for s in splits if s.strip())
            parts = new_parts
        
        # Clean up and validate
        valid_parts = []
        for part in parts:
            clean = part.strip(' .?')
            if len(clean) > 10:  # Minimum length for a valid question
                valid_parts.append(clean + ('?' if clean[-1] not in '.?!' else ''))
        
        return valid_parts if len(valid_parts) > 1 else [query]


# ==============================================================================
# MULTI-HOP REASONING
# ==============================================================================

@dataclass
class HopResult:
    """Result from one hop in multi-hop reasoning."""
    hop_number: int
    query: str
    result: str
    sources: List[str]
    derived_from: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MultiHopTrace:
    """Complete trace of multi-hop reasoning."""
    original_query: str
    hops: List[HopResult]
    final_answer: str
    total_hops: int
    success: bool
    reasoning_log: List[str] = field(default_factory=list)


class MultiHopReasoner:
    """Multi-hop reasoning with complete tracing.
    
    Implements Stage 4 Section 4: Multi-hop reasoning tracing.
    """
    
    def __init__(
        self,
        max_hops: int = 3,
        retriever: Optional[Any] = None,
        llm_provider: Optional[Any] = None,
    ):
        self.max_hops = max_hops
        self.retriever = retriever
        self.llm_provider = llm_provider
    
    async def reason(
        self,
        query: str,
        context: Optional[str] = None,
    ) -> MultiHopTrace:
        """
        Perform multi-hop reasoning with tracing.
        
        Args:
            query: Original user query
            context: Optional initial context
            
        Returns:
            MultiHopTrace with complete reasoning chain
        """
        hops = []
        reasoning_log = []
        current_context = context or ""
        current_query = query
        
        reasoning_log.append(f"Starting multi-hop reasoning for: {query}")
        
        for hop_num in range(1, self.max_hops + 1):
            reasoning_log.append(f"Hop {hop_num}: Query = {current_query[:100]}...")
            
            # Retrieve relevant information
            retrieval_result = await self._retrieve(current_query, current_context)
            
            hop_result = HopResult(
                hop_number=hop_num,
                query=current_query,
                result=retrieval_result.get('answer', ''),
                sources=retrieval_result.get('sources', []),
                derived_from=current_context[:100] if hop_num > 1 else None,
            )
            hops.append(hop_result)
            
            reasoning_log.append(
                f"Hop {hop_num} result: {hop_result.result[:100]}... "
                f"[{len(hop_result.sources)} sources]"
            )
            
            # Check if we have a complete answer
            if self._is_answer_complete(query, hop_result.result):
                reasoning_log.append("Answer complete, stopping reasoning")
                break
            
            # Generate follow-up query if needed
            next_query = await self._generate_followup(
                original_query=query,
                current_result=hop_result.result,
            )
            
            if not next_query or next_query == current_query:
                reasoning_log.append("No follow-up needed, stopping reasoning")
                break
            
            current_query = next_query
            current_context = hop_result.result
            reasoning_log.append(f"Follow-up query generated: {next_query[:100]}...")
        
        # Compile final answer
        final_answer = self._compile_final_answer(query, hops)
        
        return MultiHopTrace(
            original_query=query,
            hops=hops,
            final_answer=final_answer,
            total_hops=len(hops),
            success=bool(hops),
            reasoning_log=reasoning_log,
        )
    
    async def _retrieve(
        self,
        query: str,
        context: str,
    ) -> Dict[str, Any]:
        """Retrieve information for a query."""
        if self.retriever:
            try:
                result = await self.retriever.search(query, context=context)
                return {
                    'answer': getattr(result, 'answer', str(result)),
                    'sources': getattr(result, 'sources', []),
                }
            except Exception as e:
                logger.warning("Retrieval failed: %s", e)
        
        return {'answer': '', 'sources': []}
    
    async def _generate_followup(
        self,
        original_query: str,
        current_result: str,
    ) -> Optional[str]:
        """Generate a follow-up query based on current result."""
        if not self.llm_provider:
            return None
        
        prompt = f"""Original question: {original_query}

Current information: {current_result[:500]}

Is there more information needed to fully answer the original question?
If yes, provide a specific follow-up query. If no, respond with "COMPLETE".

Follow-up query:"""
        
        try:
            result = await self.llm_provider.complete(prompt, model="gpt-4o-mini")
            response = getattr(result, 'content', '') or str(result)
            
            if "COMPLETE" in response.upper():
                return None
            
            return response.strip()
            
        except Exception as e:
            logger.warning("Follow-up generation failed: %s", e)
            return None
    
    def _is_answer_complete(self, query: str, answer: str) -> bool:
        """Check if the answer fully addresses the query."""
        if not answer or len(answer) < 20:
            return False
        
        # Simple heuristics for completeness
        # Could be enhanced with LLM verification
        query_keywords = set(query.lower().split())
        answer_keywords = set(answer.lower().split())
        
        overlap = len(query_keywords & answer_keywords) / max(len(query_keywords), 1)
        return overlap > 0.3 and len(answer) > 100
    
    def _compile_final_answer(
        self,
        original_query: str,
        hops: List[HopResult],
    ) -> str:
        """Compile the final answer from all hops."""
        if not hops:
            return "Unable to find an answer."
        
        if len(hops) == 1:
            answer = hops[0].result
            if hops[0].sources:
                citations = ", ".join(f"【{s}†】" for s in hops[0].sources[:3])
                answer += f" {citations}"
            return answer
        
        # Multiple hops - compile with step references
        parts = []
        for hop in hops:
            step_text = f"Step {hop.hop_number}: {hop.result}"
            if hop.sources:
                citations = ", ".join(f"【{s}†】" for s in hop.sources[:2])
                step_text += f" {citations}"
            parts.append(step_text)
        
        return "\n".join(parts)


# ==============================================================================
# RETRIEVAL MANAGER
# ==============================================================================

class RAGManager:
    """Unified RAG manager with all Stage 4 enhancements.
    
    Combines chunking, ranking, answer merging, and multi-hop reasoning.
    """
    
    def __init__(
        self,
        chunker: Optional[DocumentChunker] = None,
        ranker: Optional[ChunkRanker] = None,
        merger: Optional[OrderedAnswerMerger] = None,
        multi_hop_reasoner: Optional[MultiHopReasoner] = None,
    ):
        self.chunker = chunker or DocumentChunker()
        self.ranker = ranker or ChunkRanker()
        self.merger = merger or OrderedAnswerMerger()
        self.multi_hop = multi_hop_reasoner or MultiHopReasoner()
        self._document_chunks: Dict[str, List[DocumentChunk]] = {}
    
    def index_document(self, document_id: str, content: str) -> int:
        """
        Index a document by chunking it.
        
        Args:
            document_id: Document identifier
            content: Document content
            
        Returns:
            Number of chunks created
        """
        chunks = self.chunker.chunk_document(document_id, content)
        self._document_chunks[document_id] = chunks
        
        logger.info("Indexed document %s: %d chunks", document_id, len(chunks))
        return len(chunks)
    
    def search_chunks(
        self,
        query: str,
        top_k: int = 5,
        document_ids: Optional[List[str]] = None,
    ) -> List[DocumentChunk]:
        """
        Search indexed chunks.
        
        Args:
            query: Search query
            top_k: Number of results
            document_ids: Optional filter to specific documents
            
        Returns:
            List of matching chunks
        """
        # Collect all chunks to search
        all_chunks = []
        if document_ids:
            for doc_id in document_ids:
                if doc_id in self._document_chunks:
                    all_chunks.extend(self._document_chunks[doc_id])
        else:
            for chunks in self._document_chunks.values():
                all_chunks.extend(chunks)
        
        if not all_chunks:
            return []
        
        # Rank and return top-k
        return self.ranker.rank_chunks(query, all_chunks, top_k=top_k)
    
    async def answer_query(
        self,
        query: str,
        use_multi_hop: bool = True,
    ) -> MergedAnswer:
        """
        Answer a query using RAG pipeline.
        
        Args:
            query: User query
            use_multi_hop: Whether to use multi-hop reasoning
            
        Returns:
            MergedAnswer with results
        """
        # Detect compound query
        sub_queries = self.merger.detect_compound_query(query)
        
        sub_answers = []
        for i, sub_query in enumerate(sub_queries):
            # Search for relevant chunks
            chunks = self.search_chunks(sub_query, top_k=3)
            
            if chunks:
                # Use chunk content as answer (in real system, would use LLM)
                answer_text = " ".join(c.content[:200] for c in chunks)
                sources = [c.document_id for c in chunks]
            else:
                answer_text = "No relevant information found."
                sources = []
            
            sub_answer = SubAnswer(
                question_index=i,
                question=sub_query,
                answer=answer_text,
                sources=sources,
                confidence=max((c.score for c in chunks), default=0.0),
            )
            sub_answers.append(sub_answer)
        
        return self.merger.merge(sub_answers)


# ==============================================================================
# FACTORY FUNCTIONS
# ==============================================================================

def create_document_chunker(
    chunk_size: int = 300,
    overlap: int = 50,
) -> DocumentChunker:
    """Create a document chunker."""
    return DocumentChunker(chunk_size=chunk_size, overlap=overlap)


def create_chunk_ranker(embedding_weight: float = 0.7) -> ChunkRanker:
    """Create a chunk ranker."""
    return ChunkRanker(embedding_weight=embedding_weight)


def create_answer_merger(number_answers: bool = True) -> OrderedAnswerMerger:
    """Create an ordered answer merger."""
    return OrderedAnswerMerger(number_answers=number_answers)


def create_multi_hop_reasoner(
    max_hops: int = 3,
    retriever: Optional[Any] = None,
    llm_provider: Optional[Any] = None,
) -> MultiHopReasoner:
    """Create a multi-hop reasoner."""
    return MultiHopReasoner(max_hops=max_hops, retriever=retriever, llm_provider=llm_provider)


def create_rag_manager() -> RAGManager:
    """Create a complete RAG manager."""
    return RAGManager()

