import json
import numpy as np
from app.llm.llm_client import LLMClient
from app.agents.chunking_agent import ChunkingAgent

class DomainAgent:
    def __init__(self):
        self.llm = LLMClient()
        self.chunker = ChunkingAgent()
        self.categories = [
            "Technical", "Medical", "Legal", "Business", "Academic", 
            "Celebrity", "Biography", "Entertainment", "History", "Science", "General"
        ]
        self.category_embeddings = None

    async def _ensure_category_embeddings(self):
        if self.category_embeddings is None:
            # Pre-calculate embeddings for our core categories
            embs = await self.chunker.embed(self.categories)
            self.category_embeddings = {cat: emb for cat, emb in zip(self.categories, embs)}

    async def detect_topics(self, sample_text: str):
        """
        Hybrid Semantic System: Uses embeddings to classify text into categories.
        Saves 1 LLM generation call per ingest.
        """
        await self._ensure_category_embeddings()
        
        # Embed the sample text (first 3000 chars)
        text_emb = (await self.chunker.embed([sample_text[:3000]]))[0]
        
        # Calculate similarity with all categories
        matches = []
        
        a = np.array(text_emb)
        norm_a = np.linalg.norm(a)
        
        for cat, b_list in self.category_embeddings.items():
            b = np.array(b_list)
            sim = np.dot(a, b) / (norm_a * np.linalg.norm(b))
            matches.append((cat, sim))
        
        # Sort by similarity and take top 3 above threshold
        matches.sort(key=lambda x: x[1], reverse=True)
        top_topics = [m[0] for m in matches if m[1] > 0.35]
        
        # Ensure at least General is returned
        if not top_topics: top_topics = ["General"]
        return top_topics[:3]

    async def generate_title(self, text: str) -> str:
        """Generates a short, catchy title (3-5 words) for the document content."""
        prompt = [
            {"role": "system", "content": "You are a Creative Writer. Summarize the text into a very short, catchy, professional title (MAX 5 WORDS). Return ONLY the title text."},
            {"role": "user", "content": f"Text: {text[:2000]}\n\nTitle:"}
        ]
        
        try:
            title = await self.llm.chat(prompt)
            return title.strip().replace('"', '').replace('*', '')
        except:
            return "Untitled Generation"

    async def detect_domain(self, sample_text: str):
        """Categorize the text into a single domain with tone instructions."""
        # Reuse our hybrid detection for the domain name
        topics = await self.detect_topics(sample_text)
        domain = topics[0]
        
        return {
            "domain": domain, 
            "confidence": 0.9, 
            "tone_instructions": f"Maintain a professional {domain} tone."
        }
