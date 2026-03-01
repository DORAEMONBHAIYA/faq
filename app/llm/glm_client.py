import os
import requests
import time
import threading

GLM_API_KEY = os.getenv("GLM_API_KEY")
GLM_ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL_NAME = "glm-4.7-flash"

# 🔒 Global lock for rate limiting
GLM_LOCK = threading.Lock()

class GLMClient:
    def __init__(self):
        if not GLM_API_KEY:
            raise RuntimeError("GLM_API_KEY not set")

    def chat(self, messages, temperature=0.3, retries=3):
        headers = {
            "Authorization": f"Bearer {GLM_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": temperature
        }

        for attempt in range(retries + 1):
            try:
                with GLM_LOCK:  # 🔥 serialize requests
                    response = requests.post(
                        GLM_ENDPOINT,
                        headers=headers,
                        json=payload,
                        timeout=60
                    )

                if response.status_code == 429:
                    raise requests.exceptions.HTTPError("429")

                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]

            except requests.exceptions.HTTPError as e:
                if "429" in str(e) and attempt < retries:
                    # ⏳ Exponential backoff
                    time.sleep(2 ** attempt)
                    continue
                raise
