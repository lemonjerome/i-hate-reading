from typing import Dict, List, Any
from .llm import generate_json

def plan_queries(question: str) -> Dict[str, Any]:
    prompt = f"""
    You are a retrieval planner for a local RAG system.
    Return ONLY valid JSON with this schema, no other text:
    {{
        "queries": ["..."],          // 2-4 focused search queries derived from the question, List of strings
        "top_k": 10,                 // suggested per-query retrieval depth (8-15), integer
        "rounds": 1,                 // 1-2, integer
        "notes": "short optional note" // string
    }}

    Here is the User Question:
    {question}
    """.strip()

    plan = generate_json(prompt)
    if not isinstance(plan, dict):
        return {"queries": [question], "top_k": 10, "rounds": 1, "notes": ""}
    queries = plan.get("queries") or [question]
    return {
        "queries": [q for q in queries if isinstance(q, str) and q.strip()][:4],
        "top_k": min(int(plan.get("top_k", 10)), 15),
        "rounds": min(int(plan.get("rounds", 1)), 2),
        "notes": str(plan.get("notes", ""))
    }

def followup_queries(question: str, intermedieate_summary: str) -> List[str]:
    prompt = f"""
        You are imporving retrieval with iterative search.
        Given the user question and what we have so far, propose up to 3 follow-up queriesto fill missing gaps.
        Return ONLY JSON, no other text:

        {{"queries: ["...", "..."]}} // List of strings

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

