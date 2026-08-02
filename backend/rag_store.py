"""
rag_store.py — Embeds knowledge base documents into ChromaDB
=============================================================
Run AFTER rag_builder.py:
    python backend/rag_store.py

Uses:
  - sentence-transformers (BAAI/bge-small-en-v1.5): fast, free, runs on CPU
  - ChromaDB: local persistent vector store (no API key, no cost)

Outputs → backend/rag_chroma_db/ (persistent vector database)
"""

from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

KB_DIR    = Path(__file__).parent / "rag_kb"
CHROMA_DIR = Path(__file__).parent / "rag_chroma_db"

# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list[str]:
    """
    Split text into overlapping chunks by word count.
    Overlap preserves context at chunk boundaries.
    """
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return [c for c in chunks if len(c.strip()) > 50]  # drop tiny chunks


# ── Build / update the ChromaDB collection ────────────────────────────────────

def build_store():
    if not KB_DIR.exists() or not list(KB_DIR.glob("*.txt")):
        print("❌ No documents found in rag_kb/. Run rag_builder.py first.")
        return

    # Use a local sentence-transformer model for embeddings (free, no API key)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="BAAI/bge-small-en-v1.5"  # 33MB, fast on CPU, high quality
    )

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Delete and recreate collection to allow clean rebuilds
    try:
        client.delete_collection("aethel_coach_kb")
    except Exception:
        pass

    collection = client.create_collection(
        name="aethel_coach_kb",
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )

    all_docs, all_ids, all_metas = [], [], []
    doc_counter = 0

    txt_files = sorted(KB_DIR.glob("*.txt"))
    print(f"Indexing {len(txt_files)} documents...")

    for txt_file in txt_files:
        text = txt_file.read_text(encoding="utf-8")
        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            all_docs.append(chunk)
            all_ids.append(f"{txt_file.stem}_{i}")
            all_metas.append({"source": txt_file.name, "chunk": i})
            doc_counter += 1

    # Add in batches of 100 (ChromaDB recommendation)
    batch_size = 100
    for start in range(0, len(all_docs), batch_size):
        collection.add(
            documents=all_docs[start : start + batch_size],
            ids=all_ids[start : start + batch_size],
            metadatas=all_metas[start : start + batch_size],
        )
        print(f"  Indexed chunks {start} – {min(start + batch_size, len(all_docs))}")

    print(f"\n✓ ChromaDB built: {doc_counter} chunks from {len(txt_files)} documents")
    print(f"  Stored at: {CHROMA_DIR}")
    print("Next step: import rag_retriever.py in your main.py chat endpoint.")


# ── Query helper (test it here) ───────────────────────────────────────────────

def query(question: str, n_results: int = 4) -> list[str]:
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="BAAI/bge-small-en-v1.5"
    )
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection("aethel_coach_kb", embedding_function=embedding_fn)
    results = collection.query(query_texts=[question], n_results=n_results)
    return results["documents"][0]


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # Test mode: python backend/rag_store.py "what skills do I need for MLE?"
        question = " ".join(sys.argv[1:])
        print(f"\nQuery: {question}\n")
        chunks = query(question)
        for i, chunk in enumerate(chunks):
            print(f"--- Result {i+1} ---\n{chunk}\n")
    else:
        build_store()
