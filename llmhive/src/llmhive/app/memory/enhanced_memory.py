"""Enhanced memory management with summarization and relevance filtering."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional, Sequence

from sqlalchemy.orm import Session

from ..models import Conversation, MemoryEntry
from ..knowledge import KnowledgeBase
from ..services.base import LLMProvider, LLMResult

logger = logging.getLogger(__name__)


@dataclass
class SummarizedContext:
    """Context with summarization applied."""
    
    summary: str
    recent_messages: List[str]
    relevant_past_messages: List[str]
    total_messages: int
    summarized_count: int


class EnhancedMemoryManager:
    """Enhanced memory manager with summarization and relevance filtering."""
    
    def __init__(
        self,
        session: Session,
        providers: dict[str, LLMProvider],
        *,
        summarization_threshold: int = 20,
        max_recent_messages: int = 10,
        enable_relevance_filtering: bool = True,
    ):
        """
        Initialize enhanced memory manager.
        
        Args:
            session: Database session
            providers: LLM providers for summarization
            summarization_threshold: Number of messages before summarization triggers
            max_recent_messages: Maximum recent messages to keep
            enable_relevance_filtering: Enable relevance-based filtering
        """
        self.session = session
        self.providers = providers
        self.summarization_threshold = summarization_threshold
        self.max_recent_messages = max_recent_messages
        self.enable_relevance_filtering = enable_relevance_filtering
    
    def fetch_context_with_summarization(
        self,
        conversation: Conversation,
        *,
        current_query: str,
        knowledge_base: Optional[KnowledgeBase] = None,
        providers: Optional[dict[str, LLMProvider]] = None,
    ) -> SummarizedContext:
        """
        Fetch context with automatic summarization and relevance filtering.
        
        Args:
            conversation: Conversation object
            current_query: Current user query
            knowledge_base: Optional knowledge base for relevance filtering
            providers: Optional LLM providers for summarization
            
        Returns:
            SummarizedContext with relevant messages
        """
        # Fetch all messages
        from sqlalchemy import select
        stmt = (
            select(MemoryEntry)
            .where(MemoryEntry.conversation_id == conversation.id)
            .order_by(MemoryEntry.created_at.asc())
        )
        all_entries = list(self.session.scalars(stmt))
        total_messages = len(all_entries)
        
        # Check if summarization is needed
        if total_messages > self.summarization_threshold:
            logger.info(
                "Enhanced Memory: %d messages exceed threshold (%d), triggering summarization",
                total_messages,
                self.summarization_threshold,
            )
            
            # Summarize old messages
            old_entries = all_entries[:-self.max_recent_messages]
            recent_entries = all_entries[-self.max_recent_messages:]
            
            # Generate summary of old messages
            summary = self._summarize_messages(old_entries, providers or self.providers)
            
            # Update conversation summary
            if summary:
                conversation.summary = summary
                self.session.add(conversation)
                logger.info("Enhanced Memory: Updated conversation summary (%d chars)", len(summary))
        else:
            # Use existing summary or generate simple one
            summary = conversation.summary or self._simple_summary(all_entries)
            recent_entries = all_entries[-self.max_recent_messages:]
        
        # Convert to message strings
        recent_messages = [entry.render_for_prompt() for entry in recent_entries]
        
        # Relevance filtering: Find relevant past messages
        relevant_past_messages: List[str] = []
        if self.enable_relevance_filtering and knowledge_base and current_query:
            relevant_past_messages = self._filter_relevant_messages(
                all_entries,
                current_query,
                knowledge_base,
            )
        
        return SummarizedContext(
            summary=summary or "No prior conversation.",
            recent_messages=recent_messages,
            relevant_past_messages=relevant_past_messages,
            total_messages=total_messages,
            summarized_count=max(0, total_messages - self.max_recent_messages),
        )
    
    def _summarize_messages(
        self,
        messages: Sequence[MemoryEntry],
        providers: dict[str, LLMProvider],
    ) -> Optional[str]:
        """Summarize a sequence of messages using LLM."""
        if not messages:
            return None
        
        # Build conversation text
        conversation_text = "\n".join([
            f"{entry.role}: {entry.content}"
            for entry in messages
        ])
        
        # Truncate if too long
        if len(conversation_text) > 8000:
            conversation_text = conversation_text[:8000] + "..."
        
        # Generate summary using LLM
        summary_prompt = f"""Please provide a concise summary of the following conversation, preserving key facts, decisions, and context that would be important for future interactions.

Conversation:
{conversation_text}

Summary:"""
        
        try:
            # Use first available provider
            provider = next(iter(providers.values()))
            model = "gpt-4o-mini"  # Use lightweight model for summarization
            
            # Try async first
            try:
                if hasattr(provider, 'complete'):
                    # Check if it's a coroutine function
                    import inspect
                    if inspect.iscoroutinefunction(provider.complete):
                        # Run async function
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # If loop is already running, create a task
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(asyncio.run, provider.complete(summary_prompt, model=model))
                                result = future.result(timeout=30)
                        else:
                            result = asyncio.run(provider.complete(summary_prompt, model=model))
                    else:
                        result = provider.complete(summary_prompt, model=model)
                else:
                    result = None
            except Exception as exc:
                logger.warning("Enhanced Memory: Error calling provider.complete: %s", exc)
                result = None
            
            if isinstance(result, LLMResult):
                summary = result.content.strip()
            elif isinstance(result, str):
                summary = result.strip()
            else:
                summary = None
            
            if summary:
                logger.info("Enhanced Memory: Generated summary (%d chars)", len(summary))
                return summary
        except Exception as exc:
            logger.warning("Enhanced Memory: Failed to generate summary: %s", exc)
        
        # Fallback to simple summary
        return self._simple_summary(messages)
    
    def _simple_summary(self, messages: Sequence[MemoryEntry]) -> str:
        """Generate a simple summary without LLM."""
        if not messages:
            return "No prior conversation."
        
        # Extract key points from first few and last few messages
        key_messages = list(messages[:3]) + list(messages[-3:])
        snippets = [entry.content[:100] for entry in key_messages if entry.content]
        return " | ".join(snippets[:5])
    
    def _filter_relevant_messages(
        self,
        all_entries: Sequence[MemoryEntry],
        current_query: str,
        knowledge_base: KnowledgeBase,
    ) -> List[str]:
        """Filter messages to only include those relevant to current query."""
        if not all_entries or not current_query:
            return []
        
        # Use knowledge base to find relevant past messages
        # Convert messages to searchable format
        message_texts = [
            entry.content for entry in all_entries
            if entry.role == "assistant"  # Focus on assistant responses
        ]
        
        if not message_texts:
            return []
        
        # Search for relevant messages using knowledge base
        # (This is a simplified approach - could be enhanced)
        relevant_messages: List[str] = []
        
        try:
            # Use knowledge base search to find relevant content
            # We'll search for the query and see which messages match
            hits = knowledge_base.search(
                user_id="",  # Search across all users for now
                query=current_query,
                limit=5,
                min_score=0.4,
            )
            
            # Match hits to messages
            for hit in hits:
                for entry in all_entries:
                    if entry.content and hit.content[:100] in entry.content[:200]:
                        relevant_messages.append(entry.render_for_prompt())
                        break
            
            # Also do simple keyword matching
            query_words = set(current_query.lower().split())
            for entry in all_entries[-20:]:  # Check last 20 messages
                if entry.content:
                    entry_words = set(entry.content.lower().split())
                    overlap = len(query_words.intersection(entry_words))
                    if overlap >= 2:  # At least 2 words overlap
                        msg_str = entry.render_for_prompt()
                        if msg_str not in relevant_messages:
                            relevant_messages.append(msg_str)
        except Exception as exc:
            logger.warning("Enhanced Memory: Relevance filtering failed: %s", exc)
        
        # Limit to top 5 most relevant
        return relevant_messages[:5]
    
    def load_shared_memory(
        self,
        user_id: str,
        *,
        knowledge_base: Optional[KnowledgeBase] = None,
        query: Optional[str] = None,
    ) -> str:
        """
        Load shared memory from user's past interactions.
        
        Args:
            user_id: User ID
            knowledge_base: Knowledge base for retrieval
            query: Optional query to filter relevant memories
            
        Returns:
            Context string with shared memory
        """
        if not knowledge_base:
            return ""
        
        try:
            # Search for relevant past interactions
            search_query = query or "user preferences and important facts"
            hits = knowledge_base.search(
                user_id=user_id,
                query=search_query,
                limit=5,
                min_score=0.5,
            )
            
            if not hits:
                return ""
            
            # Build shared memory context
            memory_items = []
            for hit in hits:
                # Extract key information
                content = hit.content[:300]  # Limit length
                if hit.metadata and hit.metadata.get("verified"):
                    content = f"[Verified] {content}"
                memory_items.append(content)
            
            shared_memory = "\n".join([
                f"[Shared Memory {i+1}] {item}"
                for i, item in enumerate(memory_items)
            ])
            
            logger.info(
                "Enhanced Memory: Loaded %d shared memory items for user %s",
                len(memory_items),
                user_id,
            )
            
            return f"Shared memory from past interactions:\n{shared_memory}"
        except Exception as exc:
            logger.warning("Enhanced Memory: Failed to load shared memory: %s", exc)
            return ""

