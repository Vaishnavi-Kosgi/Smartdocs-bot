import os
import time
import google.generativeai as genai
from dotenv import load_dotenv
from typing import List

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

EMBEDDING_MODEL = "models/gemini-embedding-001"


def get_embedding(text: str) -> List[float]:
    """Generate a single embedding vector for the given text."""
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document"
    )
    return result["embedding"]


def get_query_embedding(text: str) -> List[float]:
    """Generate an embedding vector optimised for query retrieval."""
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_query"
    )
    return result["embedding"]


def batch_embed(chunks: List[dict], batch_size: int = 100) -> List[List[float]]:
    """
    Embed a list of chunk dicts in batches.
    Handles rate limiting with exponential backoff.
    Returns list of embedding vectors in same order as chunks.
    """
    embeddings = []
    texts = [c["text"] for c in chunks]

    for i in range(0, len(texts), batch_size):
        batch = texts[i: i + batch_size]
        
        retries = 0
        while retries < 4:
            try:
                result = genai.embed_content(
                    model=EMBEDDING_MODEL,
                    content=batch,
                    task_type="retrieval_document"
                )
                embeddings.extend(result["embedding"])
                break
            except Exception as e:
                wait = 2 ** retries
                print(f"[Embeddings] Error: {e}. Retrying in {wait}s…")
                time.sleep(wait)
                retries += 1
        else:
            embeddings.extend([[0.0] * 768] * len(batch))

        # Gentle rate-limit pause between batches
        if i + batch_size < len(texts):
            time.sleep(2)

    return embeddings
