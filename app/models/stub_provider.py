"""
Stub LLM Provider for testing without API keys.
"""

from typing import AsyncGenerator, List, Dict
import asyncio
from .llm_provider import LLMProvider


class StubProvider(LLMProvider):
    """A stub provider that returns mock responses for testing purposes."""
    
    async def generate(self, messages: List[Dict[str, str]], model: str, **kwargs) -> str:
        """Generate a mock response."""
        await asyncio.sleep(0.1)  # Simulate API delay
        
        # Extract the user message
        user_msg = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_msg = msg.get("content", "")
                break
        
        # Generate simple responses for common queries
        user_msg_lower = user_msg.lower()
        
        if "hello" in user_msg_lower or "hi" in user_msg_lower:
            return "Hello! I'm a stub LLM response. To get real AI responses, please configure API keys for OpenAI, Anthropic, or other LLM providers."
        
        if "capital" in user_msg_lower and "france" in user_msg_lower:
            return "The capital of France is Paris."
        
        if "capital" in user_msg_lower and "spain" in user_msg_lower:
            return "The capital of Spain is Madrid."
        
        # Default response
        return f"This is a stub response from {model}. The system is working correctly, but no real LLM API keys are configured. Please add API keys to get actual AI-powered responses.\n\nYour question: {user_msg[:100]}..."
    
    async def generate_stream(self, messages: List[Dict[str, str]], model: str, **kwargs) -> AsyncGenerator[str, None]:
        """Generate a mock streaming response."""
        response = await self.generate(messages, model, **kwargs)
        
        # Stream the response word by word
        words = response.split()
        for i, word in enumerate(words):
            await asyncio.sleep(0.05)  # Simulate streaming delay
            if i < len(words) - 1:
                yield word + " "
            else:
                yield word
