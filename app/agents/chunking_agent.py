import httpx
import uuid
import asyncio
import logging
from app.config import GEMINI_API_KEY, CHUNK_SIZE

logger = logging.getLogger("ChunkingAgent")

class ChunkingAgent:
    def __init__(self):
        self.api_key = GEMINI_API_KEY

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

    async def _get_single_embedding(self, client, text):
        """Internal helper for parallel embedding calls."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={self.api_key}"
        payload = {
            "model": "models/gemini-embedding-001",
            "content": {"parts": [{"text": text}]}
        }
        res = await client.post(url, json=payload)
        if res.status_code != 200:
            logger.error(f"Gemini API Error ({res.status_code}): {res.text}")
            res.raise_for_status()
        return res.json()["embedding"]["values"]

    async def embed(self, inputs: list):
        """Uses Gemini API with parallel requests for reliability and speed."""
        if not inputs:
            return []
        
        texts = [c["text"] if isinstance(c, dict) else c for c in inputs]
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Run all embedding requests in parallel (capped at 50 to avoid rate limits)
            semaphore = asyncio.Semaphore(50)
            
            async def throttled_embed(text):
                async with semaphore:
                    return await self._get_single_embedding(client, text)
            
            tasks = [throttled_embed(t) for t in texts]
            all_embeddings = await asyncio.gather(*tasks)
                
        return all_embeddings
