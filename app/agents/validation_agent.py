class ValidationAgent:
    """
    Hybrid confidence estimator combining lexical overlap
    and LLM-based audit results.
    """

    def confidence(self, question, answer, contexts, audit_result=None):
        if not contexts or not answer:
            return 0.0

        # 1. Lexical Overlap (Fast)
        answer_words = set(answer.lower().split())
        context_words = set()
        for c in contexts:
            context_words.update(c["text"].lower().split())

        overlap = answer_words & context_words
        lexical_score = len(overlap) / max(50, len(answer_words))
        lexical_score = min(lexical_score, 1.0)

        # 2. Audit Integration (Precise)
        if audit_result:
            audit_score = audit_result.get("confidence_score", 0.0)
            # Weighted average: 30% lexical, 70% audit
            final_score = (0.3 * lexical_score) + (0.7 * audit_score)
        else:
            final_score = lexical_score

        return round(min(final_score, 1.0), 2)
