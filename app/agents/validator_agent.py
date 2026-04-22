from app.llm.llm_client import LLMClient
import json

class ValidatorAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def validate_faq(self, question, answer, context, domain_info):
        """Perform multi-dimensional scoring and hallucination detection."""
        prompt = [
            {
                "role": "system", 
                "content": f"You are a Senior Quality Assurance Agent for AI systems. Your domain is {domain_info.get('domain', 'General')}. "
                           "Score the FAQ based on the provided context. Return ONLY a JSON object."
            },
            {
                "role": "user", 
                "content": f"CONTEXT:\n{context}\n\nFAQ:\nQ: {question}\nA: {answer}\n\n"
                           "Evaluate based on these criteria (0.0 to 1.0):\n"
                           "1. relevance: Does it address a key concept?\n"
                           "2. faithfulness: Is it 100% supported by the context (no hallucinations)?\n"
                           "3. clarity: Is it easy to understand?\n"
                           "4. difficulty: 0.0=easy, 1.0=advanced.\n\n"
                           "Return JSON:\n"
                           "{\"relevance\": 0.0, \"faithfulness\": 0.0, \"clarity\": 0.0, \"difficulty\": 0.0, \"hallucination_detected\": bool, \"critique\": \"...\"}"
            }
        ]
        
        try:
            res_raw = await self.llm.chat_json(prompt)
            data = json.loads(res_raw)
            if isinstance(data, list): data = data[0]
            return data
        except Exception:
            return {"relevance": 0.5, "faithfulness": 0.5, "clarity": 0.5, "difficulty": 0.5, "hallucination_detected": True, "critique": "Validation failed"}
