import logging
import asyncio
from threading import Thread

from app.utils.task_manager import task_manager
from app.agents.chunking_agent import ChunkingAgent
from app.agents.domain_agent import DomainAgent
from app.agents.super_agent import SuperAgent
from app.agents.refiner_agent import RefinerAgent
from app.vectorstore.faiss_store import FAISSStore # Import class, not global instance
from app.config import CHUNK_SIZE

logger = logging.getLogger("BackgroundWorker")

chunker = ChunkingAgent()
domain_agent = DomainAgent()
super_agent = SuperAgent()
refine_agent = RefinerAgent()

async def _async_faq_task(task_id: str, source_data: dict, num_faqs: int, target_domain: str = "auto"):
    try:
        # 🛡️ ISOLATION: Create a fresh, private vector store for THIS specific task
        # This prevents data leakage from previous runs or other users.
        private_store = FAISSStore()
        
        task_manager.update(task_id, "processing", trace_entry={"agent": "Orchestrator", "action": "Analyzing Document Structure"})

        # 1. RAG PREP
        chunks = chunker.chunk(source_data, chunk_size=CHUNK_SIZE)
        if not chunks:
            raise ValueError("No content found in source. Please check the URL or File.")
            
        # 🧪 NEW: Generate Catchy AI Title
        task_manager.update(task_id, "processing", trace_entry={"agent": "DomainAgent", "action": "Naming your session"})
        ai_title = await domain_agent.generate_title(chunks[0]["text"])
        task_manager.update(task_id, "processing", domain={"source_name": ai_title})
        # Note: We update the source_name in the DB record
        task_manager.collection.update_one({"task_id": task_id}, {"$set": {"source_name": ai_title}})

        embeddings = await chunker.embed(chunks)
        private_store.add(embeddings, chunks)
        
        # 2. DOMAIN-AWARE RETRIEVAL (Semantic Search in private store)
        task_manager.update(task_id, "processing", trace_entry={"agent": "RetrievalAgent", "action": f"Searching for {target_domain} content"})
        
        domain_query_embedding = (await chunker.embed([target_domain]))[0]
        selected_chunks = private_store.search(domain_query_embedding, top_k=min(num_faqs + 2, len(chunks)))

        # 3. BATCH GENERATION (Strictly guided by domain)
        task_manager.update(task_id, "processing", trace_entry={"agent": "SuperAgent", "action": f"Generating {target_domain} FAQ batch"})
        batch_data = await super_agent.generate_batch(selected_chunks, num_faqs, target_domain)
        
        if not batch_data or "faqs" not in batch_data:
            raise RuntimeError("Batch generation failed. The AI couldn't find relevant information for this domain.")

        # 4. ADAPTIVE REFINEMENT
        final_faqs = []
        for faq in batch_data["faqs"]:
            faq["iterations"] = 1
            faq["status"] = "verified"
            
            if faq.get("scores", {}).get("clarity", 1.0) < 0.7:
                task_manager.update(task_id, "processing", trace_entry={"agent": "RefinerAgent", "action": "Polishing output"})
                context = selected_chunks[0]["text"]
                new_q, new_a = await refine_agent.refine(faq["question"], faq["answer"], context, f"Improve clarity for {target_domain} domain.")
                faq["question"], faq["answer"] = new_q, new_a
                faq["iterations"] = 2
            
            final_faqs.append(faq)

        # 5. FINALIZATION
        task_manager.update(task_id, "completed", result=final_faqs, trace_entry={"agent": "Orchestrator", "action": "Workflow Completed"})

    except Exception as e:
        import traceback
        error_type = type(e).__name__
        error_msg = str(e) or "Unknown error"
        full_error = f"{error_type}: {error_msg}"
        logger.error(f"Task {task_id} failed: {full_error}")
        logger.error(traceback.format_exc())
        task_manager.update(task_id, "failed", trace_entry={"agent": "Orchestrator", "action": f"ERROR: {full_error}"})

def run_faq_task(task_id: str, source_data: dict, num_faqs: int, target_domain: str = "auto"):
    asyncio.run(_async_faq_task(task_id, source_data, num_faqs, target_domain))

def start_task(task_id: str, source_data: dict, num_faqs: int, target_domain: str = "auto"):
    thread = Thread(target=run_faq_task, args=(task_id, source_data, num_faqs, target_domain))
    thread.daemon = True
    thread.start()
