"""
LanguageModel: A synchronous wrapper for OpenAI API calls.
"""
from openai import OpenAI
from typing import Optional, Dict, Any

class LanguageModel:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize a synchronous language model client.
        
        Args:
            api_key: OpenAI API key
            model: Model identifier (default: gpt-4o)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a response from the language model.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            response_format: Optional response format configuration (e.g., {"type": "json_object"})
            
        Returns:
            The generated text response
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        kwargs = {"model": self.model, "messages": messages}
        if response_format:
            kwargs["response_format"] = response_format
        
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
