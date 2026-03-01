from app.llm.glm_client import GLMClient

class QuestionAgent:
    def __init__(self):
        self.llm = GLMClient()

    def generate(self, text: str, n=5):
        messages = [
            {"role": "system", "content": "Generate diverse FAQ questions from the text."},
            {"role": "user", "content": f"Text:\n{text}\n\nGenerate {n} FAQs."}
        ]
        raw = self.llm.chat(messages)
        return [q.strip("-• ") for q in raw.split("\n") if q.strip()]
