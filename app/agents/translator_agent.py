import json
from app.llm.llm_client import LLMClient
from app.config import SUPPORTED_LANGUAGES

class TranslatorAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def translate_task(self, task: dict, target_lang: str = "en"):
        """Translate a completed task's result to target language, return new result list."""
        mode = task.get("mode", "faq")
        source_lang = task.get("language", "auto")
        target_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)
        source_name = SUPPORTED_LANGUAGES.get(source_lang, source_lang)

        if mode == "faq":
            items = task.get("result", [])
            payload = json.dumps({"faqs": items}, ensure_ascii=False)
            prompt = [
                {"role": "system", "content": f"You are a professional translator. Translate from {source_name} to {target_name}. Preserve meaning, keep JSON structure exactly. Return ONLY valid JSON."},
                {"role": "user", "content": f"Translate this JSON to {target_name}. Keep keys same, translate values of 'question' and 'answer' only:\n{payload}\n\nReturn JSON: {{\"faqs\": [...]}}"}
            ]
        elif mode == "flashcards":
            items = task.get("result", [])

            stripped = [{"front": x.get("front",""), "back": x.get("back",""), "difficulty": x.get("difficulty",0.5), "source_reference": x.get("source_reference","")} for x in items]
            payload = json.dumps({"flashcards": stripped}, ensure_ascii=False)
            prompt = [
                {"role": "system", "content": f"You are a professional translator. Translate from {source_name} to {target_name}. Preserve JSON."},
                {"role": "user", "content": f"Translate to {target_name}, keep keys, translate 'front' and 'back' only:\n{payload}\n\nReturn JSON: {{\"flashcards\": [...]}}"}
            ]
        elif mode == "quiz":
            items = task.get("result", [])
            payload = json.dumps({"quiz": items}, ensure_ascii=False)
            prompt = [
                {"role": "system", "content": f"You are a professional translator. Translate from {source_name} to {target_name}. Keep JSON, translate question, options, explanation."},
                {"role": "user", "content": f"Translate this quiz JSON to {target_name}. Translate 'question','options','explanation' (keep correct_index):\n{payload}\n\nReturn JSON: {{\"quiz\": [...]}}"}
            ]
        else:
            return None

        try:
            raw = await self.llm.chat_json(prompt, temperature=0.2)
            data = json.loads(raw)
            if isinstance(data, list):
                data = data[0]

            key = mode if mode != "faq" else "faqs"
            if key not in data:

                for k in ["faqs","flashcards","quiz"]:
                    if k in data:
                        key = k
                        break
            translated_list = data.get(key, [])
            if not isinstance(translated_list, list) or len(translated_list)==0:
                return None
            return translated_list
        except Exception as e:
            print(f"Translator error: {e}")
            return None
