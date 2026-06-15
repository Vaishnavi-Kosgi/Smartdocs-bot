import os
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Tuple, List
from rag_engine import retrieve_context, build_prompt

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

GENERATION_MODEL = "gemini-1.5-flash"

# ──────────────────────────────────────────────
# Intent Detection
# ──────────────────────────────────────────────

SUMMARIZE_KEYWORDS = [
    "summarize", "summary", "summarise", "overview", "brief",
    "tldr", "tl;dr", "outline", "abstract", "gist"
]

EXPLAIN_KEYWORDS = [
    "explain", "what is", "what does", "what are", "define",
    "meaning of", "elaborate", "describe", "clarify", "simplify",
    "how does", "how do", "break down"
]


def detect_intent(query: str) -> str:
    """
    Classify user query into one of three intents:
      - 'summarize'  → user wants a paper summary
      - 'explain'    → user wants a concept explained simply
      - 'qa'         → user asks a specific question
    """
    q = query.lower().strip()

    for kw in SUMMARIZE_KEYWORDS:
        if kw in q:
            return "summarize"

    for kw in EXPLAIN_KEYWORDS:
        if kw in q:
            return "explain"

    return "qa"


# ──────────────────────────────────────────────
# LLM Call
# ──────────────────────────────────────────────

def call_gemini(prompt: str) -> str:
    """Send prompt to Gemini and return the generated text."""
    model = genai.GenerativeModel(GENERATION_MODEL)
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=1024,
        )
    )
    return response.text.strip()


# ──────────────────────────────────────────────
# Agent Orchestrator
# ──────────────────────────────────────────────

def run_agent(doc_id: str, query: str, top_k: int = 5) -> dict:
    """
    Main agent pipeline:
      1. Detect intent
      2. Retrieve relevant chunks via RAG
      3. Build intent-aware prompt
      4. Call Gemini LLM
      5. Return answer + sources + intent
    """
    # Step 1: Intent detection
    intent = detect_intent(query)

    # Step 2: Retrieve top-k relevant chunks
    # For summarize, retrieve more chunks to get broader coverage
    k = 8 if intent == "summarize" else top_k
    context_chunks = retrieve_context(doc_id, query if intent != "summarize" else "main findings methodology results conclusion", k)

    # Step 3: Build prompt
    prompt = build_prompt(intent, context_chunks, query)

    # Step 4: Generate response
    answer = call_gemini(prompt)

    # Step 5: Format sources for UI
    sources = [
        {
            "chunk_index": c.get("chunk_index"),
            "page": c.get("page"),
            "text": c["text"][:300] + ("…" if len(c["text"]) > 300 else ""),
            "score": round(c.get("score", 0), 4)
        }
        for c in context_chunks
    ]

    return {
        "intent": intent,
        "answer": answer,
        "sources": sources
    }
