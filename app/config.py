import os
from dotenv import load_dotenv
load_dotenv()

PROVIDER_GEMINI = "gemini"
PROVIDER_OX = "ox"
PROVIDER_FELO = "felo"
PROVIDER_OPENROUTER = "openrouter"

_raw_provider = os.getenv("LLM_PROVIDER", "auto").lower()
if _raw_provider == "auto":
    if os.getenv("OPENROUTER_API_KEY"):
        LLM_PROVIDER = PROVIDER_OPENROUTER
    elif os.getenv("FELO_API_KEY"):
        LLM_PROVIDER = PROVIDER_FELO
    elif os.getenv("OX_API_KEY"):
        LLM_PROVIDER = PROVIDER_OX
    else:
        LLM_PROVIDER = PROVIDER_GEMINI
else:
    LLM_PROVIDER = _raw_provider

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OX_API_KEY = os.getenv("OX_API_KEY")
OX_BASE_URL = os.getenv("OX_BASE_URL", "https://tokenra.io/v1")
OX_MODEL = os.getenv("OX_MODEL", "ox-alpha-2")
OX_EMBED_MODEL = os.getenv("OX_EMBED_MODEL", "")
FELO_API_KEY = os.getenv("FELO_API_KEY")
FELO_BASE_URL = os.getenv("FELO_BASE_URL", "https://openapi.felo.ai/api/v1")
FELO_MODEL = os.getenv("FELO_MODEL", "ox-alpha")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

_raw_or_model = os.getenv("OPENROUTER_MODEL", "liquid/lfm-2.5-2.6b:free")

if "content-safety" in _raw_or_model.lower():
    print(f"WARNING: OPENROUTER_MODEL '{_raw_or_model}' is safety classifier — switching to liquid/lfm-2.5-2.6b:free")
    _raw_or_model = "liquid/lfm-2.5-2.6b:free"
if "llama-3.1-8b-instruct" in _raw_or_model.lower():
    print(f"WARNING: OPENROUTER_MODEL '{_raw_or_model}' not free — switching to liquid/lfm-2.5-2.6b:free")
    _raw_or_model = "liquid/lfm-2.5-2.6b:free"
if "gemma-4-31b" in _raw_or_model.lower():
    print(f"WARNING: OPENROUTER_MODEL '{_raw_or_model}' rate-limited — switching to liquid/lfm-2.5-2.6b:free")
    _raw_or_model = "liquid/lfm-2.5-2.6b:free"
OPENROUTER_MODEL = _raw_or_model

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-flash")

GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")

GEMINI_EMBEDDING_MODEL = GEMINI_EMBED_MODEL

if LLM_PROVIDER == PROVIDER_OPENROUTER:
    ACTIVE_MODEL = OPENROUTER_MODEL
elif LLM_PROVIDER == PROVIDER_FELO:
    ACTIVE_MODEL = FELO_MODEL
elif LLM_PROVIDER == PROVIDER_OX:
    ACTIVE_MODEL = OX_MODEL
else:
    ACTIVE_MODEL = GEMINI_MODEL

SUPPORTED_LANGUAGES = {
    "auto": "Auto-Detect",
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "ml": "Malayalam",
    "gu": "Gujarati",
    "mr": "Marathi",
    "bn": "Bengali",
    "te": "Telugu",
    "kn": "Kannada",
}

STUDY_MODES = ["faq", "flashcards", "quiz"]

MAX_NUM_FAQS = 20
DEFAULT_NUM_FAQS = 5
MAX_NUM_CARDS = 20
DEFAULT_NUM_CARDS = 8
MAX_NUM_QUIZ = 15
DEFAULT_NUM_QUIZ = 5
CHUNK_SIZE = 250
MAX_WEB_WORDS = 2500

MAX_FILE_SIZE_DOC = 5 * 1024 * 1024
MAX_FILE_SIZE_IMAGE = 10 * 1024 * 1024
MAX_IMAGE_DIMENSION = 4096
ALLOWED_DOC_EXTS = {".pdf", ".txt", ".docx", ".pptx"}
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIMES = {
    "application/pdf", "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "image/jpeg", "image/png", "image/webp"
}
