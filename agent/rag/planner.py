from typing import Dict, List, Any
from .llm import generate_json

def plan_queries(question: str) -> Dict[str, Any]:
    prompt = f"""
    You are a retrieval planner for a local RAG system.
    Return ONLY valid JSON with this schema, no other text:
    {{
        "queries": ["..."],
        "top_k": 12,
        "rounds": 2,
        "notes": "short optional note" 
    }}

    Here is the User Question:
    {question}
    """.strip()

    plan = generate_json(prompt)
    if not isinstance(plan, dict):
        return {"queries": [question], "top_k": 12, "rounds": 2, "notes": ""}
    queries = plan.get("queries") or [question]
    return {
        "queries": [q for q in queries if isinstance(q, str) and q.strip()],
        "top_k": int(plan.get("top_k", 12)),
        "rounds": int(plan.get("rounds", 2)),
        "notes": str(plan.get("notes", ""))
    }

def followup_queries(question: str, intermedieate_summary: str) -> List[str]:
    prompt = f"""
        You are imporving retrieval with iterative search.
        Given the user question and what we have so far, propose up to 3 follow-up queriesto fill missing gaps.
        Return ONLY JSON, no other text:

        {{"queries: ["...", "..."]}}

        Here is the User Question:
        {question}

        What we have so far (summary):
        {intermedieate_summary}
    """.strip()

    obj = generate_json(prompt)
    qs = []
    if isinstance(obj, dict):
        qs = obj.get("queries") or []
    return [q for q in qs if isinstance(q, str) and q.strip()]

