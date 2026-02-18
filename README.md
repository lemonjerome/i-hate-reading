# I Hate Reading

A local NotebookLM clone that lets you upload PDF documents, ask questions about them, and get cited answers — all running entirely on your machine. No cloud APIs, no subscriptions.

![Built with](https://img.shields.io/badge/LLM-Qwen3%3A8B-blue) ![Vector DB](https://img.shields.io/badge/VectorDB-Qdrant-red) ![Framework](https://img.shields.io/badge/Framework-FastAPI-green)

---

## How It Works

### 1. Smart Document Processing
When you upload a PDF, the app extracts the text and splits it into overlapping chunks using a sentence-aware splitter. This means chunks respect sentence boundaries instead of cutting words in half, and they overlap slightly so important ideas that span two chunks aren't lost.

### 2. Semantic Embeddings
Each chunk is converted into a numerical vector (embedding) using a language model (`BAAI/bge-base-en-v1.5`). These vectors capture the *meaning* of the text, not just keywords. They're stored in Qdrant, a vector database optimized for similarity search.

### 3. Intelligent Query Planning
When you ask a question, the LLM breaks it down into multiple targeted search queries with thinking disabled for speed. For example, *"How does knowledge distillation compare to pruning?"* might become separate queries for "knowledge distillation technique" and "model pruning methods." This retrieves more relevant chunks than a single query would.

### 4. Vector Retrieval
The decomposed queries are run in parallel against Qdrant. Results are deduplicated by content to avoid redundant chunks, then passed to the reranker.

### 5. Cross-Encoder Reranking
Initial retrieval casts a wide net. A cross-encoder model (`BAAI/bge-reranker-base`) then re-scores every retrieved chunk by looking at the query and chunk *together*, producing much more accurate relevance rankings than the initial embedding similarity alone.

### 6. Context-Aware Answers
The best-ranked chunks are stitched together in document order and fed directly to the LLM. The model generates a Markdown-formatted answer with LaTeX math support and citations pointing back to specific document sections like `[paper.pdf#3]`.

### 7. Conversation Memory
Chat history is summarized into a compact 2–3 sentence recap by the LLM (with thinking disabled) before each new question. This gives the model conversational context without bloating the prompt, which is important for smaller models with limited context windows.

### 8. Automatic GPU Detection
The embedding and reranking models automatically detect your hardware:
- **Apple Silicon** → Metal Performance Shaders (MPS)
- **NVIDIA GPU** → CUDA
- **No GPU** → CPU fallback

### 9. Source Filtering
You can check/uncheck documents in the sidebar. Only checked documents are included in retrieval, so you can focus the model's attention on specific papers. Individual documents can also be deleted with the × button.

### 10. Session-Based Storage
Documents and chat history exist only for the current browser session. Closing the tab or refreshing the page clears all data — nothing persists between sessions.

---

## Performance Optimizations

| Optimization | Effect |
|---|---|
| **Consistent `num_ctx`** | All Ollama calls use the same context size to prevent costly model reloads between requests |
| **Thinking disabled for intermediates** | Planning and chat-summary calls skip Qwen3's `<think>` blocks, saving 5–10s per query |
| **No intermediate summarization** | Retrieved context is fed directly to the final answer instead of through an extra summarization LLM call |
| **Single retrieval round** | One retrieval pass instead of iterative multi-round, cutting 1–2 extra LLM calls |
| **No output token limit on answers** | Streaming answer generation runs until the model finishes naturally — no truncation |
| **Model preloading at startup** | Embedding and reranker models load during container startup, not on the first query |
| **Real-time status indicators** | Pulsing status messages (Planning → Searching → Reranking → Generating) keep the UI responsive |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| LLM | Qwen3:8B via Ollama (local) |
| Embeddings | BAAI/bge-base-en-v1.5 |
| Reranker | BAAI/bge-reranker-base |
| Vector DB | Qdrant |
| Backend | FastAPI + Uvicorn |
| Frontend | Vanilla HTML/CSS/JS + Marked.js + KaTeX |
| PDF Parsing | pypdf |
| Chunking | LlamaIndex SentenceSplitter |
| Containerization | Docker Compose |

---

## Setup Instructions

### Prerequisites

- **MPS** (Apple Silicon) or **CUDA** (NVIDIA GPU) device recommended
- **Docker Desktop** installed and running
- **Ollama** installed ([ollama.com/download](https://ollama.com/download) or `brew install ollama`)

### Step 1: Start Ollama

Ollama runs **natively** on your host to access the GPU (Docker can't access Metal/MPS).

In a **separate terminal** (keep it running):

```bash
ollama serve
```

You should see it listening on `http://127.0.0.1:11434`.

### Step 2: Pull the LLM Model

In another terminal, pull the model while Ollama is serving:

```bash
ollama pull qwen3:8b
```

This downloads ~5 GB. Verify it's there:

```bash
ollama list
```

### Step 3: Clone and Start

```bash
git clone https://github.com/your-username/i-hate-reading.git
cd i-hate-reading
docker compose up --build
```

This starts:
- **Qdrant** (vector database) on port 6333
- **notebook-agent** (backend + frontend) on port 8000

First build takes a few minutes to download dependencies and models.

### Step 4: Open the App

Go to [http://localhost:8000](http://localhost:8000) in your browser.

1. Upload one or more PDF documents
2. Wait for processing to complete
3. Ask questions about your documents
4. Get cited, formatted answers with math rendering

---

## Stopping the App

```bash
# Stop Docker services
docker compose down

# Stop Ollama (Ctrl+C in the terminal running `ollama serve`)
```

---

## Environment Variables

Configured in `docker-compose.yml` under `notebook-agent`:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `qwen3:8b` | LLM model name |
| `QDRANT_HOST` | `http://qdrant:6333` | Qdrant URL |
| `NUM_CTX` | `8192` | Context window size for all LLM calls |
| `RERANK_MODEL` | `BAAI/bge-reranker-base` | Cross-encoder model |
| `ENABLE_RERANK` | `1` | Toggle reranking (0 to disable) |
| `MAX_CONTEXT_CHUNKS` | `8` | Max chunks in final prompt |

---

## Project Structure

```
i-hate-reading/
├── docker-compose.yml
├── .env
├── README.md
└── agent/
    ├── Dockerfile
    ├── requirements.txt
    ├── app.py                  # FastAPI server
    ├── rag/
    │   ├── pipeline.py         # RAG orchestrator
    │   ├── planner.py          # Query decomposition
    │   ├── retrieval.py        # Vector search
    │   ├── rerank.py           # Cross-encoder reranking
    │   ├── embeddings.py       # Text → vectors
    │   ├── chunking.py         # Document splitting
    │   ├── ingestion.py        # PDF → chunks → Qdrant
    │   ├── llm.py              # Ollama API wrapper
    │   └── vector_store.py     # Qdrant client
    └── static/
        ├── index.html
        ├── css/styles.css
        └── js/app.js
```

---

*Built by lemonjerome.*
