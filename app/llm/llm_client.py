import time
import asyncio
import httpx
import json
from app.config import GEMINI_API_KEY, GEMINI_MODEL

# Global Rate Limiter
class RateLimiter:
    def __init__(self, max_rpm=30):
        self.semaphore = asyncio.Semaphore(5)
        self.max_rpm = max_rpm
        self.requests = []

    async def wait_if_needed(self):
        async with self.semaphore:
            now = time.time()
            self.requests = [r for r in self.requests if now - r < 60]
            
            if len(self.requests) >= self.max_rpm:
                wait_time = 60 - (now - self.requests[0]) + 1
                print(f"RPM Safety: Waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
            
            self.requests.append(time.time())

limiter = RateLimiter(max_rpm=30)

class LLMClient:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.model = GEMINI_MODEL

    async def chat(self, messages, temperature=0.3, retries=3):
        await limiter.wait_if_needed()
        contents = []
        for m in messages:
            role = "user" if m["role"] in ["user", "system"] else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=120.0) as client:
            for attempt in range(retries + 1):
                try:
                    response = await client.post(url, json={"contents": contents, "generationConfig": {"temperature": temperature, "maxOutputTokens": 2048}})
                    if response.status_code == 429:
                        await asyncio.sleep((attempt + 1) * 5)
                        continue
                    response.raise_for_status()
                    data = response.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except Exception:
                    if attempt < retries:
                        await asyncio.sleep(2)
                        continue
                    raise

    async def chat_json(self, messages, temperature=0.1):
        if "JSON" not in messages[0]["content"]:
            messages[0]["content"] += " Return valid JSON."
        raw = await self.chat(messages, temperature=temperature)
        
        # Super aggressive JSON cleaning
        clean = raw.strip()
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0].strip()
        
        # Remove potential preamble/postamble
        start = clean.find("{")
        end = clean.rfind("}")
        if start != -1 and end != -1:
            clean = clean[start:end+1]
            
        return clean
