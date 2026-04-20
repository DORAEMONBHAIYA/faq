from app.llm.llm_client import LLMClient

class QuestionAgent:
    def __init__(self):
        self.llm = LLMClient()

    def generate_from_chunk(self, chunk_text: str):
        """Generates exactly ONE high-quality question from a specific chunk of text."""
        messages = [
            {"role": "system", "content": "You are an expert FAQ creator. Your task is to extract the MOST important information from the text and turn it into ONE clear, standalone question."},
            {"role": "user", "content": f"Text:\n{chunk_text}\n\nGenerate exactly ONE question based on this text. Do not provide any other text."}
        ]
        q = self.llm.chat(messages, temperature=0.2).strip("-• ")
        return q

    def deduplicate(self, questions: list):
        """Removes exact and near-duplicate questions."""
        seen = set()
        unique = []
        for q in questions:
            clean_q = q.lower().strip("?").strip()
            if clean_q not in seen:
                seen.add(clean_q)
                unique.append(q)
        return unique

    def generate(self, text: str, n=5):
        # Keep this for backward compatibility or bulk generation
        messages = [
            {"role": "system", "content": "Generate distinct, non-overlapping FAQ questions from the text."},
            {"role": "user", "content": f"Text:\n{text}\n\nGenerate {n} unique FAQs. Ensure no two questions cover the same topic."}
        ]
        raw = self.llm.chat(messages)
        qs = [q.strip("-• ") for q in raw.split("\n") if q.strip() and "?" in q]
        return self.deduplicate(qs)[:n]
