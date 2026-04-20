import time
import asyncio
import httpx
from app.config import GEMINI_API_KEY, GEMINI_MODEL

class LLMClient:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.model = GEMINI_MODEL

        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not set in .env")
        print(f"LLMClient initialized using Gemini model: {self.model}")

    async def chat(self, messages, temperature=0.3, retries=3):
        """Asynchronous Gemini Native API implementation."""
        contents = []
        for m in messages:
            role = "user" if m["role"] in ["user", "system"] else "model"
            contents.append({
                "role": role,
                "parts": [{"text": m["content"]}]
            })

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 1024,
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            for attempt in range(retries + 1):
                try:
                    response = await client.post(url, json=payload)
                    
                    if response.status_code == 429:
                        wait = (attempt + 1) * 3
                        print(f"Rate limit hit. Waiting {wait}s...")
                        await asyncio.sleep(wait)
                        continue
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    if "candidates" in data and data["candidates"]:
                        return data["candidates"][0]["content"]["parts"][0]["text"]
                    
                    if "error" in data:
                        raise RuntimeError(f"Gemini Error: {data['error']['message']}")
                    
                    raise RuntimeError("Gemini error: Empty candidates")
                except Exception as e:
                    if attempt < retries:
                        await asyncio.sleep(2)
                        continue
                    raise

    async def chat_json(self, messages, temperature=0.1):
        if "JSON" not in messages[0]["content"]:
            messages[0]["content"] += " Return valid JSON."
        raw = await self.chat(messages, temperature=temperature)
        clean = raw.strip()
        if clean.startswith("```json"): clean = clean[7:]
        if clean.endswith("```"): clean = clean[:-3]
        return clean.strip()
