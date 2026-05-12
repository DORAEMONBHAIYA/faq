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
                "content": f"You are the Aquila SuperAgent. Expert in {target_domain}. "
                           f"TASK: Generate {num_faqs} professional FAQs based ONLY on the provided context. "
                           "FORMAT: Respond ONLY with a valid JSON object. No thoughts. No markdown. "
                           "The JSON must start with '{' and contain actual questions and answers from the text."
            },
            {
                "role": "user", 
                "content": f"CONTEXT:\n{context_block}\n"
                           f"Generate {num_faqs} FAQs in this EXACT JSON structure:\n"
                           "{\n"
                           "  \"faqs\": [\n"
                           "    {\n"
                           "      \"question\": \"(actual question from text)\",\n"
                           "      \"answer\": \"(detailed answer from text)\",\n"
                           "      \"scores\": {\"relevance\": 0.9, \"faithfulness\": 1.0, \"clarity\": 0.9, \"difficulty\": 0.5},\n"
                           "      \"why_generated\": \"brief reason\",\n"
                           "      \"source_reference\": \"chunk ID\"\n"
                           "    }\n"
                           "  ]\n"
                           "}"
            }
        ]
        
        try:
            res_raw = await self.llm.chat_json(prompt, temperature=0.2)
            print(f"\n--- RAW LLM OUTPUT ---\n{res_raw}\n----------------------")
            data = json.loads(res_raw)
            if isinstance(data, list): data = data[0]
            return data
        except Exception as e:
            print(f"SuperAgent Error: {e}")
            return None
