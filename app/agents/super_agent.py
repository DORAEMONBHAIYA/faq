from app.llm.llm_client import LLMClient
import json

class SuperAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def generate_batch(self, chunks, num_faqs, target_domain="General"):
        """Unified Batch Generation focused on a specific target domain."""
        
        context_block = ""
        for i, c in enumerate(chunks):
            context_block += f"--- CHUNK {i+1} ---\n{c['text']}\n\n"

        prompt = [
            {
                "role": "system", 
                "content": f"You are the Aquila SuperAgent. You are an expert in the {target_domain} domain. "
                           f"Your goal is to generate a professional FAQ batch STRICTLY for the {target_domain} perspective. "
                           "You must: 1. Generate FAQs. 2. Score them (0-1). 3. Explain logic. "
                           "Strictly ground all answers in the context. Return ONLY a JSON object."
            },
            {
                "role": "user", 
                "content": f"CONTEXT BLOCKS:\n{context_block}\n"
                           f"TARGET DOMAIN: {target_domain}\n"
                           f"TASK: Generate {num_faqs} high-quality FAQs specifically relevant to {target_domain}.\n"
                           "REQUIRED JSON FORMAT:\n"
                           "{\n"
                           "  \"faqs\": [\n"
                           "    {\n"
                           "      \"question\": \"...\",\n"
                           "      \"answer\": \"...\",\n"
                           "      \"scores\": {\"relevance\": 0.9, \"faithfulness\": 1.0, \"clarity\": 0.9, \"difficulty\": 0.5},\n"
                           "      \"why_generated\": \"...\",\n"
                           "      \"source_reference\": \"...\"\n"
                           "    }\n"
                           "  ]\n"
                           "}"
            }
        ]
        
        try:
            res_raw = await self.llm.chat_json(prompt, temperature=0.2)
            data = json.loads(res_raw)
            if isinstance(data, list): data = data[0]
            return data
        except Exception as e:
            print(f"SuperAgent Error: {e}")
            return None
