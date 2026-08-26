import re

def clean_text(text: str) -> str:
    """Normalize whitespace, remove control chars, fix OCR artifacts."""
    if not text:
        return ""

    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    text = text.replace("\xa0", " ")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    text = re.sub(r"([a-z])-\n([a-z])", r"\1\2", text)
    return text.strip()

def clean_blocks(blocks: list) -> list:
    """Clean list of {text, ...} blocks."""
    out = []
    for b in blocks:
        t = clean_text(b.get("text", ""))
        if len(t.split()) >= 3:
            b["text"] = t
            out.append(b)
    return out

def truncate_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])

def clean_answer_text(text: str) -> str:
    """Remove internal chunk references like 'As mentioned in Chunk 3' from LLM answers to make them student-friendly."""
    if not text:
        return ""
    original = text

    text = re.sub(r"\s*\(Translated\)\s*$", "", text, flags=re.IGNORECASE)

    text = re.sub(r"\bAs\s+(?:mentioned|described|stated|given|said|per|shown)?\s*in\s+Chunks?\s*[\d,\s,\u2013\-and&]+[.,]?","", text, flags=re.IGNORECASE)

    text = re.sub(r"\bin\s+Chunks?\s*[\d,\s,\u2013\-and&]+[.,]?","", text, flags=re.IGNORECASE)

    text = re.sub(r"\(?\bChunks?\s*\d+[\d,\s,\u2013\-and&]*\)?","", text, flags=re.IGNORECASE)

    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+,\s*,","", text)
    text = re.sub(r"^\s*[.,;:\-–]\s*","", text)
    text = text.strip()

    if len(text) < 10:
        return original.strip()

    text = re.sub(r"^\s*[,;]\s*","", text)

    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    text = re.sub(r"\.\s+([a-z])", lambda m: ". " + m.group(1).upper(), text)

    text = re.sub(r"detail\s+This", "detail. This", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()
