# ═══════════════════════════════════════════════════════════════
#  Aethel — HuggingFace Spaces Docker Deployment
#  Bot 1 (GLiNER) runs locally on CPU
#  Bots 3 & 4 call the HF Serverless Inference API
#  RAG ChromaDB is baked into the image at build time
# ═══════════════════════════════════════════════════════════════

FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces requires running as non-root user (UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# ── 1. Copy requirements and install dependencies ──────────────
COPY --chown=user requirements.txt ./requirements.txt

# Install CPU-only torch first (separate step to use --extra-index-url)
RUN pip install --no-cache-dir \
    torch \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Install the rest of the dependencies (including chromadb for RAG)
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    groq \
    PyPDF2 \
    python-multipart \
    requests \
    transformers \
    sentencepiece \
    gliner \
    Pillow \
    sqlalchemy \
    psycopg2-binary \
    fpdf2 \
    bcrypt \
    PyJWT \
    resend \
    slowapi \
    chromadb \
    onnxruntime \
    scikit-learn \
    sentence-transformers

# ── 2. Copy all backend source files ───────────────────────────
COPY --chown=user main.py ./main.py
COPY --chown=user evaluator_agent.py ./evaluator_agent.py
COPY --chown=user structure_agent.py ./structure_agent.py
COPY --chown=user database.py ./database.py
COPY --chown=user auth.py ./auth.py
COPY --chown=user name_signals.py ./name_signals.py
COPY --chown=user report_generator.py ./report_generator.py
COPY --chown=user email_service.py ./email_service.py
COPY --chown=user skill_graph.json ./skill_graph.json
COPY --chown=user skill_matcher.py ./skill_matcher.py
COPY --chown=user worker.py ./worker.py
COPY --chown=user process_dataset.py ./process_dataset.py
COPY --chown=user modal_bot3.py ./modal_bot3.py
COPY --chown=user modal_bot4.py ./modal_bot4.py
COPY --chown=user rag_builder.py ./rag_builder.py
COPY --chown=user rag_store.py ./rag_store.py
COPY --chown=user rag_retriever.py ./rag_retriever.py
COPY --chown=user adzuna_refresh.py ./adzuna_refresh.py

# ── 3. Copy RAG knowledge base (plain text files) ─────────────
COPY --chown=user rag_kb/ ./rag_kb/

# ── 4. Build ChromaDB at image build time ──────────────────────
# This bakes the vector database INTO the Docker image.
# It will persist across every cold start — no rebuild needed.
RUN python rag_store.py && \
    echo "[Docker Build] ✓ ChromaDB baked into image — RAG will be active on startup."

# HF Spaces requires port 7860
ENV PORT=7860
EXPOSE 7860

# Start the FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
