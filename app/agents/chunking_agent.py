import httpx
import uuid
import asyncio
import logging
from app.config import GEMINI_API_KEY, GEMINI_EMBED_MODEL, OX_API_KEY, OX_BASE_URL, OX_EMBED_MODEL, LLM_PROVIDER, PROVIDER_OX, CHUNK_SIZE

logger = logging.getLogger("ChunkingAgent")

class ChunkingAgent:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.model_name = GEMINI_EMBED_MODEL
        self.use_ox = LLM_PROVIDER == PROVIDER_OX and bool(OX_API_KEY) and bool(OX_EMBED_MODEL)

    def chunk(self, source_data: dict, chunk_size=CHUNK_SIZE):
        chunks = []
        for block in source_data["content"]:
            words = block["text"].split()
            for i in range(0, len(words), chunk_size):
                chunk_text = " ".join(words[i:i+chunk_size])
                chunks.append({
                    "chunk_id": f"chunk_{uuid.uuid4().hex[:8]}",
                    "source_id": block.get("source_id", "unknown"),
                    "text": chunk_text
                })
        return chunks

    async def _get_single_gemini_embedding(self, client, text):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:embedContent?key={self.api_key}"
        payload = {
            "model": f"models/{self.model_name}",
            "content": {"parts": [{"text": str(text)}]},
            "taskType": "RETRIEVAL_DOCUMENT"
        }
        res = await client.post(url, json=payload)
        if res.status_code != 200:
            logger.error(f"Gemini Embedding API Error ({res.status_code}): {res.text}")
            res.raise_for_status()
        return res.json()["embedding"]["values"]

    async def _get_ox_embeddings(self, texts: list):
        """Use OX OpenAI-compatible embeddings endpoint."""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(base_url=OX_BASE_URL, api_key=OX_API_KEY)

            resp = await client.embeddings.create(model=OX_EMBED_MODEL, input=texts)

            return [d.embedding for d in resp.data]
        except Exception as e:
            logger.error(f"OX Embedding failed, falling back to Gemini: {e}")
            raise

    async def embed(self, inputs: list):
        """Uses OX embeddings if configured, otherwise Gemini — parallelized."""
        if not inputs:
            return []
        texts = [c["text"] if isinstance(c, dict) else c for c in inputs]

        if self.use_ox:
            try:

                all_embs = []
                for i in range(0, len(texts), 100):
                    batch = texts[i:i+100]
                    embs = await self._get_ox_embeddings(batch)
                    all_embs.extend(embs)
                return all_embs
            except Exception:

                pass

        async with httpx.AsyncClient(timeout=60.0) as client:
            semaphore = asyncio.Semaphore(50)
            async def throttled_embed(text):
                async with semaphore:
                    return await self._get_single_gemini_embedding(client, text)
            tasks = [throttled_embed(t) for t in texts]
            all_embeddings = await asyncio.gather(*tasks)
        return all_embeddings
