from typing import List, Tuple
from embeddings import get_query_embedding
import vector_store as vs

# ──────────────────────────────────────────────
# Prompt Templates
# ──────────────────────────────────────────────

SUMMARIZE_PROMPT = """You are a research assistant. Based ONLY on the context below, write a clear and structured summary of the research paper. 
Include: main objective, methodology, key findings, and conclusions.
Do NOT add any information not present in the context.

Context:
{context}

Structured Summary:"""


EXPLAIN_PROMPT = """You are a helpful teacher. Using ONLY the context below, explain the concept or section in simple, easy-to-understand language.
Avoid jargon where possible, and use analogies if helpful.
Do NOT add any information not present in the context.

Context:
{context}

Question / Topic: {query}

Simple Explanation:"""


QA_PROMPT = """You are a research assistant. Answer the user's question using ONLY the context provided below.
If the answer cannot be found in the context, respond with exactly: "Not found in document."
Do NOT use any prior knowledge or make assumptions beyond the provided context.

Context:
{context}

Question: {query}

Answer:"""


# ──────────────────────────────────────────────
# Core RAG Functions
# ──────────────────────────────────────────────

def retrieve_context(doc_id: str, query: str, top_k: int = 5) -> List[dict]:
    """Embed the query and retrieve top-k relevant chunks from FAISS."""
    query_emb = get_query_embedding(query)
    results = vs.search(doc_id, query_emb, top_k=top_k)
    return results


def format_context(chunks: List[dict]) -> str:
    """Concatenate chunk texts into a single context string."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        page_info = f" (Page {chunk['page']})" if chunk.get("page") else ""
        parts.append(f"[Chunk {i}{page_info}]\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


def build_prompt(intent: str, context_chunks: List[dict], query: str) -> str:
    """Construct the LLM prompt based on detected intent."""
    context = format_context(context_chunks)

    if intent == "summarize":
        return SUMMARIZE_PROMPT.format(context=context)
    elif intent == "explain":
        return EXPLAIN_PROMPT.format(context=context, query=query)
    else:  # qa
        return QA_PROMPT.format(context=context, query=query)
