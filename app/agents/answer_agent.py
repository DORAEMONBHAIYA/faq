from app.llm.llm_client import LLMClient

class AnswerAgent:
    def __init__(self):
        self.llm = LLMClient()

    def answer(self, question: str, contexts: list):
        context_text = "\n\n".join([c["text"] for c in contexts])

        messages = [
            {"role": "system", "content": "You are a factual Q&A assistant. Answer the user's question using ONLY the provided context. If the answer is not in the context, say 'I cannot find the answer in the provided document.' Do not use external knowledge, do not ask follow-up questions, and do not provide instructions on how to use the system."},
            {
                "role": "user",
                "content": f"DOCUMENT CONTEXT:\n{context_text}\n\nQUESTION:\n{question}\n\nFINAL ANSWER:"
            }
        ]
        return self.llm.chat(messages)
