from app.llm.llm_client import LLMClient
import json

class DomainAgent:
    def __init__(self):
        self.llm = LLMClient()
        self.categories = ["Technical", "Medical", "Legal", "Business", "Academic", "General"]

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

    async def detect_topics(self, sample_text: str):
        """Identify which broad categories are relevant to the text."""
        prompt = [
            {"role": "system", "content": f"You are a Content Classification Expert. Choose from this list: {', '.join(self.categories)}. Return ONLY a JSON list of the categories that are significantly present in the text (max 3)."},
            {"role": "user", "content": f"Analyze this text sample and pick the relevant categories:\n{sample_text[:3000]}\n\nReturn format: [\"Category 1\", \"Category 2\"]"}
        ]
        
        try:
            res_raw = await self.llm.chat_json(prompt)
            data = json.loads(res_raw)
            if not isinstance(data, list): data = ["General"]
            # Filter to ensure only allowed categories are returned
            valid = [c for c in data if c in self.categories]
            return valid if valid else ["General"]
        except Exception:
            return ["General"]

    async def detect_domain(self, sample_text: str):
        """Standard single-domain detection."""
        prompt = [
            {"role": "system", "content": "You are a Domain Classification Expert. Categorize the text. Return ONLY a JSON object."},
            {"role": "user", "content": f"Analyze this text sample:\n{sample_text[:1000]}\n\nReturn format:\n{{\"domain\": \"...\", \"confidence\": 0.0, \"tone_instructions\": \"...\"}}"}
        ]
        
        try:
            res_raw = await self.llm.chat_json(prompt)
            data = json.loads(res_raw)
            if isinstance(data, list): data = data[0]
            return data
        except Exception:
            return {"domain": "General", "confidence": 1.0, "tone_instructions": "Maintain a neutral, helpful tone."}
