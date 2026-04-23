import uuid
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from app.config import MAX_WEB_WORDS

class WebAgent:
    def ingest(self, url: str) -> dict:
        web_id = f"web_{uuid.uuid4().hex[:8]}"

        response = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "AquilaFAQBot/1.0"}
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove junk tags
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Capture all text from standard content tags
        text_blocks = []
        for tag in soup.find_all(['p', 'div', 'span', 'article', 'section']):
            # Filter out very short UI fragments but keep meaningful text
            t = tag.get_text(" ", strip=True)
            if len(t.split()) > 4:
                text_blocks.append(t)
        
        # Deduplicate and join
        clean_text = " ".join(dict.fromkeys(text_blocks)) # Preserve order, remove duplicates
        clean_text = " ".join(clean_text.split()[:MAX_WEB_WORDS])

        return {
            "source_id": web_id,
            "type": "web",
            "url": url,
            "domain": urlparse(url).netloc,
            "content": [{
                "source_id": web_id,
                "text": clean_text
            }]
        }
