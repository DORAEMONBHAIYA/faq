import os

# API Providers
PROVIDER_GEMINI = "gemini"

# Active Provider (Locked to Gemini)
LLM_PROVIDER = PROVIDER_GEMINI

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Endpoints (Native Gemini doesn't use a single endpoint string in config, but we keep it for consistency)
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta"

# Model Names
GEMINI_MODEL = "gemma-3-27b-it"

# Generation Settings
MAX_NUM_FAQS = 20
DEFAULT_NUM_FAQS = 5
CHUNK_SIZE = 250
MAX_WEB_WORDS = 2500
