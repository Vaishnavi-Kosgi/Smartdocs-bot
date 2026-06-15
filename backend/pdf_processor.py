import fitz  # PyMuPDF
import re
from typing import List


def extract_text(file_path: str) -> str:
    """Extract raw text from all pages of a PDF."""
    doc = fitz.open(file_path)
    pages_text = []
    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        pages_text.append(f"[Page {page_num + 1}]\n{text}")
    doc.close()
    return "\n\n".join(pages_text)


def clean_text(text: str) -> str:
    """Remove noise and normalize whitespace."""
    # Remove excessive whitespace / blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove non-printable characters except newlines and tabs
    text = re.sub(r'[^\x20-\x7E\n\t]', ' ', text)
    # Collapse multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> List[dict]:
    """
    Split text into overlapping chunks.
    Returns list of dicts with 'text', 'chunk_index', and 'page_hint'.
    """
    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Try to break at a sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            if last_period > chunk_size // 2:
                end = start + last_period + 1
                chunk = text[start:end]

        # Extract page hint from chunk if present
        page_match = re.search(r'\[Page (\d+)\]', chunk)
        page_hint = int(page_match.group(1)) if page_match else None

        # Clean page markers from chunk text for cleaner LLM context
        clean_chunk = re.sub(r'\[Page \d+\]', '', chunk).strip()

        if clean_chunk:
            chunks.append({
                "text": clean_chunk,
                "chunk_index": chunk_index,
                "page": page_hint
            })
            chunk_index += 1

        start = end - overlap

    return chunks
