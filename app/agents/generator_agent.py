from app.llm.llm_client import LLMClient
import json

class GeneratorAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def generate_from_chunk(self, chunk_text, domain_info):
        """Generate a grounded FAQ with explainability."""
        prompt = [
            {
                "role": "system", 
                "content": f"You are a Knowledge Extraction Agent specializing in the {domain_info.get('domain', 'General')} domain. "
                           "Create a high-value FAQ from the text. Be concise. Return ONLY JSON."
            },
            {
                "role": "user", 
                "content": f"TEXT:\n{chunk_text}\n\n"
                           "INSTRUCTIONS:\n"
                           "1. Question must be clear.\n"
                           "2. Answer must be strictly from text.\n"
                           "3. Provide 'why_generated' (reasoning).\n"
                           "4. Provide 'source_reference' (a short quote or key phrase).\n\n"
                           "Return JSON:\n"
                           "{\"question\": \"...\", \"answer\": \"...\", \"why_generated\": \"...\", \"source_reference\": \"...\"}"
            }
        ]
        
        try:
            res_raw = await self.llm.chat_json(prompt)
            data = json.loads(res_raw)
            if isinstance(data, list): data = data[0]
            return data
        except Exception:
            return None
