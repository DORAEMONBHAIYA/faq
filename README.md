# 📄 FAQ Generator using Multi-Agent AI System

An intelligent **FAQ generation system** that automatically extracts meaningful, domain-relevant questions and answers from large documents using **multi-agent architecture, embeddings, and domain filtering techniques**.

---

## 🚀 Overview

This project is designed to solve the problem of extracting **useful and relevant FAQs** from large unstructured documents (e.g., PDFs, notes, research papers, transcripts).

Instead of blindly generating FAQs, the system:
- Identifies **domain-relevant content**
- Filters out low-value information
- Generates **high-quality, context-aware FAQs**

---

## 🧠 Key Features

- 🔹 Multi-Agent Architecture for modular processing  
- 🔹 Domain Relevance Filtering (prevents useless FAQ generation)  
- 🔹 Embedding-based semantic understanding  
- 🔹 Handles large documents (~10k+ tokens)  
- 🔹 Intelligent FAQ extraction (not just summarization)  
- 🔹 Scalable pipeline for research and production use  

---

## ⚙️ How It Works

### 1. Document Parsing
- Input document (PDF / text) is parsed into smaller chunks

### 2. Embedding Generation
- Each chunk is converted into vector embeddings

### 3. Domain Relevance Detection
- A scoring system evaluates whether the chunk belongs to the **target domain**
- Low-domain chunks are discarded

### 4. Multi-Agent Processing
Different agents handle different responsibilities:
- **Extractor Agent** → Finds potential FAQ-worthy content  
- **Validator Agent** → Checks relevance and clarity  
- **Generator Agent** → Converts content into Q&A format  

### 5. FAQ Generation
- High-quality FAQs are generated only from validated domain-specific content

---

## 🏗️ Project Structure

```
faq/
├── .gitignore
├── README.md
├── requirements.txt
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   │
│   ├── agents/
│   │   ├── answer_agent.py
│   │   ├── audit_agent.py
│   │   ├── chunking_agent.py
│   │   ├── document_agent.py
│   │   ├── domain_agent.py
│   │   ├── generator_agent.py
│   │   ├── question_agent.py
│   │   ├── refinement_agent.py
│   │   ├── refiner_agent.py
│   │   ├── source_manager.py
│   │   ├── super_agent.py
│   │   ├── validation_agent.py
│   │   ├── validator_agent.py
│   │   └── web_agent.py
│   │
│   ├── api/
│   │   └── routes.py
│   │
│   ├── auth/
│   │   └── auth_handler.py
│   │
│   ├── database/
│   │   └── mongodb.py
│   │
│   ├── llm/
│   │   └── llm_client.py
│   │
│   ├── utils/
│   │   ├── background_worker.py
│   │   ├── task_manager.py
│   │   └── text_cleaner.py
│   │
│   └── vectorstore/
│       └── faiss_store.py
│
├── static/
│   └── index.html
│
└── scratch/
    └── test_gemini.py
```

---

## 📦 Installation

```bash
git clone https://github.com/DORAEMONBHAIYA/faq.git
cd faq

pip install -r requirements.txt
```

---

## ▶️ Usage

```bash
python -m uvicorn app.main:app --port 8000
```

Optional configuration:
- Set domain threshold
- Adjust chunk size
- Choose embedding model

---

## 🧪 Example Use Case

Input:
> A 10,000-token technical document

Output:
- Clean, structured FAQs
- Only domain-relevant Q&A pairs
- No noise or irrelevant questions

---

## 📊 Research Value

This project is useful for:
- 📚 Academic research papers  
- 🤖 NLP experimentation  
- 🧾 Documentation automation  
- 🏢 Enterprise knowledge systems  

It also allows comparison between:
- Embedding-only vs Hybrid systems  
- Domain-filtered vs raw FAQ generation  
- Multi-agent vs single-model pipelines  

---

## 🔮 Future Improvements

- Add RAG (Retrieval-Augmented Generation)
- Fine-tuned domain classifiers
- UI for document upload & FAQ visualization
- Real-time FAQ generation API

---

## 🤝 Contributing

Contributions are welcome!

```bash
fork → clone → create branch → commit → PR
```

---

## 👨‍💻 Author

Developed by **AKSHAT GUPTA**
