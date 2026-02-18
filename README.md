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
When you ask a question, the LLM first breaks it down into multiple targeted search queries. For example, *"How does knowledge distillation compare to pruning?"* might become separate queries for "knowledge distillation technique" and "model pruning methods." This retrieves more relevant chunks than a single query would.

### 4. Multi-Round Retrieval
The system can perform multiple rounds of search. After the first round, it summarizes what it found and identifies gaps, then generates follow-up queries to fill those gaps. This mimics how a researcher would iteratively refine their search.

### 5. Cross-Encoder Reranking
Initial retrieval casts a wide net. A cross-encoder model (`BAAI/bge-reranker-base`) then re-scores every retrieved chunk by looking at the query and chunk *together*, producing much more accurate relevance rankings than the initial embedding similarity alone.

### 6. Context-Aware Answers
The best-ranked chunks are stitched together in document order and fed to the LLM along with a summary of the retrieval results. The LLM generates a Markdown-formatted answer with citations pointing back to specific document sections like `[paper.pdf#3]`.

### 7. Conversation Memory
Chat history is summarized into a compact 2–3 sentence recap by the LLM before each new question. This gives the model conversational context without bloating the prompt, which is important for smaller models with limited context windows.

### 8. Automatic GPU Detection
The embedding and reranking models automatically detect your hardware:
- **Apple Silicon (M1–M4)** → Metal Performance Shaders (MPS)
- **NVIDIA GPU** → CUDA
- **No GPU** → CPU fallback

### 9. Source Filtering
You can check/uncheck documents in the sidebar. Only checked documents are included in retrieval, so you can focus the model's attention on specific papers.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| LLM | Qwen3:8B via Ollama (local) |
| Embeddings | BAAI/bge-base-en-v1.5 |
| Reranker | BAAI/bge-reranker-base |
| Vector DB | Qdrant |
| Backend | FastAPI + Uvicorn |
| Frontend | Vanilla HTML/CSS/JS + Marked.js |
| PDF Parsing | pypdf |
| Chunking | LlamaIndex SentenceSplitter |
| Containerization | Docker Compose |

---

## Setup Instructions

### Prerequisites

- **macOS** with Apple Silicon (M1/M2/M3/M4) recommended
- **Docker Desktop** installed and running
- **Homebrew** installed (for Ollama)

### Step 1: Install Ollama

Ollama runs **natively** on your Mac to use the Metal GPU (Docker can't access it).

```bash
brew install ollama
```

Or download from [ollama.com/download](https://ollama.com/download).

### Step 2: Start Ollama

In a **separate terminal** (keep it running):

```bash
ollama serve
```

You should see it listening on `http://127.0.0.1:11434`.

### Step 3: Pull the LLM Model

In another terminal, pull the model while Ollama is serving:

```bash
ollama pull qwen3:8b
```

This downloads ~5 GB. Verify it's there:

```bash
ollama list
```

### Step 4: Clone the Repository

```bash
git clone https://github.com/your-username/i-hate-reading.git
cd i-hate-reading
```

### Step 5: Start the App

In another terminal:

```bash
docker-compose up --build
```

This starts:
- **Qdrant** (vector database) on port 6333
- **notebook-agent** (backend + frontend) on port 8000

First build takes a few minutes to download dependencies and models.

### Step 6: Open the App

Go to [http://localhost:8000](http://localhost:8000) in your browser.

1. Upload one or more PDF documents
2. Wait for processing to complete
3. Ask questions about your documents
4. Get cited, formatted answers

---

## Stopping the App

```bash
# Stop Docker services
docker-compose down

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
