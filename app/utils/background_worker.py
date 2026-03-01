from threading import Thread
from concurrent.futures import ThreadPoolExecutor

from app.utils.task_manager import task_manager
from app.agents.chunking_agent import ChunkingAgent
from app.agents.question_agent import QuestionAgent
from app.agents.answer_agent import AnswerAgent
from app.agents.validation_agent import ValidationAgent
from app.vectorstore.faiss_store import FAISSStore

# =========================
# SINGLETON AGENTS
# =========================
chunker = ChunkingAgent()
q_agent = QuestionAgent()
a_agent = AnswerAgent()
v_agent = ValidationAgent()
store = FAISSStore()

# =========================
# SIMPLE IN-MEMORY CACHE
# =========================
ANSWER_CACHE = {}

# =========================
# INTERNAL HELPERS
# =========================
def _batched_answer(questions):
    """
    Try to answer all questions in one LLM call.
    Raises exception if LLM times out or fails.
    """
    batch_prompt = "\n".join(
        [f"Q{i+1}: {q}" for i, q in enumerate(questions)]
    )

    return a_agent.answer(
        "Answer all questions clearly and separately. "
        "Prefix answers with A1:, A2:, etc.",
        [{"text": batch_prompt}]
    )

def _split_and_answer(questions):
    """
    Fallback: split questions into two smaller batches
    """
    mid = len(questions) // 2
    answers = []

    for sub in [questions[:mid], questions[mid:]]:
        if not sub:
            continue
        text = _batched_answer(sub)
        answers.extend(
            [a.strip() for a in text.split("\n") if a.strip()]
        )

    return answers

# =========================
# MAIN BACKGROUND TASK
# =========================
def run_faq_task(task_id, source_data, num_faqs):
    try:
        task_manager.update(task_id, "processing")

        # -------- 1. Chunking --------
        chunks = chunker.chunk(source_data)

        # Speed cap for web sources
        if source_data["type"] == "web":
            chunks = chunks[:8]

        if not chunks:
            raise RuntimeError("No usable text chunks found")

        # -------- 2. Embeddings + Index --------
        embeddings = chunker.embed(chunks)
        store.add(embeddings, chunks)

        # -------- 3. Question Generation --------
        seed_text = " ".join(c["text"] for c in chunks[:2])
        questions = q_agent.generate(seed_text, num_faqs)

        if not questions:
            raise RuntimeError("Question generation failed")

        # -------- 4. Parallel Retrieval --------
        with ThreadPoolExecutor(max_workers=3) as executor:
            contexts = list(executor.map(
                lambda q: store.search(chunker.model.encode(q)),
                questions
            ))

        # -------- 5. Batched Answer Generation --------
        uncached_questions = []
        index_map = {}

        for i, q in enumerate(questions):
            if q not in ANSWER_CACHE:
                index_map[len(uncached_questions)] = i
                uncached_questions.append(q)

        answers = []

        if uncached_questions:
            try:
                # First attempt: full batch
                answers_text = _batched_answer(uncached_questions)
                answers = [
                    a.strip() for a in answers_text.split("\n") if a.strip()
                ]
            except Exception:
                # 🔥 Final fallback: answer first 2 questions only
                limited = uncached_questions[:2]
                answers_text = _batched_answer(limited)
                answers = [a.strip() for a in answers_text.split("\n") if a.strip()]

            # Store in cache
            for i, ans in enumerate(answers):
                q_index = index_map.get(i)
                if q_index is not None:
                    ANSWER_CACHE[questions[q_index]] = ans

        # -------- 6. Build Final Output --------
        faqs = []

        for i, q in enumerate(questions):
            answer = ANSWER_CACHE.get(q, "Answer not available")
            confidence = v_agent.confidence(q, answer, contexts[i])

            faqs.append({
                "question": q,
                "answer": answer,
                "confidence": confidence,
                "sources": list(set(c["source_id"] for c in contexts[i]))
            })

        task_manager.update(task_id, "completed", faqs)

    except Exception as e:
        task_manager.update(task_id, "failed", {"error": str(e)})

# =========================
# TASK STARTER
# =========================
def start_task(task_id, source_data, num_faqs):
    Thread(
        target=run_faq_task,
        args=(task_id, source_data, num_faqs),
        daemon=True
    ).start()
