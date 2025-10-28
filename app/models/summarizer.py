from .language_model import LanguageModel

class Summarizer:
    def __init__(self, llm: LanguageModel):
        self.llm = llm

    def run(self, text_or_prompt: str, instruction: str | None = None) -> str:
        """Generate a summary or direct response using the configured LLM."""

        system_prompt = (
            "You are an expert summarizer and helpful assistant. Follow the user's "
            "instructions precisely."
        )

        if instruction is None:
            prompt = text_or_prompt
        else:
            prompt = (
                f"Instruction: {instruction}\n\n"
                "Text to process:\n---\n"
                f"{text_or_prompt}\n---"
            )

        return self.llm.generate(prompt, system_prompt=system_prompt)
