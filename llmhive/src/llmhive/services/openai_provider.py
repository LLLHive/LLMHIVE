from fastapi import HTTPException
import openai

async def complete(self, model: str, messages: list[str]) -> str:
    allowed_models = {"gpt-4o", "gpt-3.5-turbo"}
    if model not in allowed_models:
        raise HTTPException(status_code=400, detail=f"Unsupported model: {model}")
    try:
        result = await self._client.chat.completions.create(
            model=model,
            messages=messages,
            timeout=self.timeout,
        )
        return result
    except openai.OpenAIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected error")
