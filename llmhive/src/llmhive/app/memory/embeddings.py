"""Embedding service for generating vector embeddings.

This module provides embedding generation for text using OpenAI or
fallback methods for vector database storage and retrieval.
"""
from __future__ import annotations

import hashlib
import logging
import os
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Try to import OpenAI client
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None  # type: ignore


class EmbeddingService:
    """Service for generating text embeddings."""
    
    def __init__(
        self,
        model: str = "text-embedding-3-small",
        dimension: int = 1536,
        api_key: Optional[str] = None,
    ):
        """
        Initialize embedding service.
        
        Args:
            model: Embedding model to use
            dimension: Embedding dimension
            api_key: OpenAI API key (uses env if not provided)
        """
        self.model = model
        self.dimension = dimension
        self._client: Optional[OpenAI] = None
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if OPENAI_AVAILABLE and self._api_key:
            try:
                self._client = OpenAI(api_key=self._api_key)
                logger.info("Embedding service initialized with OpenAI model: %s", model)
            except Exception as e:
                logger.warning("Failed to initialize OpenAI client: %s", e)
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * self.dimension
        
        # Truncate if too long (OpenAI has token limits)
        text = text[:8000]
        
        # Try OpenAI embedding
        if self._client:
            try:
                response = self._client.embeddings.create(
                    input=text,
                    model=self.model,
                )
                embedding = response.data[0].embedding
                logger.debug("Generated embedding with OpenAI (dim=%d)", len(embedding))
                return embedding
            except Exception as e:
                logger.warning("OpenAI embedding failed, using fallback: %s", e)
        
        # Fallback: Generate deterministic pseudo-embedding from hash
        return self._fallback_embedding(text)
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Filter empty texts
        processed_texts = [t[:8000] if t else "" for t in texts]
        
        # Try OpenAI batch embedding
        if self._client:
            try:
                response = self._client.embeddings.create(
                    input=processed_texts,
                    model=self.model,
                )
                embeddings = [d.embedding for d in response.data]
                logger.debug("Generated %d embeddings with OpenAI", len(embeddings))
                return embeddings
            except Exception as e:
                logger.warning("OpenAI batch embedding failed, using fallback: %s", e)
        
        # Fallback: Generate individually
        return [self._fallback_embedding(t) for t in processed_texts]
    
    def _fallback_embedding(self, text: str) -> List[float]:
        """
        Generate a deterministic pseudo-embedding from text hash.
        
        This is a fallback when OpenAI is not available. It creates
        a reproducible vector from the text hash for testing purposes.
        
        Args:
            text: Text to embed
            
        Returns:
            Pseudo-embedding vector
        """
        # Create deterministic hash-based embedding
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # Convert hash to floats
        embedding = []
        for i in range(0, min(len(text_hash), self.dimension * 2), 2):
            hex_pair = text_hash[i:i+2]
            if i + 2 <= len(text_hash):
                value = int(hex_pair, 16) / 255.0  # Normalize to 0-1
                embedding.append(value - 0.5)  # Center around 0
        
        # Pad or truncate to target dimension
        while len(embedding) < self.dimension:
            # Repeat pattern with variation
            idx = len(embedding) % len(text_hash)
            value = int(text_hash[idx:idx+2], 16) / 255.0 if idx + 2 <= len(text_hash) else 0.5
            embedding.append(value - 0.5)
        
        # Normalize to unit vector
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = [e / norm for e in embedding[:self.dimension]]
        
        return embedding
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = np.sqrt(sum(a * a for a in vec1))
        norm2 = np.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


# Global embedding service instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        from ..config import settings
        _embedding_service = EmbeddingService(
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
        )
    return _embedding_service


def get_embedding(text: str) -> List[float]:
    """Convenience function to get embedding for text."""
    return get_embedding_service().get_embedding(text)

