import httpx
import dotenv

dotenv.load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 512


def get_embedding(text: str) -> list:
    response = httpx.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {dotenv.dotenv_values().get('OPENAI_API_KEY')}"},
        json={"model": EMBEDDING_MODEL, "input": text, "dimensions": EMBEDDING_DIMENSIONS},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]