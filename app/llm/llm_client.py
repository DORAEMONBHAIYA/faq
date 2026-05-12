import time
import asyncio
import httpx
import json
import logging
from app.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger("LLMClient")

# Global Rate Limiter
class RateLimiter:
    def __init__(self, max_rpm=15):
        self.semaphore = asyncio.Semaphore(10) # 10 concurrent requests
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

# Shared global client and limiter
_global_client = httpx.AsyncClient(timeout=120.0)
limiter = RateLimiter(max_rpm=30)

class LLMClient:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.model = GEMINI_MODEL

    async def chat(self, messages, temperature=0.3, retries=3, json_mode=False):
        await limiter.wait_if_needed()
        contents = []
        for m in messages:
            role = "user" if m["role"] in ["user", "system"] else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

        gen_config = {
            "temperature": temperature,
            "topP": 0.95,
            "maxOutputTokens": 8192,
        }
        if json_mode:
            gen_config["responseMimeType"] = "application/json"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        for attempt in range(retries + 1):
            try:
                response = await _global_client.post(url, json={"contents": contents, "generationConfig": gen_config})
                if response.status_code == 429:
                    await asyncio.sleep((attempt + 1) * 5)
                    continue
                response.raise_for_status()
                data = response.json()
                
                if "candidates" not in data or not data["candidates"]:
                    logger.error(f"No candidates in response: {data}")
                    return ""
                    
                candidate = data["candidates"][0]
                if "content" not in candidate:
                    logger.warning(f"Safety Block or empty content: {candidate.get('finishReason')}")
                    return ""
                    
                return candidate["content"]["parts"][0]["text"]
            except Exception as e:
                logger.error(f"API Request failed: {e}")
                if attempt < retries:
                    await asyncio.sleep(2)
                    continue
                raise

    async def chat_json(self, messages, temperature=0.1):
        if "JSON" not in messages[0]["content"]:
            messages[0]["content"] += " Return valid JSON."
        
        # ⚠️ CRITICAL: Gemma models on Gemini API do NOT support responseMimeType: application/json yet.
        # We must use standard chat and clean the output manually.
        use_json_mode = False if "gemma" in self.model.lower() else True
        raw = await self.chat(messages, temperature=temperature, json_mode=use_json_mode)
        
        # Super aggressive JSON extraction using regex
        import re
        match = re.search(r'(\{.*\})', raw, re.DOTALL)
        if match:
            clean = match.group(1)
        else:
            clean = raw.strip()
            
        # Fallback cleaning
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0].strip()
            
        return clean
