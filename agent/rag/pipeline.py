import os
from typing import Any, Dict, List, Tuple, Iterator
from collections import defaultdict

from .retrieval import retrieve
from .planner import plan_queries, followup_queries
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

def _summarize_hits(question: str, hits: List[Dict[str, Any]]) -> str:
    by_source = defaultdict(list)
    for h in hits:
        by_source[str(h.get("source", "unknown"))].append(h)

    blocks = []
    for source, hs in by_source.items():
        hs = sorted (hs, key=lambda x: (x.get("rerank_score", x.get("score", 0))or 0), reverse=True)[:6]
        excerpts = "\n".join(
            f"- [{source}#{h.get('chunk_index')}] {h.get('text', '')[:700]}"
            for h in hs
        )
        blocks.append(f"SOURCE: {source}\n{excerpts}")

    prompt = f"""
    Summarize the retrieved information to supportanswering the user's question.
    Write a compact bullet summary and explicitly mention uncertainties/gaps.

    Here is the User Question:
    {question}

    Retrieved Excerpts:
    {chr(10).join(blocks)}
    """.strip()

    return generate_text(prompt, temperature=0.2)

def _summarize_chat_history(chat_history: List[dict]) -> str:
    if not chat_history:
        return ""
    
    recent_history = chat_history[-8:]

    history_text = "Recent conversation:\n"

    for msg in recent_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        history_text += f"{role}: {content}\n"

    summary_prompt = f"""
    Summarize this conversation history into bullets focusing on:
    - Key topics discussed
    - Relevant terms mentioned and defined
    - Important conclusions or facts mentioned
    - Context relevant to continuing the conversation

    The roles should still be mentioned for example:

    '''
    user: <question 1>
    assistant: <response in bullets>

    user: <question 2>
    assistant: <response in bullets>
    '''

    Keep the bullets brief and factual.

    {history_text}
    """.strip()

    summary = generate_text(summary_prompt, temperature=0.1)
    return summary.strip()

def _stitch_context(hits: List[Dict[str, Any]], max_chunks: int = 12) -> str:
    def key(h: Dict[str, Any]):
        return (
            str(h.get("source", "")),
            str(h.get("doc_id", "")),
            int(h.get("chunk_index") if h.get("chunk_index") is not None else 10**9)
        )
    
    selected = hits[:max_chunks]
    selected_sorted = sorted(selected, key=key)

    stitched = []
    for h in selected_sorted:
        source = h.get("source", "unknown")
        idx = h.get("chunk_index", "?")
        stitched.append(f"[{source}#{idx}] {h.get('text', '')}")
    return "\n\n".join(stitched)

def answer_question_stream(question: str, chat_history: List[dict], selected_sources: List[dict]) -> Iterator[Dict[str, Any]]:
    enable_rerank = os.getenv("ENABLE_RERANK", "1") not in ("0", "false", "False")
    max_context_chunks = int(os.getenv("MAX_CONTEXT_CHUNKS", "12"))

    chat_history = chat_history or []
    selected_sources = selected_sources or []

    # Chat Context
    chat_summary = ""
    if chat_history:
        chat_summary = _summarize_chat_history(chat_history)

    
    # Initial Planning
    plan = plan_queries(question)
    queries = plan["queries"]
    top_k = plan["top_k"]
    rounds = plan["rounds"]

    all_hits: List[Dict[str, Any]] = []
    intermediate_summary = ""

    # Iterative Planning
    for r in range(max(1, rounds)):
        round_hits: List[Dict[str, Any]] = []
        for q in queries:
            res = retrieve(q, top_k=top_k, filter_sources=selected_sources)
            if isinstance(res, dict) and res.get("error"):
                yield {"type": "error", "error": res["error"], "plan": plan}
                return
            round_hits.extend(res)

        round_hits = _dedupe_hits(round_hits)

        if enable_rerank:
            round_hits=rerank(question, round_hits, top_n=max_context_chunks*2)
        else:
            round_hits.sort(key=lambda x: (x.get("score") or 0), reverse=True)
            round_hits = round_hits[: max_context_chunks*2]

        all_hits = _dedupe_hits(all_hits + round_hits)

        intermediate_summary = _summarize_hits(question, all_hits[: max_context_chunks * 2])

        if r < rounds - 1:
            next_qs = followup_queries(question, intermediate_summary)
            if next_qs:
                queries = next_qs

    # Final Answer
    final_hits = all_hits
    if enable_rerank:
        final_hits = rerank(question, final_hits, top_n=max_context_chunks)
    else:
        final_hits.sort(key=lambda x: (x.get("score") or 0), reverse=True)
        final_hits = final_hits[:max_context_chunks]

    stitched_context = _stitch_context(final_hits, max_chunks=max_context_chunks)

    yield {
        "type": "metadata",
        "plan": plan,
        "intermediate_summary": intermediate_summary,
        "hits": final_hits,
        "context": stitched_context,
    }

    final_prompt = f"""
    Answer the user using ONLY the context below. Format your response in clean Markdown:
    - Use **bold** for emphasis
    - Use ## for section headers if needed
    - Use bullet points with - or numbered lists
    - Use `code` for technical terms
    - Include citations like [source#chunk_index] for key claims
    
    If the context is insufficient, clearly state what information is missing.

    Chat Context:
    {chat_summary}

    Current Question:
    {question}

    Intermediate summary (may be incomplete):
    {intermediate_summary}

    Context from RAG:
    {stitched_context}
    """.strip()

    for token in generate_text_stream(final_prompt, temperature=0.2):
        yield {"type": "token", "content": token}

    yield {"type": "done"}