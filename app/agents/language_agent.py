import re
from app.llm.llm_client import LLMClient
from app.config import SUPPORTED_LANGUAGES

try:
    from langdetect import detect as langdetect_detect
    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False
    langdetect_detect = None

LANG_MAP = {
    "en": "en", "hi": "hi", "ta": "ta", "ml": "ml", "gu": "gu",
    "mr": "mr", "bn": "bn", "te": "te", "kn": "kn",

    "ne": "hi",
}

class LanguageAgent:
    def __init__(self):
        self.llm = LLMClient()

    def _heuristic_detect(self, text: str) -> str:
        """Fast heuristic: unicode ranges for Indian scripts."""
        if not text:
            return "en"

        if re.search(r"[\u0900-\u097F]", text):

            return "hi"
        if re.search(r"[\u0B80-\u0BFF]", text):
            return "ta"
        if re.search(r"[\u0D00-\u0D7F]", text):
            return "ml"
        if re.search(r"[\u0A80-\u0AFF]", text):
            return "gu"
        if re.search(r"[\u0980-\u09FF]", text):
            return "bn"
        if re.search(r"[\u0C00-\u0C7F]", text):
            return "te"
        if re.search(r"[\u0C80-\u0CFF]", text):
            return "kn"
        return "en"

    async def detect(self, text: str) -> str:
        """Detect language, returns SUPPORTED_LANGUAGES key."""
        sample = text[:2000] if len(text) > 2000 else text

        heur = self._heuristic_detect(sample)
        if heur != "en":
            return heur

        if HAS_LANGDETECT:
            try:
                code = langdetect_detect(sample)
                mapped = LANG_MAP.get(code, "en")
                if mapped in SUPPORTED_LANGUAGES:
                    return mapped
            except Exception:
                pass

        return "en"

    def normalize(self, lang: str) -> str:
        lang = (lang or "auto").lower().strip()
        if lang in SUPPORTED_LANGUAGES:
            return lang

        rev = {v.lower(): k for k, v in SUPPORTED_LANGUAGES.items()}
        if lang in rev:
            return rev[lang]
        return "auto"

    def display_name(self, lang: str) -> str:
        return SUPPORTED_LANGUAGES.get(lang, lang)
