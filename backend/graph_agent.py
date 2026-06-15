import os
from typing import TypedDict, List, Dict, Any, Literal, Annotated
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages

load_dotenv()

import vector_store as vs
from agent import detect_intent
from rag_engine import format_context

# Define State Schema
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    query: str
    intent: str
    doc_id: str
    context: List[dict]
    response: str
    sources: List[dict]


# ──────────────────────────────────────────────
# Nodes
# ──────────────────────────────────────────────

async def condense_query(state: AgentState) -> Dict[str, Any]:
    """
    If there is chat history, reformulate the user query to be 
    a standalone search query.
    """
    messages = state.get("messages", [])
    latest_query = state.get("query", "")
    
    # If no history besides current question, skip condensation
    if len(messages) <= 1:
        return {"query": latest_query}
        
    llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0.1)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Given a chat history and the latest user question which might reference context in the chat history, formulate a standalone question which can be understood without the chat history. Do NOT answer the question, just reformulate it if needed and otherwise return it as is."),
        *messages[:-1],  # Include previous turns
        ("human", "{latest_question}")
    ])
    
    chain = prompt | llm
    
    try:
        result = await chain.ainvoke({"latest_question": latest_query})
        condensed = result.content.strip()
        print(f"[GraphAgent] Condensed query: '{latest_query}' -> '{condensed}'")
        return {"query": condensed}
    except Exception as e:
        print(f"[GraphAgent] Error condensing query: {e}. Using original.")
        return {"query": latest_query}


async def route_intent(state: AgentState) -> Dict[str, Any]:
    """Detect the user's intent (summarize, explain, or qa)."""
    # We can detect intent using the keywords regex in agent.py
    intent = detect_intent(state["query"])
    print(f"[GraphAgent] Query '{state['query']}' routed as intent: '{intent}'")
    return {"intent": intent}


async def retrieve_context(state: AgentState) -> Dict[str, Any]:
    """Retrieve relevant chunks from ChromaDB based on intent and query."""
    intent = state.get("intent", "qa")
    doc_id = state["doc_id"]
    query = state["query"]
    
    # Retrieve top-k based on intent
    k = 8 if intent == "summarize" else 5
    
    # If summarizing, use broad keywords to search for representative parts of the paper
    search_query = query if intent != "summarize" else "abstract main findings methodology results conclusion summary"
    
    try:
        context_chunks = vs.search(doc_id, search_query, top_k=k)
    except Exception as e:
        print(f"[GraphAgent] Chroma search error: {e}")
        context_chunks = []
        
    return {"context": context_chunks}


# ──────────────────────────────────────────────
# Agent Generator Nodes (Async)
# ──────────────────────────────────────────────

async def summarizer_agent(state: AgentState) -> Dict[str, Any]:
    """Generate a structured summary of the document using CoT reasoning."""
    context_str = format_context(state["context"])
    
    prompt = f"""You are a research assistant. Based ONLY on the provided context, generate a structured summary of the research paper.
Do NOT add any information not present in the context.

Few-Shot Example:
Context:
[Chunk 1] (Page 1)
This paper introduces ResNet, a deep residual learning framework to ease training of networks that are substantially deeper than those previously used. We present residual connections...
[Chunk 2] (Page 12)
Our experiments show that ResNet achieves 3.57% error on ImageNet test set and won 1st place in ILSVRC 2015. We evaluated on depths up to 152 layers...

Structured Summary:
- **Main Objective**: Ease the training of substantially deeper neural networks using a residual learning framework.
- **Methodology**: Introduce shortcut connections (residual connections) that perform identity mapping, allowing gradients to flow directly. Tested on depths up to 152 layers.
- **Key Findings**: Achieved a 3.57% error rate on the ImageNet test set and won 1st place in the ILSVRC 2015 competition.
- **Conclusions**: Residual learning facilitates optimization and improves accuracy from greatly increased depth.

Now, summarize the paper based on the following context.

Context:
{context_str}

Structured Summary:"""
    
    llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0.2, streaming=True)
    res = await llm.ainvoke(prompt)
    
    sources = [
        {
            "chunk_index": c.get("chunk_index"),
            "page": c.get("page"),
            "text": c["text"][:300] + ("…" if len(c["text"]) > 300 else ""),
            "score": round(c.get("score", 0), 4)
        }
        for c in state["context"]
    ]
    
    return {"intent": "summarize", "response": res.content, "sources": sources, "messages": [AIMessage(content=res.content)]}


async def explainer_agent(state: AgentState) -> Dict[str, Any]:
    """Explain a concept simply with analogies using only context."""
    context_str = format_context(state["context"])
    query = state["query"]
    
    prompt = f"""You are a helpful teacher. Using ONLY the provided context, explain the concept or section in simple, easy-to-understand language.
Avoid jargon where possible, and use analogies if helpful.
Do NOT add any information not present in the context.

Context:
{context_str}

Question / Topic: {query}

Simple Explanation:"""
    
    llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0.3, streaming=True)
    res = await llm.ainvoke(prompt)
    
    sources = [
        {
            "chunk_index": c.get("chunk_index"),
            "page": c.get("page"),
            "text": c["text"][:300] + ("…" if len(c["text"]) > 300 else ""),
            "score": round(c.get("score", 0), 4)
        }
        for c in state["context"]
    ]
    
    return {"intent": "explain", "response": res.content, "sources": sources, "messages": [AIMessage(content=res.content)]}


async def qa_agent(state: AgentState) -> Dict[str, Any]:
    """Answer questions precisely, strictly grounded in the document context."""
    context_str = format_context(state["context"])
    query = state["query"]
    
    prompt = f"""You are a research assistant. Answer the user's question using ONLY the context provided below.
If the answer cannot be found in the context, respond with exactly: "Not found in document."
Do NOT use any prior knowledge or make assumptions beyond the provided context.

Context:
{context_str}

Question: {query}

Answer:"""
    
    llm = ChatGroq(model_name="llama-3.1-8b-instant", temperature=0.1, streaming=True)
    res = await llm.ainvoke(prompt)
    
    sources = [
        {
            "chunk_index": c.get("chunk_index"),
            "page": c.get("page"),
            "text": c["text"][:300] + ("…" if len(c["text"]) > 300 else ""),
            "score": round(c.get("score", 0), 4)
        }
        for c in state["context"]
    ]
    
    return {"intent": "qa", "response": res.content, "sources": sources, "messages": [AIMessage(content=res.content)]}


# ──────────────────────────────────────────────
# Workflow Compilation
# ──────────────────────────────────────────────

def route_to_agent(state: AgentState) -> str:
    """Conditional edge router based on detected intent."""
    intent = state.get("intent", "qa")
    if intent == "summarize":
        return "summarizer"
    elif intent == "explain":
        return "explainer"
    else:
        return "qa_assistant"


workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("condense_query", condense_query)
workflow.add_node("route_intent", route_intent)
workflow.add_node("retrieve_context", retrieve_context)
workflow.add_node("summarizer", summarizer_agent)
workflow.add_node("explainer", explainer_agent)
workflow.add_node("qa_assistant", qa_agent)

# Add Edges
workflow.set_entry_point("route_intent")
workflow.add_edge("route_intent", "condense_query")
workflow.add_edge("condense_query", "retrieve_context")

workflow.add_conditional_edges(
    "retrieve_context",
    route_to_agent,
    {
        "summarizer": "summarizer",
        "explainer": "explainer",
        "qa_assistant": "qa_assistant"
    }
)

workflow.add_edge("summarizer", END)
workflow.add_edge("explainer", END)
workflow.add_edge("qa_assistant", END)

# Compile with Memory
memory = MemorySaver()
graph = workflow.compile(checkpointer=memory)
