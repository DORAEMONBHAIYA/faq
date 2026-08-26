import logging
import asyncio
from threading import Thread

from app.utils.task_manager import task_manager
from app.agents.chunking_agent import ChunkingAgent
from app.agents.domain_agent import DomainAgent
from app.agents.super_agent import SuperAgent
from app.agents.refiner_agent import RefinerAgent
from app.agents.flashcard_agent import FlashcardAgent
from app.agents.quiz_agent import QuizAgent
from app.vectorstore.faiss_store import FAISSStore
from app.config import CHUNK_SIZE, STUDY_MODES, SUPPORTED_LANGUAGES

logger = logging.getLogger("BackgroundWorker")

chunker = ChunkingAgent()
domain_agent = DomainAgent()
super_agent = SuperAgent()
flashcard_agent = FlashcardAgent()
quiz_agent = QuizAgent()
refine_agent = RefinerAgent()

async def _async_learn_task(task_id: str, source_data: dict, num_items: int, target_domain: str = "auto", target_language: str = "auto", mode: str = "faq"):
    mode = mode if mode in STUDY_MODES else "faq"
    target_language = target_language if target_language in SUPPORTED_LANGUAGES else "auto"
    try:
        private_store = FAISSStore()
        task_manager.update(task_id, "processing", trace_entry={"agent": "Orchestrator", "action": f"Starting {mode} generation ({target_language})"})

        chunks = chunker.chunk(source_data, chunk_size=CHUNK_SIZE)
        if not chunks:
            raise ValueError("No content found in source. Please check the URL or File.")
        task_manager.update(task_id, "processing", trace_entry={"agent": "Orchestrator", "action": "Analyzing Content & Indexing"})

        title_task = domain_agent.generate_title(chunks[0]["text"])
        embed_task = chunker.embed(chunks)
        ai_title, embeddings = await asyncio.gather(title_task, embed_task)

        task_manager.update(task_id, "processing", domain={"source_name": ai_title})
        task_manager.collection.update_one({"task_id": task_id}, {"$set": {"source_name": ai_title, "mode": mode, "language": target_language}})
        private_store.add(embeddings, chunks)

        task_manager.update(task_id, "processing", trace_entry={"agent": "RetrievalAgent", "action": f"Searching for {target_domain} content"})
        domain_query_embedding = (await chunker.embed([target_domain]))[0]
        selected_chunks = private_store.search(domain_query_embedding, top_k=min(num_items + 2, len(chunks)))

        if mode == "flashcards":
            task_manager.update(task_id, "processing", trace_entry={"agent": "FlashcardAgent", "action": f"Generating {num_items} flashcards in {target_language}"})
            batch_data = await flashcard_agent.generate(selected_chunks, num_items, target_language, target_domain)
            if not batch_data or "flashcards" not in batch_data:
                raise RuntimeError("Flashcard generation failed.")
            result = batch_data["flashcards"]
        elif mode == "quiz":
            task_manager.update(task_id, "processing", trace_entry={"agent": "QuizAgent", "action": f"Generating {num_items} quiz questions in {target_language}"})
            batch_data = await quiz_agent.generate(selected_chunks, num_items, target_language, target_domain)
            if not batch_data or "quiz" not in batch_data:
                raise RuntimeError("Quiz generation failed.")
            result = batch_data["quiz"]
        else:
            task_manager.update(task_id, "processing", trace_entry={"agent": "SuperAgent", "action": f"Generating {target_domain} FAQ batch in {target_language}"})
            batch_data = await super_agent.generate_batch(selected_chunks, num_items, target_domain, target_language)
            if not batch_data or "faqs" not in batch_data:
                raise RuntimeError("Batch generation failed. The AI couldn't find relevant information for this domain.")
            result = batch_data["faqs"]

        task_manager.update(task_id, "completed", result=result, trace_entry={"agent": "Orchestrator", "action": f"{mode.upper()} Workflow Completed"})

    except Exception as e:
        import traceback
        error_type = type(e).__name__
        error_msg = str(e) or "Unknown error"
        full_error = f"{error_type}: {error_msg}"
        logger.error(f"Task {task_id} failed: {full_error}")
        logger.error(traceback.format_exc())
        task_manager.update(task_id, "failed", trace_entry={"agent": "Orchestrator", "action": f"ERROR: {full_error}"})

async def _async_faq_task(task_id: str, source_data: dict, num_faqs: int, target_domain: str = "auto"):

    await _async_learn_task(task_id, source_data, num_faqs, target_domain, "auto", "faq")
    try:

        private_store = FAISSStore()

        task_manager.update(task_id, "processing", trace_entry={"agent": "Orchestrator", "action": "Analyzing Document Structure"})

        chunks = chunker.chunk(source_data, chunk_size=CHUNK_SIZE)
        if not chunks:
            raise ValueError("No content found in source. Please check the URL or File.")

        task_manager.update(task_id, "processing", trace_entry={"agent": "Orchestrator", "action": "Analyzing Content & Indexing"})

        title_task = domain_agent.generate_title(chunks[0]["text"])
        embed_task = chunker.embed(chunks)

        ai_title, embeddings = await asyncio.gather(title_task, embed_task)

        task_manager.update(task_id, "processing", domain={"source_name": ai_title})
        task_manager.collection.update_one({"task_id": task_id}, {"$set": {"source_name": ai_title}})

        private_store.add(embeddings, chunks)

        task_manager.update(task_id, "processing", trace_entry={"agent": "RetrievalAgent", "action": f"Searching for {target_domain} content"})

        domain_query_embedding = (await chunker.embed([target_domain]))[0]
        selected_chunks = private_store.search(domain_query_embedding, top_k=min(num_faqs + 2, len(chunks)))

        task_manager.update(task_id, "processing", trace_entry={"agent": "SuperAgent", "action": f"Generating {target_domain} FAQ batch"})
        batch_data = await super_agent.generate_batch(selected_chunks, num_faqs, target_domain)

        if not batch_data or "faqs" not in batch_data:
            raise RuntimeError("Batch generation failed. The AI couldn't find relevant information for this domain.")

        task_manager.update(task_id, "completed", result=batch_data["faqs"], trace_entry={"agent": "Orchestrator", "action": "Workflow Completed"})

    except Exception as e:
        import traceback
        error_type = type(e).__name__
        error_msg = str(e) or "Unknown error"
        full_error = f"{error_type}: {error_msg}"
        logger.error(f"Task {task_id} failed: {full_error}")
        logger.error(traceback.format_exc())
        task_manager.update(task_id, "failed", trace_entry={"agent": "Orchestrator", "action": f"ERROR: {full_error}"})

def run_learn_task(task_id: str, source_data: dict, num_items: int, target_domain: str = "auto", target_language: str = "auto", mode: str = "faq"):
    asyncio.run(_async_learn_task(task_id, source_data, num_items, target_domain, target_language, mode))

def run_faq_task(task_id: str, source_data: dict, num_faqs: int, target_domain: str = "auto"):
    asyncio.run(_async_faq_task(task_id, source_data, num_faqs, target_domain))

def start_learn_task(task_id: str, source_data: dict, num_items: int, target_domain: str = "auto", target_language: str = "auto", mode: str = "faq"):
    thread = Thread(target=run_learn_task, args=(task_id, source_data, num_items, target_domain, target_language, mode))
    thread.daemon = True
    thread.start()

def start_task(task_id: str, source_data: dict, num_faqs: int, target_domain: str = "auto", target_language: str = "auto", mode: str = "faq"):

    thread = Thread(target=run_learn_task, args=(task_id, source_data, num_faqs, target_domain, target_language, mode))
    thread.daemon = True
    thread.start()
