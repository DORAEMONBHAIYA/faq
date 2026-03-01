from app.llm.glm_client import GLMClient

class AnswerAgent:
    def __init__(self):
        self.llm = GLMClient()

    def answer(self, question: str, contexts: list):
        context_text = "\n\n".join([c["text"] for c in contexts])

        messages = [
            {"role": "system", "content": "Answer strictly using the provided context."},
            {
                "role": "user",
                "content": f"Context:\n{context_text}\n\nQuestion:\n{question}"
            }
        ]
        return self.llm.chat(messages)
