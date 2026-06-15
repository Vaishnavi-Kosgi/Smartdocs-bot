import os
import chromadb
from typing import List, Dict, Any, Union
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

STORE_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
os.makedirs(STORE_DIR, exist_ok=True)

# Initialize LangChain Embeddings using Google Gemini API
embeddings_model = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY")
)


def add_document(doc_id: str, chunks: List[dict], filename: str) -> None:
    """Build and persist a ChromaDB collection for a document."""
    # Chroma collection names must start with a letter and contain only alphanumeric, _ or -
    collection_name = f"doc_{doc_id}"

    texts = [c["text"] for c in chunks]
    # Keep chunk metadata (like page and chunk_index)
    metadatas = [
        {
            "chunk_index": c["chunk_index"],
            "page": c.get("page") or 0
        }
        for c in chunks
    ]
    ids = [f"{doc_id}_{c['chunk_index']}" for c in chunks]

    # Initialize Chroma client and create collection with metadata
    client = chromadb.PersistentClient(path=STORE_DIR)
    
    # Check if collection exists and delete it to overwrite if necessary
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        pass

    # Create collection with filename in metadata
    collection = client.create_collection(name=collection_name, metadata={"filename": filename})

    # Generate embeddings in batches with retry / rate-limit logic
    from embeddings import batch_embed
    embeddings = batch_embed(chunks)

    # Add documents and pre-computed embeddings directly to Chroma collection
    collection.add(
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )
    print(f"[VectorStore] Stored {len(chunks)} chunks for doc '{doc_id}' ({filename}) in ChromaDB")


def search(doc_id: str, query: Union[str, List[float]], top_k: int = 5) -> List[dict]:
    """Retrieve the top-k most relevant chunks for a query from ChromaDB."""
    collection_name = f"doc_{doc_id}"
    
    if not document_exists(doc_id):
        raise ValueError(f"Document '{doc_id}' not found in vector store.")

    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings_model,
        persist_directory=STORE_DIR
    )

    if isinstance(query, str):
        results = vector_store.similarity_search_with_score(query, k=top_k)
    else:
        # If query is a vector (list of floats), query Chroma raw collection directly
        try:
            col = vector_store._collection
            res = col.query(query_embeddings=[query], n_results=top_k)
            results = []
            if res and "documents" in res and res["documents"]:
                ids = res["ids"][0]
                documents = res["documents"][0]
                metadatas = res["metadatas"][0]
                distances = res["distances"][0] if "distances" in res else [0.0] * len(ids)
                
                from langchain_core.documents import Document
                for idx in range(len(ids)):
                    doc = Document(
                        page_content=documents[idx],
                        metadata=metadatas[idx]
                    )
                    results.append((doc, distances[idx]))
        except Exception as e:
            print(f"[VectorStore] Direct vector query failed: {e}. Falling back to default search.")
            results = []

    formatted_results = []
    for doc, score in results:
        # Normalize/format the score
        similarity = 1.0 / (1.0 + float(score)) if score is not None else 0.0
        formatted_results.append({
            "text": doc.page_content,
            "chunk_index": doc.metadata.get("chunk_index"),
            "page": doc.metadata.get("page"),
            "score": similarity
        })

    return formatted_results


def list_documents() -> List[str]:
    """Return all known document IDs (from ChromaDB collections)."""
    client = chromadb.PersistentClient(path=STORE_DIR)
    collections = client.list_collections()
    doc_ids = []
    for col in collections:
        if col.name.startswith("doc_"):
            # strip "doc_" prefix to get the original doc_id
            doc_ids.append(col.name[4:])
    return sorted(doc_ids)


def get_document_metadata(doc_id: str) -> Dict[str, Any]:
    """Get stored metadata for a document collection."""
    collection_name = f"doc_{doc_id}"
    client = chromadb.PersistentClient(path=STORE_DIR)
    try:
        col = client.get_collection(name=collection_name)
        metadata = col.metadata or {}
        count = col.count()
        return {
            "doc_id": doc_id,
            "filename": metadata.get("filename", f"Document {doc_id}"),
            "chunk_count": count
        }
    except Exception:
        return {
            "doc_id": doc_id,
            "filename": f"Document {doc_id}",
            "chunk_count": None
        }


def document_exists(doc_id: str) -> bool:
    """Check if a document's ChromaDB collection exists."""
    collection_name = f"doc_{doc_id}"
    client = chromadb.PersistentClient(path=STORE_DIR)
    try:
        client.get_collection(name=collection_name)
        return True
    except Exception:
        return False


def delete_document(doc_id: str) -> None:
    """Delete the ChromaDB collection for a document."""
    collection_name = f"doc_{doc_id}"
    client = chromadb.PersistentClient(path=STORE_DIR)
    try:
        client.delete_collection(name=collection_name)
        print(f"[VectorStore] Deleted ChromaDB collection for doc '{doc_id}'")
    except Exception as e:
        print(f"[VectorStore] Error deleting collection for doc '{doc_id}': {e}")

