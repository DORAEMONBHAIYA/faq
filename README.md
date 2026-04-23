# 🦅 AquilaFAQ | Intelligence System

AquilaFAQ is a state-of-the-art, **Multi-Agent AI FAQ Engine** designed to transform complex documents and websites into structured, expert-verified knowledge bases. Built for performance and precision, it utilizes Google's Gemini Pro models to orchestrate a sophisticated RAG (Retrieval-Augmented Generation) pipeline.

![AquilaFAQ Dashboard](https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&q=80&w=1600)

## 🚀 Key Features

- **Multi-Source Ingestion**: Seamlessly ingest content from PDFs and live Web URLs.
- **Dynamic Perspective Detection**: Automatically identifies the "domain" of the content (e.g., Medical, Technical, Business) to tailor the FAQ style.
- **Expert Multi-Agent Pipeline**: A fleet of specialized agents works in parallel to synthesize, validate, and refine every FAQ.
- **Vector Intelligence**: Uses FAISS for high-speed semantic search across massive document sets.
- **Premium UI**: A sleek, mobile-responsive dashboard with glassmorphism aesthetics and smooth transitions.
- **Persistent History**: Integrated MongoDB Atlas storage for keeping your generations accessible across devices.

## 🧠 Multi-Agent Architecture

AquilaFAQ operates like an AI newsroom, where specialized agents collaborate to ensure accuracy:

1.  **Source Agent**: Ingests and cleanses data from Web/PDF.
2.  **Domain Agent**: Analyzes the "vibe" and topic of the source to set the right tone.
3.  **Chunking Agent**: Uses Gemini Embeddings to create a high-dimensional vector map of the text.
4.  **Super Agent**: The "Lead Author" that synthesizes raw information into high-quality FAQs.
5.  **Refinement Agent**: The "Editor-in-Chief" that checks for flow, accuracy, and formatting.

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: MongoDB Atlas (Persistent Storage) & FAISS (Vector Store)
- **AI Engine**: Google Gemini Pro (LLM & Embeddings)
- **Frontend**: Vanilla JS & CSS (Glassmorphism Design System)
- **Authentication**: JWT (JSON Web Tokens) with secure password hashing.

## ⚙️ Setup & Installation

### 1. Prerequisites
- Python 3.9+
- MongoDB Atlas Account (or local MongoDB)
- Google Gemini API Key

### 2. Environment Configuration
Create a `.env` file in the root directory:
```env
MONGODB_URI=mongodb+srv://your_connection_string
GEMINI_API_KEY=your_gemini_key
JWT_SECRET=your_secret_key_for_auth
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Locally
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📈 Deployment
This project is optimized for **Render** and **Vercel**. 
- The system is built to fit within a **512MB RAM** footprint by offloading heavy ML models to the Gemini Cloud API.
- Ensure all environment variables are set in your production dashboard.

---
*Built with ❤️ by the Aquila Team.*
