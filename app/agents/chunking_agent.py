from sentence_transformers import SentenceTransformer
import uuid

class ChunkingAgent:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def chunk(self, source_data: dict, chunk_size=250):
        chunks = []

        for block in source_data["content"]:
            words = block["text"].split()
            for i in range(0, len(words), chunk_size):
                chunk_text = " ".join(words[i:i+chunk_size])
                chunks.append({
                    "chunk_id": f"chunk_{uuid.uuid4().hex[:8]}",
                    "source_id": block["source_id"],
                    "text": chunk_text
                })
        return chunks

    def embed(self, chunks: list):
        texts = [c["text"] for c in chunks]
        embeddings = self.model.encode(texts)
        return embeddings
