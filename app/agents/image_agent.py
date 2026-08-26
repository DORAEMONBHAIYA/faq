import uuid
import base64
import httpx
from PIL import Image
import io
from app.config import GEMINI_API_KEY, GEMINI_VISION_MODEL, OX_API_KEY, LLM_PROVIDER, PROVIDER_OX
from app.utils.text_cleaner import clean_text

class ImageAgent:
    """OCR via OX Vision if provider=ox, else Gemini Vision."""

    def __init__(self):
        self.provider = LLM_PROVIDER
        self.gemini_api_key = GEMINI_API_KEY
        self.gemini_model = GEMINI_VISION_MODEL
        self.use_ox = self.provider == PROVIDER_OX and bool(OX_API_KEY)

    def _preprocess(self, file_path: str) -> bytes:
        from app.config import MAX_IMAGE_DIMENSION
        img = Image.open(file_path)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        w, h = img.size
        if max(w, h) > MAX_IMAGE_DIMENSION:
            ratio = MAX_IMAGE_DIMENSION / max(w, h)
            img = img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()

    async def _ocr_gemini(self, b64: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_api_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Extract ALL text visible in this image. Preserve structure and paragraphs. If multilingual (Hindi/Tamil/Malayalam/Gujarati etc.), keep original script. Return ONLY the extracted text, no commentary."},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64}}
                ]
            }],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192}
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()
            if "candidates" not in data or not data["candidates"]:
                raise RuntimeError(f"Vision OCR failed: {data}")
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _ocr_ox(self, b64: str) -> str:
        from app.llm.llm_client import LLMClient
        llm = LLMClient()
        prompt = "Extract ALL text visible in this image. Preserve structure and paragraphs. If multilingual (Hindi/Tamil/Malayalam/Gujarati etc.), keep original script. Return ONLY the extracted text, no commentary."
        return await llm.chat_vision_ox(prompt, b64, "image/jpeg")

    async def ingest(self, file_path: str) -> dict:
        image_bytes = self._preprocess(file_path)
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        web_id = f"img_{uuid.uuid4().hex[:8]}"

        text = None
        if self.use_ox:
            try:
                text = await self._ocr_ox(b64)
            except Exception as e:
                print(f"OX Vision failed, fallback to Gemini: {e}")
                text = await self._ocr_gemini(b64)
        else:
            text = await self._ocr_gemini(b64)

        clean = clean_text(text)
        return {
            "source_id": web_id,
            "type": "image",
            "content": [{"source_id": web_id, "text": clean}]
        }

    def ingest_sync(self, file_path: str) -> dict:
        import asyncio
        return asyncio.run(self.ingest(file_path))
