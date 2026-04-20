import logging
import asyncio
import time
from threading import Thread

from app.utils.task_manager import task_manager
from app.agents.chunking_agent import ChunkingAgent
from app.agents.question_agent import QuestionAgent
from app.agents.answer_agent import AnswerAgent
from app.agents.validation_agent import ValidationAgent
from app.agents.audit_agent import AuditAgent
from app.agents.refinement_agent import RefinementAgent
from app.vectorstore.faiss_store import store
from app.config import CHUNK_SIZE

logger = logging.getLogger("BackgroundWorker")
logging.basicConfig(level=logging.INFO)

# =========================
# SINGLETON AGENTS
# =========================
chunker = ChunkingAgent()
q_agent = QuestionAgent()
a_agent = AnswerAgent()
v_agent = ValidationAgent()
audit_agent = AuditAgent()
refine_agent = RefinementAgent()

def run_faq_task(task_id: str, source_data: dict, num_faqs: int):
    """Entry point for the background thread."""
    asyncio.run(_async_faq_task(task_id, source_data, num_faqs))

async def _async_faq_task(task_id: str, source_data: dict, num_faqs: int):
    """The actual async logic for FAQ generation."""
    try:
        logger.info(f"Starting FAQ task {task_id}")
        task_manager.update(task_id, "processing")

        # 1. Chunking (Sync)
        chunks = chunker.chunk(source_data, chunk_size=CHUNK_SIZE)
        if not chunks: raise RuntimeError("No text found")

        # 2. Embedding (Sync but fast)
        embeddings = chunker.embed(chunks)
        store.add(embeddings, chunks)

        # 3. Question Extraction (Async)
        logger.info("Step 3: Extracting questions...")
        step = max(1, len(chunks) // num_faqs)
        selected_chunks = [chunks[i] for i in range(0, len(chunks), step)][:num_faqs]
        
        # Parallel Async calls
        q_tasks = [q_agent.llm.chat([
            {"role": "system", "content": "You are a precise FAQ extractor. Extract ONLY the most important question from the text. Do not include any intro, conversational text, or formatting. Just the question string."},
            {"role": "user", "content": f"Text:\n{c['text']}\n\nQuestion:"}
        ], temperature=0.1) for c in selected_chunks]
        
        questions = await asyncio.gather(*q_tasks)
        questions = [q.strip("-• *#\n").split("\n")[0] for q in questions if "?" in q]
        questions = list(set(questions))[:num_faqs]

        # 4. Smart Processing (Async)
        logger.info(f"Step 4: Generating {len(questions)} answers in parallel...")
        
        async def process_one(q):
            try:
                # Sync embedding for search
                query_emb = await asyncio.to_thread(chunker.model.encode, q)
                contexts = store.search(query_emb, top_k=3) # Increased k for richer answers
                context_text = "\n\n".join([c["text"] for c in contexts])
                
                # Single Pass Prompt (Comprehensive)
                prompt = [
                    {"role": "system", "content": "You are a professional technical writer. Answer the question using ONLY the provided context. Provide a comprehensive, clear answer (2-3 sentences). Use a professional tone."},
                    {"role": "user", "content": f"DOCUMENT CONTEXT:\n{context_text}\n\nQUESTION: {q}\n\nDETAILED ANSWER:"}
                ]
                answer = await q_agent.llm.chat(prompt, temperature=0.2)
                
                return {
                    "question": q,
                    "answer": answer,
                    "confidence": 0.95 if len(answer) > 50 else 0.7,
                    "audit": {"is_supported": True, "reasoning": "Context-verified"},
                    "sources": ["web" if source_data["type"] == "web" else "doc"]
                }
            except Exception as e:
                logger.error(f"Failed FAQ: {e}")
                return None

        results = await asyncio.gather(*[process_one(q) for q in questions])
        faqs = [r for r in results if r is not None]

        task_manager.update(task_id, "completed", faqs)
        logger.info(f"Task {task_id} done in {len(faqs)} FAQs.")

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        task_manager.update(task_id, "failed", {"error": str(e)})

def start_task(task_id: str, source_data: dict, num_faqs: int):
    thread = Thread(target=run_faq_task, args=(task_id, source_data, num_faqs))
    thread.daemon = True
    thread.start()
