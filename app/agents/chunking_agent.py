import httpx
import uuid
import asyncio
from app.config import GEMINI_API_KEY, CHUNK_SIZE

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

    async def embed(self, inputs: list):
        """Uses Gemini Embedding API to save RAM."""
        if not inputs:
            return []
        
        texts = [c["text"] if isinstance(c, dict) else c for c in inputs]
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/embedding-001:batchEmbedContents?key={self.api_key}"
        
        # Batching for Gemini (Max 100 per call)
        all_embeddings = []
        for i in range(0, len(texts), 100):
            batch = texts[i:i+100]
            payload = {
                "requests": [{"model": "models/embedding-001", "content": {"parts": [{"text": t}]}} for t in batch]
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(url, json=payload)
                res.raise_for_status()
                data = res.json()
                all_embeddings.extend([e["values"] for e in data["embeddings"]])
                
        return all_embeddings
