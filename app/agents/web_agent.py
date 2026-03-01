import uuid
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

MAX_WORDS = 2500   # 🔥 HARD LIMIT (speed control)

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

        paragraphs = [
            p.get_text(" ", strip=True)
            for p in soup.find_all("p")
            if len(p.get_text(strip=True).split()) > 20
        ]

        words_collected = []
        for p in paragraphs:
            words_collected.extend(p.split())
            if len(words_collected) >= MAX_WORDS:
                break

        clean_text = " ".join(words_collected[:MAX_WORDS])

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
