import os
from typing import Any, Dict, List, Tuple, Iterator
from collections import defaultdict

from .retrieval import retrieve
from .planner import plan_queries
from .llm import generate_text, generate_text_stream
from .rerank import rerank

def _dedupe_hits(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[Tuple[str, str]] = set()
    out = []
    for h in hits:
        key = (str(h.get("source", "")), str(h.get("text", ""))[:200])
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out


def _summarize_chat_history(chat_history: List[dict]) -> str:
    """Summarize recent chat history into a compact context."""
    if not chat_history:
        return ""

    recent_history = chat_history[-6:]

    history_text = "Recent conversation:\n"
    for msg in recent_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")[:300]
        history_text += f"{role}: {content}\n"

    summary_prompt = f"""
    Summarize this conversation in 2-3 sentences. Focus on key topics and conclusions.

    {history_text}
    """.strip()

    summary = generate_text(summary_prompt, temperature=0.1, max_tokens=150, think=False)
    return summary.strip()


def _stitch_context(hits: List[Dict[str, Any]], max_chunks: int = 8) -> str:
    def key(h: Dict[str, Any]):
        return (
            str(h.get("source", "")),
            str(h.get("doc_id", "")),
            int(
                h.get("chunk_index")
                if h.get("chunk_index") is not None
                else 10**9
            ),
        )

    selected = hits[:max_chunks]
    selected_sorted = sorted(selected, key=key)

    stitched = []
    for h in selected_sorted:
        source = h.get("source", "unknown")
        idx = h.get("chunk_index", "?")
        stitched.append(f"[{source}#{idx}] {h.get('text', '')}")
    return "\n\n".join(stitched)


def answer_question_stream(
    question: str,
    chat_history: List[dict] = None,
    selected_sources: List[str] = None,
) -> Iterator[Dict[str, Any]]:
    enable_rerank = os.getenv("ENABLE_RERANK", "1") not in ("0", "false", "False")
    max_context_chunks = int(os.getenv("MAX_CONTEXT_CHUNKS", "8"))

    chat_history = chat_history or []
    selected_sources = selected_sources or []

    # Summarize chat context (with thinking disabled for speed)
    chat_summary = ""
    if chat_history:
        yield {"type": "status", "message": "Summarizing conversation..."}
        chat_summary = _summarize_chat_history(chat_history)

    # Planning (thinking disabled — simple JSON task)
    yield {"type": "status", "message": "Planning queries..."}
    plan = plan_queries(question)
    queries = plan["queries"]
    top_k = plan["top_k"]

    # Retrieval
    yield {"type": "status", "message": f"Searching documents ({len(queries)} queries)..."}
    all_hits: List[Dict[str, Any]] = []
    for q in queries:
        res = retrieve(q, top_k=top_k, filter_sources=selected_sources)
        if isinstance(res, dict) and res.get("error"):
            yield {"type": "error", "error": res["error"], "plan": plan}
            return
        all_hits.extend(res)

    all_hits = _dedupe_hits(all_hits)

    # Rerank
    if enable_rerank:
        yield {"type": "status", "message": "Reranking results..."}
        all_hits = rerank(question, all_hits, top_n=max_context_chunks)
    else:
        all_hits.sort(key=lambda x: (x.get("score") or 0), reverse=True)
        all_hits = all_hits[:max_context_chunks]

    stitched_context = _stitch_context(all_hits, max_chunks=max_context_chunks)

    yield {
        "type": "metadata",
        "plan": plan,
        "hits": all_hits,
        "context": stitched_context,
    }

    # Build final prompt (no intermediate summary — feed context directly)
    yield {"type": "status", "message": "Generating answer..."}

    chat_context_section = ""
    if chat_summary:
        chat_context_section = f"""
Previous Conversation Summary:
{chat_summary}
"""

    final_prompt = f"""
Answer the user using ONLY the context below. Format in clean Markdown.
Use citations like [source#chunk] for key claims.
If context is insufficient, state what is missing.
{chat_context_section}
Question: {question}

Context:
{stitched_context}

Answer:
""".strip()

    for token in generate_text_stream(final_prompt, temperature=0.2):
        yield {"type": "token", "content": token}

    yield {"type": "done"}