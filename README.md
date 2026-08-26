# 📚 Aquila Learn — Smart Student Learning System

> **From FAQ Generator → Multilingual, Multi-Modal Study Companion**

Aquila Learn is a **multi-agent, RAG-powered learning system** that turns any document, image or website into **FAQs, interactive flashcards, and mock quizzes** — in the student's own language (English, Hindi, Tamil, Malayalam, Gujarati, Marathi, Bengali, Telugu, Kannada).

---

## 🚀 Overview

Instead of blindly summarizing, the system:

- **Ingests everything:** PDF, TXT, DOCX, PPTX, JPG/PNG/WEBP + Website URLs
- **Understands language:** auto-detects script (Devanagari, Tamil, Malayalam, etc.) + `langdetect` + LLM fallback
- **Understands domain:** Technical, Medical, Legal, Academic, etc. via embedding similarity
- **Generates in the right mode & language:** FAQ / Flashcards / Quiz, with tone adapted to domain
- **Keeps it in one chat:** same source → switch between FAQ ↔ Flashcards ↔ Quiz without creating new chats
- **Translates on demand:** any generation can be toggled to English

Built on **FastAPI + MongoDB + FAISS + OpenRouter/Gemini** with a dark, mobile-first UI.

---

## 🧠 Key Features

- 🔹 **Multi-modal ingestion** — `DocumentAgent` (pdfplumber), `FileAgent` (docx/pptx/txt), `ImageAgent` (Gemini/OpenRouter Vision OCR), `WebAgent` (BeautifulSoup, SSRF guard)
- 🔹 **Indian language support** — `LanguageAgent` (heuristic + `langdetect`), 9 languages, auto target `auto`
- 🔹 **Three study modes** — `SuperAgent` (FAQ), `FlashcardAgent` (no hints, flip cards), `QuizAgent` (4-option MCQ + explanation)
- 🔹 **Student-friendly answers** — prompts forbid `Chunk X` leaks; `text_cleaner.clean_answer_text()` strips any `As mentioned in Chunk...` / `(Translated)`
- 🔹 **RAG + FAISS** — `ChunkingAgent` (250-word chunks, embedding `gemini-embedding-001` or OX `text-embedding`), per-task isolated `FAISS IndexFlatL2` for retrieval
- 🔹 **Single-chat switching** — grouped history by `source_id`, `chatCache` + `switchChatMode()` stays in `step-4`
- 🔹 **Translate toggle** — `TranslatorAgent` via LLM, `POST /translate/{task_id}` → English, toggle `↩ Show Original`
- 🔹 **Multi-provider LLM** — `LLMClient` with auto-fallback: **OpenRouter** (`liquid/lfm-2.5-2.6b:free`, `reasoning.enabled`) → Felo `ox-alpha` → Tokenra `ox-alpha-2` → Gemini `gemini-2.5-flash`
- 🔹 **Auth & retention** — JWT (`sha256_crypt`), 7-day TTL (user) / 1-hour (anon), `faiss` per-task ephemeral index

---

## ⚙️ How It Works

### 1. Ingest
Upload via `POST /ingest/document` (unified: pdf/txt/docx/pptx/image) or `POST /ingest/web` → `SourceManagerAgent` → `sources` collection with `language` detection.

### 2. Customize
UI `step-2` lets student pick **Mode** (FAQ/Flashcards/Quiz), **Language** (auto + 8 Indian), **Topic** (DomainAgent top-3), **Quantity**.

### 3. Generate (Background)
`POST /generate/learn?source_id=&mode=&num_items=&target_domain=&language=` → `task_manager.create_task(source_id)` → `BackgroundWorker._async_learn_task` (thread):
- Chunk → parallel `DomainAgent.generate_title` + `ChunkingAgent.embed`
- FAISS add + domain-aware semantic search
- Mode switch: `SuperAgent.generate_batch` / `FlashcardAgent.generate` / `QuizAgent.generate` (with `target_language`)

### 4. Poll & Render
`GET /results/{task_id}` polled every 2s; `renderResults` caches in `chatCache[source_id][mode]`; switcher `switchChatMode()` reuses cache or generates.

### 5. Translate (optional)
`POST /translate/{task_id}` → `TranslatorAgent.translate_task()` for non-English results.

---

## 🏗️ Project Structure

```
faq/
├── .env.example / .env
├── requirements.txt
├── app/
│   ├── config.py          # PROVIDER_*, LLM_PROVIDER auto (openrouter>felo>ox>gemini), SUPPORTED_LANGUAGES, STUDY_MODES, limits
│   ├── main.py            # FastAPI + security headers + static mount
│   ├── agents/
│   │   ├── source_manager.py   # ingest_document/file/image/web with TTL
│   │   ├── document_agent.py   # pdfplumber
│   │   ├── file_agent.py       # txt/docx/pptx
│   │   ├── image_agent.py      # Pillow + Vision OCR (OpenRouter/Gemini)
│   │   ├── web_agent.py        # requests + bs4
│   │   ├── chunking_agent.py   # Gemini/OX embeddings, parallel 50
│   │   ├── domain_agent.py     # embedding similarity categories
│   │   ├── language_agent.py   # heuristic + langdetect
│   │   ├── super_agent.py      # FAQ batch (clean_answer_text)
│   │   ├── flashcard_agent.py  # Flashcards (no hint)
│   │   ├── quiz_agent.py       # MCQs
│   │   ├── translator_agent.py # LLM translate to English
│   │   └── ... (answer/audit/validator legacy)
│   ├── api/routes.py       # /ingest/*, /generate/*, /translate/*, /results, /user/history
│   ├── auth/auth_handler.py
│   ├── database/mongodb.py # TTL + mode/language indexes
│   ├── llm/llm_client.py   # OpenRouter/Felo/OX/Gemini with auto-fallback & vision
│   ├── utils/background_worker.py # _async_learn_task, start_learn_task
│   ├── utils/task_manager.py      # source_id, mode, language
│   ├── utils/text_cleaner.py      # clean_text, clean_answer_text (chunk-ref strip)
│   └── vectorstore/faiss_store.py # IndexFlatL2
├── static/index.html       # Single-chat UI, mode switcher, translate toggle, mobile responsive
└── TASK.md                 # Upgrade tracker
```

---

## 📦 Installation

```bash
git clone https://github.com/DORAEMONBHAIYA/faq.git
cd faq
python -m venv venv
# Windows
venv\Scripts\activate
# Unix
source venv/bin/activate

pip install -r requirements.txt
# requires: fastapi uvicorn pymongo httpx openai python-docx python-pptx Pillow langdetect pdfplumber faiss-cpu ...
```

**Env setup** (`cp .env.example .env`):
```env
# OpenRouter (primary, free)
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=liquid/lfm-2.5-2.6b:free

# Felo / Tokenra fallback (optional)
FELO_API_KEY=fk-...
OX_API_KEY=sk-...

# Gemini (embeddings + fallback)
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash
GEMINI_EMBED_MODEL=gemini-embedding-001

MONGODB_URI=mongodb://localhost:27017
JWT_SECRET= # python -c "import secrets; print(secrets.token_hex(32))"
```

---

## ▶️ Usage

```bash
# dev
uvicorn app.main:app --reload --port 8000
# prod
python -m uvicorn app.main:app --port 8000 --host 0.0.0.0
```

Open `http://localhost:8000` → Upload → Customize → Generate → Switch modes in same chat → Translate toggle (shows for hi/ta/ml/gu etc.).

**API quick test:**
```bash
curl http://localhost:8000/health
# {"provider":"openrouter","model":"liquid/lfm-2.5-2.6b:free"}

curl -X POST http://localhost:8000/ingest/web -H "Content-Type: application/json" -d '{"url":"https://en.wikipedia.org/wiki/Photosynthesis"}'
curl -X POST "http://localhost:8000/generate/learn?source_id=src_xxx&mode=faq&num_items=5&target_domain=Science&language=hi"
curl http://localhost:8000/results/task_xxx
curl -X POST http://localhost:8000/translate/task_xxx -H "Content-Type: application/json" -d '{"target_language":"en"}'
```

Config tweaks: `app/config.py` (`CHUNK_SIZE=250`, `MAX_FILE_SIZE_DOC=5MB`, `MAX_FILE_SIZE_IMAGE=10MB`), or override via `GEMINI_MODEL`, `OPENROUTER_MODEL`.

---

## 🧪 Example

**Input:** 10k-token Tulsidas/Ramcharitmanas PDF in Hindi  
**Output:**
- FAQ: `Q: Why did Tulsidas use local language? A: To make Ramayana accessible to common people as a cultural decision...` (no `Chunk 3`)
- Flashcards: `Front: What is... / Back: ...` (tap to flip, no hints)
- Quiz: MCQ with `correct_index` + `explanation`, `Show Score`
- All toggleable `🌐 Translate to English ↔ Show Original`

---

## 📊 Research Value

- 📚 Academic: domain-filtered RAG vs raw generation
- 🤖 NLP: multilingual embeddings, chunk-reference stripping
- 🏢 Enterprise: source-grouped chat history, TTL

---

## 🔮 Future

- [ ] Mixed “Study Pack” (FAQ+cards+quiz in one)
- [ ] Progress tracking (`progress` collection)
- [ ] Dockerfile / docker-compose (app + mongo)
- [ ] Tests for agents / multilingual fixtures

---

## 🤝 Contributing

`fork → clone → branch → commit → PR`

---

## 👨‍💻 Author

Developed by **AKSHAT GUPTA** — Aquila Learn v4.0 (OpenRouter liquid + Gemini 2.5)
