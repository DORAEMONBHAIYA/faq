import time
import asyncio
import httpx
import json
import logging
import os
from app.config import (
    GEMINI_API_KEY, GEMINI_MODEL, GEMINI_EMBED_MODEL,
    OX_API_KEY, OX_BASE_URL, OX_MODEL,
    FELO_API_KEY, FELO_BASE_URL, FELO_MODEL,
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL,
    LLM_PROVIDER, PROVIDER_OX, PROVIDER_FELO, PROVIDER_OPENROUTER
)

logger = logging.getLogger("LLMClient")

class RateLimiter:
    def __init__(self, max_rpm=60):
        self.semaphore = asyncio.Semaphore(10)
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

_google_client = httpx.AsyncClient(timeout=120.0)
limiter = RateLimiter(max_rpm=60)

_ox_client = None
_ox_async_client = None
_felo_client = None
_felo_async_client = None
_openrouter_client = None
_openrouter_async_client = None

def _get_ox_clients():
    global _ox_client, _ox_async_client
    if _ox_client is None and OX_API_KEY:
        try:
            from openai import OpenAI, AsyncOpenAI
            _ox_client = OpenAI(base_url=OX_BASE_URL, api_key=OX_API_KEY)
            _ox_async_client = AsyncOpenAI(base_url=OX_BASE_URL, api_key=OX_API_KEY)
        except Exception as e:
            logger.error(f"Failed to init OX client: {e}")
    return _ox_client, _ox_async_client

def _get_felo_clients():
    global _felo_client, _felo_async_client
    if _felo_client is None and FELO_API_KEY:
        try:
            from openai import OpenAI, AsyncOpenAI
            _felo_client = OpenAI(base_url=FELO_BASE_URL, api_key=FELO_API_KEY)
            _felo_async_client = AsyncOpenAI(base_url=FELO_BASE_URL, api_key=FELO_API_KEY)
        except Exception as e:
            logger.error(f"Failed to init Felo client: {e}")
    return _felo_client, _felo_async_client

def _get_openrouter_clients():
    global _openrouter_client, _openrouter_async_client
    if _openrouter_client is None and OPENROUTER_API_KEY:
        try:
            from openai import OpenAI, AsyncOpenAI
            _openrouter_client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY)
            _openrouter_async_client = AsyncOpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY)
        except Exception as e:
            logger.error(f"Failed to init OpenRouter client: {e}")
    return _openrouter_client, _openrouter_async_client

class LLMClient:
    def __init__(self):
        self.provider = LLM_PROVIDER
        self.gemini_api_key = GEMINI_API_KEY
        self.gemini_model = GEMINI_MODEL
        self.ox_api_key = OX_API_KEY
        self.ox_model = OX_MODEL
        self.ox_base_url = OX_BASE_URL
        self.felo_api_key = FELO_API_KEY
        self.felo_model = FELO_MODEL
        self.felo_base_url = FELO_BASE_URL
        self.openrouter_api_key = OPENROUTER_API_KEY
        self.openrouter_model = OPENROUTER_MODEL
        self.openrouter_base_url = OPENROUTER_BASE_URL
        if self.provider == PROVIDER_OPENROUTER and not self.openrouter_api_key:
            logger.warning("OPENROUTER_API_KEY missing but LLM_PROVIDER=openrouter — falling back to gemini")
            self.provider = "gemini"
        elif self.provider == PROVIDER_FELO and not self.felo_api_key:
            logger.warning("FELO_API_KEY missing but LLM_PROVIDER=felo — falling back to gemini")
            self.provider = "gemini"
        elif self.provider == PROVIDER_OX and not self.ox_api_key:
            logger.warning("OX_API_KEY missing but LLM_PROVIDER=ox — falling back to gemini")
            self.provider = "gemini"

    async def chat(self, messages, temperature=0.3, retries=3, json_mode=False):
        await limiter.wait_if_needed()
        if self.provider == PROVIDER_OPENROUTER and self.openrouter_api_key:
            try:
                return await self._chat_openrouter(messages, temperature, retries, json_mode)
            except Exception as e:
                msg = str(e).lower()
                is_quota = any(x in msg for x in ["insufficient", "quota", "额度", "余额", "billing", "exceeded", "credits", "limit"])
                is_model = "404" in msg or "model is unavailable" in msg or "not found" in msg or "user safety" in msg
                if (is_quota or is_model) and self.gemini_api_key:
                    logger.warning(f"OpenRouter failed ({e}) — auto-fallback to Gemini")
                    return await self._chat_gemini(messages, temperature, retries, json_mode)
                raise
        if self.provider == PROVIDER_FELO and self.felo_api_key:
            try:
                return await self._chat_felo(messages, temperature, retries, json_mode)
            except Exception as e:
                msg = str(e).lower()
                is_quota = any(x in msg for x in ["insufficient", "quota", "额度", "余额不足", "billing", "exceeded"])
                if is_quota and self.gemini_api_key:
                    logger.warning(f"Felo quota/auth failed ({e}) — auto-fallback to Gemini")
                    return await self._chat_gemini(messages, temperature, retries, json_mode)
                raise
        if self.provider == PROVIDER_OX and self.ox_api_key:
            try:
                return await self._chat_ox(messages, temperature, retries, json_mode)
            except Exception as e:
                msg = str(e).lower()
                is_quota = "insufficient_user_quota" in msg or "用户额度不足" in msg or "quota" in msg and "403" in msg
                is_auth = "403" in msg and ("quota" in msg or "insufficient" in msg or "额度" in msg)
                if (is_quota or is_auth or "insufficient" in msg) and self.gemini_api_key:
                    logger.warning(f"OX quota exhausted ({e}) — auto-fallback to Gemini")
                    return await self._chat_gemini(messages, temperature, retries, json_mode)
                raise
        return await self._chat_gemini(messages, temperature, retries, json_mode)

    async def _chat_openrouter(self, messages, temperature=0.3, retries=3, json_mode=False):
        _, or_async = _get_openrouter_clients()
        if not or_async:
            raise RuntimeError("OpenRouter client not initialized — check OPENROUTER_API_KEY")

        kwargs = {"model": self.openrouter_model, "messages": messages, "temperature": temperature}

        extra = {"reasoning": {"enabled": True}}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(retries + 1):
            try:
                resp = await or_async.chat.completions.create(**kwargs, extra_body=extra)
                content = resp.choices[0].message.content or ""
                if content.strip().lower().startswith("user safety:"):
                    raise RuntimeError(f"OpenRouter content-safety model returned '{content.strip()}' — switch OPENROUTER_MODEL to liquid/lfm-2.5-2.6b:free")
                return content
            except Exception as e:
                msg = str(e).lower()
                if "user safety:" in msg or "content-safety" in msg:
                    logger.error(f"OpenRouter safety-model error — Gemini fallback: {e}")
                    raise
                if any(x in msg for x in ["insufficient", "quota", "credits", "limit", "billing", "exceeded", "rate-limited upstream"]):

                    logger.error(f"OpenRouter quota/rate-limit — fast fallback: {e}")
                    raise
                is_rate = "429" in msg or "rate" in msg or "too many" in msg
                logger.error(f"OpenRouter API Request failed (attempt {attempt+1}): {e}")
                if is_rate and attempt < retries:
                    await asyncio.sleep((attempt + 1) * 2)
                    continue
                if attempt < retries:
                    await asyncio.sleep(1)
                    continue
                raise

    async def _chat_felo(self, messages, temperature=0.3, retries=3, json_mode=False):
        _, felo_async = _get_felo_clients()
        if not felo_async:
            raise RuntimeError("Felo client not initialized — check FELO_API_KEY / FELO_BASE_URL")
        kwargs = {"model": self.felo_model, "messages": messages, "temperature": temperature}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        for attempt in range(retries + 1):
            try:
                resp = await felo_async.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content
                return content or ""
            except Exception as e:
                msg = str(e).lower()
                if any(x in msg for x in ["insufficient", "quota", "额度", "余额", "billing"]) :
                    logger.error(f"Felo quota exhausted — not retrying: {e}")
                    raise
                is_rate = "429" in msg or "rate" in msg or "too many" in msg
                logger.error(f"Felo API Request failed (attempt {attempt+1}): {e}")
                if is_rate and attempt < retries:
                    await asyncio.sleep((attempt + 1) * 5)
                    continue
                if attempt < retries:
                    await asyncio.sleep(2)
                    continue
                raise

    async def _chat_ox(self, messages, temperature=0.3, retries=3, json_mode=False):
        _, ox_async = _get_ox_clients()
        if not ox_async:
            raise RuntimeError("OX client not initialized — check OX_API_KEY / OX_BASE_URL")
        kwargs = {"model": self.ox_model, "messages": messages, "temperature": temperature}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        for attempt in range(retries + 1):
            try:
                resp = await ox_async.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content
                return content or ""
            except Exception as e:
                msg = str(e).lower()
                if "insufficient_user_quota" in msg or "用户额度不足" in msg or ("403" in msg and "quota" in msg):
                    logger.error(f"OX quota exhausted — not retrying: {e}")
                    raise
                is_rate = "429" in msg or "rate" in msg or "too many" in msg
                logger.error(f"OX API Request failed (attempt {attempt+1}): {e}")
                if is_rate and attempt < retries:
                    await asyncio.sleep((attempt + 1) * 5)
                    continue
                if attempt < retries:
                    await asyncio.sleep(2)
                    continue
                raise

    async def _chat_gemini(self, messages, temperature=0.3, retries=3, json_mode=False):
        contents = []
        for m in messages:
            role = "user" if m["role"] in ["user", "system"] else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        gen_config = {"temperature": temperature, "topP": 0.95, "maxOutputTokens": 8192}
        if json_mode:
            gen_config["responseMimeType"] = "application/json"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
        for attempt in range(retries + 1):
            try:
                response = await _google_client.post(url, json={"contents": contents, "generationConfig": gen_config})
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
                logger.error(f"Gemini API Request failed: {e}")
                if attempt < retries:
                    await asyncio.sleep(2)
                    continue
                raise

    async def chat_json(self, messages, temperature=0.1):
        if "JSON" not in messages[0]["content"]:
            messages[0]["content"] += " Return valid JSON."

        if self.provider == PROVIDER_OPENROUTER:
            use_json_mode = False
        elif self.provider in (PROVIDER_FELO, PROVIDER_OX):
            use_json_mode = True
        else:
            use_json_mode = False if "gemma" in self.gemini_model.lower() else True
        raw = await self.chat(messages, temperature=temperature, json_mode=use_json_mode)
        import re
        match = re.search(r'(\{.*\})', raw, re.DOTALL)
        if match:
            clean = match.group(1)
        else:
            clean = raw.strip()
        if "```json" in clean:
            clean = clean.split("```json")[1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[1].split("```")[0].strip()
        return clean

    async def chat_vision_ox(self, prompt_text: str, image_b64: str, mime: str = "image/jpeg"):
        if self.provider == PROVIDER_OPENROUTER and self.openrouter_api_key:
            _, or_async = _get_openrouter_clients()
            if or_async:
                try:
                    messages = [{"role": "user", "content": [{"type": "text", "text": prompt_text}, {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}}]}]
                    resp = await or_async.chat.completions.create(model=self.openrouter_model, messages=messages, temperature=0.1)
                    return resp.choices[0].message.content or ""
                except Exception as e:
                    logger.warning(f"OpenRouter vision failed, trying fallback: {e}")
        if self.felo_api_key:
            _, felo_async = _get_felo_clients()
            if felo_async:
                try:
                    messages = [{"role": "user", "content": [{"type": "text", "text": prompt_text}, {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}}]}]
                    resp = await felo_async.chat.completions.create(model=self.felo_model, messages=messages, temperature=0.1)
                    return resp.choices[0].message.content or ""
                except Exception:
                    pass
        _, ox_async = _get_ox_clients()
        if ox_async:
            messages = [{"role": "user", "content": [{"type": "text", "text": prompt_text}, {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}}]}]
            resp = await ox_async.chat.completions.create(model=self.ox_model, messages=messages, temperature=0.1)
            return resp.choices[0].message.content or ""
        raise RuntimeError("Vision client not initialized")
