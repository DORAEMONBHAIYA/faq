import os
import uuid
import pdfplumber

UPLOAD_DIR = "data/uploads"

class DocumentAgent:
    def ingest(self, file_path: str) -> dict:
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        text_blocks = []

        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    text_blocks.append({
                        "source_id": doc_id,
                        "page": i + 1,
                        "text": text.strip()
                    })

        return {
            "source_id": doc_id,
            "type": "document",
            "content": text_blocks
        }
