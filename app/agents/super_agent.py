from app.llm.llm_client import LLMClient
from app.config import SUPPORTED_LANGUAGES
from app.utils.text_cleaner import clean_answer_text
import json

class SuperAgent:
    def __init__(self):
        self.llm = LLMClient()

    async def generate_batch(self, chunks, num_faqs, target_domain="General", target_language="auto"):
        """Unified Batch Generation — robust JSON handling with retry + safety-model guard."""
        lang_name = SUPPORTED_LANGUAGES.get(target_language, target_language) if target_language != "auto" else "the same language as the source"

        context_block = ""
        for i, c in enumerate(chunks):
            context_block += f"--- CHUNK {i+1} ---\n{c['text']}\n\n"

        base_prompt = [
            {
                "role": "system",
                "content": f"You are the Aquila SuperAgent. Expert in {target_domain}. Language: {lang_name}. "
                           f"TASK: Generate {num_faqs} professional FAQs based ONLY on the provided context. "
                           "All Q&A must be in the target language. "
                           "STYLE: Student-friendly, natural, self-contained answers. Do NOT mention internal structure like 'Chunk 3', 'Chunks 4 and 5', 'As mentioned in Chunk...' — never reference chunks in question or answer. "
                           "The 'source_reference' field is metadata only; do NOT copy it into answer text. "
                           "CRITICAL: Output MUST be valid JSON only — no prefix like 'User Safety:', no markdown, no thoughts. "
                           "The JSON must start with '{' and contain actual questions and answers from the text."
            },
            {
                "role": "user",
                "content": f"CONTEXT:\n{context_block}\n"
                           f"Generate {num_faqs} FAQs in {lang_name} in this EXACT JSON structure (keys must be double-quoted):\n"
                           "{\n"
                           "  \"faqs\": [\n"
                           "    {\n"
                           "      \"question\": \"(actual question from text)\",\n"
                           "      \"answer\": \"(natural, detailed answer from text, no chunk references)\",\n"
                           "      \"scores\": {\"relevance\": 0.9, \"faithfulness\": 1.0, \"clarity\": 0.9, \"difficulty\": 0.5},\n"
                           "      \"why_generated\": \"brief reason\",\n"
                           "      \"source_reference\": \"chunk ID\"\n"
                           "    }\n"
                           "  ]\n"
                           "}\n"
                           "REMINDER: Return ONLY JSON. In question/answer, NEVER write 'Chunk', 'Chunks', 'As mentioned in Chunk 3' etc. Answer as if explaining to a student."
            }
        ]

        for attempt in range(2):
            try:
                res_raw = await self.llm.chat_json(base_prompt, temperature=0.2 if attempt==0 else 0.3)
                print(f"\n--- RAW LLM OUTPUT (attempt {attempt+1}) ---\n{res_raw[:1500]}\n----------------------")
                if res_raw.strip().lower().startswith("user safety"):
                    raise ValueError(f"Model returned safety classifier output instead of JSON: {res_raw[:200]} — try switching OPENROUTER_MODEL to meta-llama/llama-3.1-8b-instruct:free")
                data = json.loads(res_raw)
                if isinstance(data, list): data = data[0]
                if "faqs" not in data or not isinstance(data["faqs"], list) or len(data["faqs"])==0:
                    raise ValueError(f"Missing or empty 'faqs' key in: {res_raw[:500]}")

                for faq in data["faqs"]:
                    if "question" in faq:
                        faq["question"] = clean_answer_text(faq["question"])
                    if "answer" in faq:
                        faq["answer"] = clean_answer_text(faq["answer"])
                return data
            except Exception as e:
                print(f"SuperAgent Error (attempt {attempt+1}): {e}")
                if attempt == 1:
                    return None

                base_prompt[1]["content"] += "\n\nSTRICT: Your last output was invalid. Now return ONLY the JSON object, starting with { and ending with }."
        return None
