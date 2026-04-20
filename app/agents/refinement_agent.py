from app.llm.llm_client import LLMClient

class RefinementAgent:
    def __init__(self):
        self.llm = LLMClient()

    def refine(self, question: str, answer: str):
        """
        Polishes the language of the question and answer for professional tone and clarity.
        """
        system_prompt = (
            "You are a Content Refiner. Your goal is to improve the clarity, "
            "tone, and conciseness of FAQ entries while preserving the original meaning."
        )
        
        user_prompt = (
            "Please refine the following FAQ entry to make it more professional "
            "and easy to read.\n\n"
            f"Question: {question}\n"
            f"Answer: {answer}\n\n"
            "Return the refined version in the following format:\n"
            "Q: [Refined Question]\nA: [Refined Answer]"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        raw = self.llm.chat(messages)
        
        # Simple parsing
        lines = [line.strip() for line in raw.split("\n") if line.strip()]
        refined_q = question
        refined_a = answer
        
        for line in lines:
            if line.startswith("Q:"):
                refined_q = line[2:].strip()
            elif line.startswith("A:"):
                refined_a = line[2:].strip()
                
        return refined_q, refined_a
