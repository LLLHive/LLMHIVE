from .language_model import LanguageModel

class Summarizer:
    def __init__(self, llm: LanguageModel):
        self.llm = llm

    def run(self, text_to_summarize: str, instruction: str) -> str:
        """
        Uses a language model to summarize or transform text based on an instruction.
        """
        system_prompt = "You are an expert summarizer and text analyst. Follow the user's instructions precisely."
        prompt = f"""Instruction: {instruction}

Text to process:
---
{text_to_summarize}
---
"""
        return self.llm.generate(prompt, system_prompt=system_prompt)
