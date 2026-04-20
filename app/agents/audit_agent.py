import json
from app.llm.llm_client import LLMClient

class AuditAgent:
    def __init__(self):
        self.llm = LLMClient()

    def audit(self, question: str, answer: str, contexts: list):
        """
        Verifies if the answer is supported by the context and relevant to the question.
        Returns a confidence score and reasoning.
        """
        context_text = "\n\n".join([c["text"] for c in contexts])
        
        system_prompt = (
            "You are an AI Auditor. Your job is to verify if an answer is strictly "
            "supported by the provided context. You must also check if the answer "
            "directly addresses the question."
        )
        
        user_prompt = (
            f"Context:\n{context_text}\n\n"
            f"Question: {question}\n"
            f"Answer: {answer}\n\n"
            "Evaluate the answer based on the context. Return a JSON object with:\n"
            "- 'is_supported': boolean\n"
            "- 'is_relevant': boolean\n"
            "- 'confidence_score': float (0.0 to 1.0)\n"
            "- 'reasoning': string"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            raw_json = self.llm.chat_json(messages)
            return json.loads(raw_json)
        except Exception as e:
            return {
                "is_supported": False,
                "is_relevant": False,
                "confidence_score": 0.0,
                "reasoning": f"Audit failed: {str(e)}"
            }
