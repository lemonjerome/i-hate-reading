from typing import Dict, List, Any
from .llm import generate_json


def _collection_tier(chunk_count: int) -> Dict[str, Any]:
    """Return planning floors/ceilings based on collection size."""
    if chunk_count <= 30:
        return {"min_queries": 1, "max_queries": 2, "min_top_k": 6,  "max_top_k": 12, "max_context_chunks": 12, "guidance": "small collection — 1-2 focused queries"}
    elif chunk_count <= 100:
        return {"min_queries": 2, "max_queries": 3, "min_top_k": 10, "max_top_k": 18, "max_context_chunks": 20, "guidance": "medium collection — 2-3 varied queries"}
    elif chunk_count <= 300:
        return {"min_queries": 3, "max_queries": 4, "min_top_k": 12, "max_top_k": 22, "max_context_chunks": 30, "guidance": "large collection — 3-4 diverse queries covering different angles"}
    else:
        return {"min_queries": 4, "max_queries": 5, "min_top_k": 18, "max_top_k": 28, "max_context_chunks": 40, "guidance": "very large collection — 4-5 broad, diverse queries with high recall"}


def plan_queries(question: str, chunk_count: int = 0, source_count: int = 0) -> Dict[str, Any]:
    tier = _collection_tier(chunk_count)

    collection_context = (
        f"The knowledge base has {chunk_count} chunks across {source_count} document(s). "
        f"Planning guidance: {tier['guidance']}."
    ) if chunk_count > 0 else ""

    prompt = f"""
    You are a retrieval planner for a local RAG system.
    {collection_context}
    Generate {tier['min_queries']}-{tier['max_queries']} search queries that together fully cover the question from different angles.
    Choose top_k between {tier['min_top_k']} and {tier['max_top_k']} based on how broad the question is — prefer higher values for exploratory or multi-faceted questions.

    Do the aforementioned strategies by default. But also look out for user instructions to determine the level or depth of the research.
    For example: If the User wants thorough research, take longer to plan and research. If the user only wants short, simple, or brief explanations only, use less chunks or plan shorter just to be able to asnwer faster.
    Only do these if there are clear instructions. If there are none. stick to the default.
    
    Return ONLY valid JSON with this schema, no other text:
    {{
        "queries": ["..."],
        "top_k": {tier['min_top_k']},
        "rounds": 1,
        "notes": "short optional note"
    }}

    User Question: {question}
    """.strip()

    plan = generate_json(prompt, think=False)
    if not isinstance(plan, dict):
        return {"queries": [question], "top_k": tier["min_top_k"], "rounds": 1, "notes": ""}

    queries = plan.get("queries") or [question]
    queries = [q for q in queries if isinstance(q, str) and q.strip()]
    # Enforce tier floors/ceilings
    queries = queries[:tier["max_queries"]]
    if len(queries) < tier["min_queries"]:
        queries = (queries + [question] * tier["min_queries"])[:tier["min_queries"]]

    raw_top_k = int(plan.get("top_k", tier["min_top_k"]))
    top_k = max(tier["min_top_k"], min(raw_top_k, tier["max_top_k"]))

    return {
        "queries": queries,
        "top_k": top_k,
        "rounds": 1,
        "notes": str(plan.get("notes", "")),
        "tier": tier["guidance"],
        "max_context_chunks": tier["max_context_chunks"],
    }

