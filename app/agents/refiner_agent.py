from app.llm.llm_client import LLMClient

class RefinerAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def refine(self, question, answer, context, critique):
        """Improve an FAQ based on validator feedback."""
        prompt = [
            {"role": "system", "content": "You are a Professional Editor. Your goal is to improve the clarity and flow of FAQs without altering facts or adding outside info. Strictly adhere to the context."},
            {"role": "user", "content": f"CONTEXT:\n{context}\n\nORIGINAL FAQ:\nQ: {question}\nA: {answer}\n\nCRITIQUE:\n{critique}\n\nReturn the improved FAQ in this format:\nQ: [Question]\nA: [Answer]"}
        ]
        
        res = await self.llm.chat(prompt)
        
        # Simple parser
        lines = res.strip().split("\n")
        new_q, new_a = question, answer
        for l in lines:
            if l.startswith("Q:"): new_q = l[2:].strip()
            if l.startswith("A:"): new_a = l[2:].strip()
        
        return new_q, new_a
