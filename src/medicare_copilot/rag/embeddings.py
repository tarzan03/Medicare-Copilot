import time

import cohere

from medicare_copilot.utils.settings import settings

MODEL_NAME = "embed-v4.0"
EMBEDDING_DIMENSION = 1024

client = cohere.ClientV2(api_key=settings.COHERE_API_KEY)

# Retry configuration for Cohere rate-limit (429) responses.
_MAX_RETRIES = 3
_RETRY_WAIT_SECONDS = 62  # 100 K tokens/min window resets after 60 s


def _embed(texts: list[str], input_type: str) -> list[list[float]]:
    """Low-level embed call with automatic retry on 429 rate-limit errors."""
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = client.embed(
                texts=texts,
                model=MODEL_NAME,
                input_type=input_type,
                embedding_types=["float"],
                output_dimension=EMBEDDING_DIMENSION,
            )
            return [list(vector) for vector in response.embeddings.float]
        except Exception as exc:
            if getattr(exc, "status_code", None) == 429 and attempt < _MAX_RETRIES:
                wait = _RETRY_WAIT_SECONDS * (attempt + 1)
                print(
                    f"Cohere rate limit hit (attempt {attempt + 1}/{_MAX_RETRIES}), "
                    f"waiting {wait}s before retry…",
                    flush=True,
                )
                time.sleep(wait)
                continue
            raise
    # Unreachable, but keeps type-checkers happy.
    raise RuntimeError("_embed: exhausted all retries")


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for document chunks."""
    if not texts:
        return []
    return _embed(texts, input_type="search_document")


def embed_query(query: str) -> list[float]:
    """Generate an embedding for a search query."""
    return _embed([query], input_type="search_query")[0]
