import os
import uuid
import shutil
import json
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from pdf_processor import extract_text, clean_text, chunk_text
import vector_store as vs
from graph_agent import graph
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

# ──────────────────────────────────────────────
# App Setup
# ──────────────────────────────────────────────

app = FastAPI(
    title="SmartDocs AI",
    description="RAG-powered research paper assistant using Google Gemini",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory doc registry: doc_id -> {filename, chunk_count}
doc_registry: dict = {}


# ──────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    doc_id: str
    query: str
    top_k: int = 5


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "SmartDocs AI backend is running"}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file, extract text, chunk it, generate embeddings,
    and store in FAISS. Returns doc_id and chunk count.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Save uploaded file
    doc_id = str(uuid.uuid4())[:8]
    save_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{file.filename}")

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        # Extract and clean text
        raw_text = extract_text(save_path)
        clean = clean_text(raw_text)

        if not clean.strip():
            raise HTTPException(status_code=422, detail="Could not extract text from this PDF. It may be image-based.")

        # Chunk text
        chunks = chunk_text(clean, chunk_size=800, overlap=120)

        if not chunks:
            raise HTTPException(status_code=422, detail="PDF had no processable text content.")

        # Store in ChromaDB (embeddings are generated automatically)
        vs.add_document(doc_id, chunks, filename=file.filename)

        # Register document
        doc_registry[doc_id] = {
            "doc_id": doc_id,
            "filename": file.filename,
            "chunk_count": len(chunks),
            "file_path": save_path
        }

        return {
            "doc_id": doc_id,
            "filename": file.filename,
            "chunk_count": len(chunks),
            "message": f"Successfully processed {len(chunks)} text chunks."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Run the RAG agent for a user query on a specific document.
    Returns: answer, intent, and source chunks.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    if not vs.document_exists(request.doc_id):
        raise HTTPException(status_code=404, detail=f"Document '{request.doc_id}' not found. Please upload it first.")

    try:
        config = {"configurable": {"thread_id": request.doc_id}}
        
        state_info = await graph.aget_state(config)
        messages = state_info.values.get("messages", []) if state_info.values else []
        messages.append(HumanMessage(content=request.query))
        
        final_state = await graph.ainvoke(
            {
                "messages": messages,
                "query": request.query,
                "doc_id": request.doc_id
            },
            config=config
        )
        
        return {
            "intent": final_state.get("intent", "qa"),
            "answer": final_state.get("response", ""),
            "sources": final_state.get("sources", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Run the RAG agent and stream the response tokens in real-time.
    Uses Server-Sent Events (SSE).
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    if not vs.document_exists(request.doc_id):
        raise HTTPException(status_code=404, detail=f"Document '{request.doc_id}' not found. Please upload it first.")

    async def event_generator():
        config = {"configurable": {"thread_id": request.doc_id}}
        
        state_info = await graph.aget_state(config)
        messages = state_info.values.get("messages", []) if state_info.values else []
        messages.append(HumanMessage(content=request.query))
        
        inputs = {
            "messages": messages,
            "query": request.query,
            "doc_id": request.doc_id
        }
        
        sources = []
        intent = "qa"
        final_answer = ""
        
        try:
            async for event in graph.astream_events(inputs, version="v2", config=config):
                kind = event["event"]
                
                if kind == "on_chat_model_stream":
                    token = event["data"]["chunk"].content
                    if token:
                        final_answer += token
                        yield f"event: token\ndata: {json.dumps(token)}\n\n"
                        
                elif kind == "on_chain_end":
                    name = event["name"]
                    if name in ["summarizer", "explainer", "qa_assistant"]:
                        output = event["data"].get("output", {})
                        if "sources" in output:
                            sources = output["sources"]
                        if "intent" in output:
                            intent = output["intent"]
            
            result_data = {
                "intent": intent,
                "sources": sources,
                "answer": final_answer
            }
            yield f"event: result\ndata: {json.dumps(result_data)}\n\n"
            yield "event: done\ndata: {}\n\n"
            
        except Exception as e:
            yield f"event: error\ndata: {json.dumps(str(e))}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/documents")
def list_documents():
    """List all uploaded documents."""
    disk_docs = vs.list_documents()
    documents = []
    for doc_id in disk_docs:
        if doc_id in doc_registry:
            documents.append(doc_registry[doc_id])
        else:
            meta = vs.get_document_metadata(doc_id)
            documents.append(meta)
    return {"documents": documents}


@app.delete("/documents/{doc_id}")
def delete_document(doc_id: str):
    """Delete a document's vector store, registry entry, and uploaded file."""
    # 1. Clean up from ChromaDB
    vs.delete_document(doc_id)

    # 2. Clean up from in-memory registry
    if doc_id in doc_registry:
        doc_registry.pop(doc_id)

    # 3. Clean up matching file(s) in UPLOAD_DIR
    try:
        if os.path.exists(UPLOAD_DIR):
            for filename in os.listdir(UPLOAD_DIR):
                if filename.startswith(f"{doc_id}_"):
                    file_path = os.path.join(UPLOAD_DIR, filename)
                    os.remove(file_path)
                    print(f"[Backend] Deleted uploaded file: {file_path}")
    except Exception as e:
        print(f"[Backend] Error deleting file for doc '{doc_id}': {e}")

    return {"status": "success", "message": f"Document {doc_id} successfully deleted."}

