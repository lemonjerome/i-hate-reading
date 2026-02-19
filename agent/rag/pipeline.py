import os
from typing import Any, Dict, List, Tuple, Iterator
from collections import defaultdict

from .retrieval import retrieve
from .planner import plan_queries
from .llm import generate_text, generate_text_stream
from .rerank import rerank
from .vector_store import client, COLLECTION

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
    # MAX_CONTEXT_CHUNKS env var acts as a hard cap; tier-based value is used otherwise
    hard_cap = int(os.getenv("MAX_CONTEXT_CHUNKS", "24"))

    chat_history = chat_history or []
    selected_sources = selected_sources or []

    # --- Count chunks/sources in the active collection ---
    try:
        count_result = client.count(collection_name=COLLECTION, exact=True)
        total_chunks = count_result.count
    except Exception:
        total_chunks = 0

    # Count distinct sources (or cap at a scroll)
    try:
        scroll_result = client.scroll(
            collection_name=COLLECTION,
            limit=10000,
            with_payload=["source"],
            with_vectors=False,
        )
        active_sources = set()
        for pt in scroll_result[0]:
            if pt.payload and "source" in pt.payload:
                # Only count sources the user has selected (or all if no filter)
                src = pt.payload["source"]
                if not selected_sources or src in selected_sources:
                    active_sources.add(src)
        source_count = len(active_sources)
    except Exception:
        source_count = len(selected_sources) if selected_sources else 1

    yield {
        "type": "status",
        "message": f"Indexed {total_chunks} chunks across {source_count} document(s) — planning search...",
    }

    # Summarize chat context (with thinking disabled for speed)
    chat_summary = ""
    if chat_history:
        yield {"type": "status", "message": "Summarizing conversation history..."}
        chat_summary = _summarize_chat_history(chat_history)

    # Planning — scaled to collection size
    plan = plan_queries(question, chunk_count=total_chunks, source_count=source_count)
    queries = plan["queries"]
    top_k = plan["top_k"]
    tier_note = plan.get("tier", "")
    # Final context window: tier recommendation capped by hard override
    max_context_chunks = min(plan["max_context_chunks"], hard_cap)

    yield {
        "type": "status",
        "message": f"Running {len(queries)} search quer{'y' if len(queries) == 1 else 'ies'} (top {top_k} per query, up to {max_context_chunks} final chunks)...",
    }

    # Retrieval — emit per-query progress
    all_hits: List[Dict[str, Any]] = []
    for i, q in enumerate(queries, 1):
        short_q = q if len(q) <= 60 else q[:57] + "..."
        yield {"type": "status", "message": f"Query {i}/{len(queries)}: \"{short_q}\""}
        res = retrieve(q, top_k=top_k, filter_sources=selected_sources)
        if isinstance(res, dict) and res.get("error"):
            yield {"type": "error", "error": res["error"], "plan": plan}
            return
        all_hits.extend(res)

    all_hits = _dedupe_hits(all_hits)
    unique_sources = len({h.get("source") for h in all_hits})

    yield {
        "type": "status",
        "message": f"Retrieved {len(all_hits)} candidate chunks from {unique_sources} source(s)...",
    }

    # Rerank
    if enable_rerank:
        yield {
            "type": "status",
            "message": f"Reranking {len(all_hits)} chunks → selecting top {max_context_chunks}...",
        }
        all_hits = rerank(question, all_hits, top_n=max_context_chunks)
    else:
        all_hits.sort(key=lambda x: (x.get("score") or 0), reverse=True)
        all_hits = all_hits[:max_context_chunks]

    stitched_context = _stitch_context(all_hits, max_chunks=max_context_chunks)

    # Surface which sources made it into the final context
    final_sources = sorted({h.get("source", "?") for h in all_hits})
    sources_label = ", ".join(final_sources) if final_sources else "unknown"

    yield {
        "type": "metadata",
        "plan": plan,
        "hits": all_hits,
        "context": stitched_context,
    }

    yield {
        "type": "status",
        "message": f"Generating answer from {len(all_hits)} chunks ({sources_label})...",
    }

    chat_context_section = ""
    if chat_summary:
        chat_context_section = f"""
Previous Conversation Summary:
{chat_summary}
"""

    final_prompt = f"""
Answer the user using ONLY the context below. Format in clean Markdown.
Cite sources by copying the exact tags from the context (e.g. [filename.pdf#2]).
Don't put citations inside latex. This will break latex processing. Only clean math should be inside latex delimiters.
Every key claim must have at least one citation. Do NOT write [source#chunk] literally.
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