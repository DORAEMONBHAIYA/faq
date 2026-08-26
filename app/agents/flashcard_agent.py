from app.llm.llm_client import LLMClient
from app.config import SUPPORTED_LANGUAGES
from app.utils.text_cleaner import clean_answer_text
import json

class FlashcardAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def generate(self, chunks, num_cards=8, target_language="auto", target_domain="General"):
        context_block = ""
        for i, c in enumerate(chunks):
            context_block += f"--- CHUNK {i+1} ---\n{c['text']}\n\n"

        lang_name = SUPPORTED_LANGUAGES.get(target_language, target_language) if target_language != "auto" else "the same language as the source"
        prompt = [
            {
                "role": "system",
                "content": f"You are Aquila Flashcard Expert ({target_domain}). Create {num_cards} interactive flashcards. Language: {lang_name}. "
                           "Cards must be grounded ONLY in provided context. No hallucinations. "
                           "STYLE: Natural, student-friendly. Do NOT mention 'Chunk', 'Chunks', or 'As mentioned in Chunk...' in front/back. "
                           "CRITICAL: Output MUST be valid JSON only — no 'User Safety:' prefix, no markdown."
            },
            {
                "role": "user",
                "content": f"CONTEXT:\n{context_block}\n"
                           f"Generate {num_cards} flashcards in this EXACT JSON (double-quoted keys):\n"
                           "{\n  \"flashcards\": [\n"
                           "    {\"front\": \"question/prompt (no chunk refs)\", \"back\": \"concise answer (no chunk refs)\", \"difficulty\": 0.5, \"source_reference\": \"chunk id\"}\n  ]\n"
                           "}\n"
                           f"All front/back must be in {lang_name}. Front = clear question, Back = factual answer from context. Return ONLY JSON. Do NOT include hint field. NEVER write 'Chunk' in front/back."
            }
        ]
        for attempt in range(2):
            try:
                raw = await self.llm.chat_json(prompt, temperature=0.3 if attempt==0 else 0.4)
                print(f"--- Flashcard RAW (attempt {attempt+1}) ---\n{raw[:1000]}")
                if raw.strip().lower().startswith("user safety"):
                    raise ValueError("Safety classifier output — wrong model")
                data = json.loads(raw)
                if isinstance(data, list):
                    data = data[0]
                if "flashcards" not in data or not isinstance(data["flashcards"], list) or len(data["flashcards"])==0:
                    raise ValueError("Missing flashcards")
                for card in data["flashcards"]:
                    if "front" in card:
                        card["front"] = clean_answer_text(card["front"])
                    if "back" in card:
                        card["back"] = clean_answer_text(card["back"])
                return data
            except Exception as e:
                print(f"FlashcardAgent Error (attempt {attempt+1}): {e}")
                if attempt==1: return None
                prompt[1]["content"] += "\nSTRICT: Return ONLY JSON."
        return None
