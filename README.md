# AI-Powered FAQ Generator (Multi-Agent System)

An automated intelligence system that transforms static documents into structured FAQ resources using a multi-agent orchestration. This tool is designed to reduce the workload for support teams and content creators by extracting key information and formatting it for immediate use.

## 🚀 Features

- **Multi-Agent Orchestration**: Utilizes specialized agents to parse documents, generate contextually relevant questions, and verify answer accuracy.
- **Support for Multiple Formats**: Effortlessly process PDF and DOCX files.
- **Smart Caching**: Integrated MongoDB caching to store results, minimizing LLM API costs and improving response times for similar documents.
- **Professional Export**: Download your generated FAQs as cleanly formatted PDF or DOCX files.
- **Dockerized Setup**: Ready for deployment with a containerized environment.

## 🛠️ Tech Stack

- **Language**: Python 3.x
- **LLM Provider**: DeepSeek (via API)
- **Database**: MongoDB (for caching and storage)
- **Document Processing**: PyPDF2, python-docx
- **Containerization**: Docker

## 📦 Installation & Setup

### Prerequisites
- Docker & Docker Compose
- DeepSeek API Key
- MongoDB Instance (Local or Atlas)

### Local Development

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/DORAEMONBHAIYA/faq.git](https://github.com/DORAEMONBHAIYA/faq.git)
   cd faq
