class ValidationAgent:
    """
    Lightweight confidence estimator based on
    lexical overlap between answer and context.
    Extremely fast and free-tier friendly.
    """

    def confidence(self, question, answer, contexts):
        if not contexts or not answer:
            return 0.0

        answer_words = set(answer.lower().split())
        context_words = set()

        for c in contexts:
            context_words.update(c["text"].lower().split())

        overlap = answer_words & context_words

        # Normalize confidence score
        score = len(overlap) / max(50, len(answer_words))
        return round(min(score, 1.0), 2)
