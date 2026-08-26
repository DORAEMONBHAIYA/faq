from app.llm.llm_client import LLMClient
from app.config import SUPPORTED_LANGUAGES
from app.utils.text_cleaner import clean_answer_text
import json

class QuizAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def generate(self, chunks, num_questions=5, target_language="auto", target_domain="General"):
        context_block = ""
        for i, c in enumerate(chunks):
            context_block += f"--- CHUNK {i+1} ---\n{c['text']}\n\n"

        lang_name = SUPPORTED_LANGUAGES.get(target_language, target_language) if target_language != "auto" else "the same language as the source"
        prompt = [
            {
                "role": "system",
                "content": f"You are Aquila Quiz Master ({target_domain}). Create {num_questions} MCQs for students. Language: {lang_name}. "
                           "All questions strictly from context. Provide 4 options, one correct. Include explanation. "
                           "STYLE: Natural, no chunk references. Do NOT write 'Chunk' or 'As mentioned in...' in any field. "
                           "CRITICAL: Output MUST be valid JSON only — no 'User Safety:' prefix, no markdown."
            },
            {
                "role": "user",
                "content": f"CONTEXT:\n{context_block}\n"
                           f"Generate {num_questions} MCQs in this EXACT JSON (double-quoted keys):\n"
                           "{\n  \"quiz\": [\n"
                           "    {\n"
                           "      \"question\": \"...(no chunk refs)\",\n"
                           "      \"options\": [\"A\", \"B\", \"C\", \"D\"],\n"
                           "      \"correct_index\": 0,\n"
                           "      \"explanation\": \"brief why correct (no chunk refs)\",\n"
                           "      \"difficulty\": 0.5,\n"
                           "      \"source_reference\": \"chunk id\"\n"
                           "    }\n  ]\n"
                           "}\n"
                           f"All text in {lang_name}. correct_index is 0-3. Return ONLY JSON. NEVER mention Chunk."
            }
        ]
        for attempt in range(2):
            try:
                raw = await self.llm.chat_json(prompt, temperature=0.3 if attempt==0 else 0.4)
                print(f"--- Quiz RAW (attempt {attempt+1}) ---\n{raw[:1000]}")
                if raw.strip().lower().startswith("user safety"):
                    raise ValueError("Safety classifier output — wrong model")
                data = json.loads(raw)
                if isinstance(data, list):
                    data = data[0]
                if "quiz" not in data or not isinstance(data["quiz"], list) or len(data["quiz"])==0:
                    raise ValueError("Missing quiz")
                for q in data["quiz"]:
                    if "question" in q:
                        q["question"] = clean_answer_text(q["question"])
                    if "explanation" in q:
                        q["explanation"] = clean_answer_text(q["explanation"])
                    if "options" in q and isinstance(q["options"], list):
                        q["options"] = [clean_answer_text(opt) for opt in q["options"]]
                return data
            except Exception as e:
                print(f"QuizAgent Error (attempt {attempt+1}): {e}")
                if attempt==1: return None
                prompt[1]["content"] += "\nSTRICT: Return ONLY JSON."
        return None
