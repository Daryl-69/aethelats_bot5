"""
rag_retriever.py — Retrieval interface for the Aethel AI Coach
===============================================================
Import this in main.py to augment chat prompts with RAG context.

Usage:
    from rag_retriever import retrieve_context
    context = retrieve_context("What skills do I need to become an MLE?")
    # Returns a formatted string to inject into the system prompt
"""

from pathlib import Path
from functools import lru_cache

CHROMA_DIR = Path(__file__).parent / "rag_chroma_db"
_collection = None  # lazy singleton


def _get_collection():
    """Lazy-load the ChromaDB collection once per process."""
    global _collection
    if _collection is not None:
        return _collection

    if not CHROMA_DIR.exists():
        return None  # RAG not built yet — fall back gracefully

    try:
        import chromadb
        from chromadb.utils import embedding_functions

        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-small-en-v1.5"
        )
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = client.get_collection("aethel_coach_kb", embedding_function=embedding_fn)
        return _collection
    except Exception as e:
        print(f"[RAG] Warning: Could not load ChromaDB: {e}")
        return None


def retrieve_context(question: str, n_results: int = 4) -> str:
    """
    Retrieve the top-N most relevant knowledge base chunks for a question.

    Returns a formatted string ready to be injected into the LLM system prompt.
    Returns an empty string if RAG is unavailable (fails silently).
    """
    collection = _get_collection()
    if collection is None:
        return ""

    try:
        results = collection.query(query_texts=[question], n_results=n_results)
        chunks = results["documents"][0]
        sources = [m["source"] for m in results["metadatas"][0]]

        if not chunks:
            return ""

        lines = ["RELEVANT KNOWLEDGE BASE CONTEXT:", "─" * 40]
        for chunk, source in zip(chunks, sources):
            lines.append(f"[Source: {source}]")
            lines.append(chunk.strip())
            lines.append("")
        return "\n".join(lines)

    except Exception as e:
        print(f"[RAG] Retrieval error: {e}")
        return ""


def retrieve_for_skill_gaps(skill_gaps: list[str]) -> str:
    """
    Special retriever: given a list of skill gaps, fetch course recommendations
    for each missing skill. Used to proactively suggest learning resources.
    """
    if not skill_gaps:
        return ""

    query_text = f"courses and resources for: {', '.join(skill_gaps[:5])}"
    return retrieve_context(query_text, n_results=5)


def retrieve_career_path(role: str) -> str:
    """
    Retrieve career path information for a specific target role.
    """
    query_text = f"career path skills salary levels for {role}"
    return retrieve_context(query_text, n_results=4)
