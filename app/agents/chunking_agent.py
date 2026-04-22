from sentence_transformers import SentenceTransformer
import uuid
from app.config import CHUNK_SIZE

class ChunkingAgent:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def chunk(self, source_data: dict, chunk_size=CHUNK_SIZE):
        chunks = []

        # source_data["content"] is a list of blocks from DocAgent/WebAgent
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

    def embed(self, inputs: list):
        """Handle both list of strings or list of chunk dictionaries."""
        if not inputs:
            return []
        
        if isinstance(inputs[0], dict):
            texts = [c["text"] for c in inputs]
        else:
            texts = inputs # List of strings
            
        embeddings = self.model.encode(texts)
        return embeddings
