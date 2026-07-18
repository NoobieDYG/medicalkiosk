import os

import dotenv
import httpx


dotenv.load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 512


def get_embedding(text: str) -> list:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

    if not endpoint or not api_key :
        raise RuntimeError(
            "Azure OpenAI environment variables are not configured. Set AZURE_OPENAI_ENDPOINT, "
            "AZURE_OPENAI_API_KEY, and AZURE_OPENAI_EMBEDDING_DEPLOYMENT."
        )

    url = f"{endpoint}/openai/deployments/{EMBEDDING_MODEL}/embeddings?api-version={api_version}"
    response = httpx.post(
        url,
        headers={"api-key": api_key, "Content-Type": "application/json"},
        json={"input": text, "dimensions": EMBEDDING_DIMENSIONS},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]