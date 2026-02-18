from typing import Dict, List, Any
from .llm import generate_json

def plan_queries(question: str) -> Dict[str, Any]:
    prompt = f"""
    You are a retrieval planner for a local RAG system.
    Return ONLY valid JSON with this schema, no other text:
    {{
        "queries": ["..."],
        "top_k": 10,
        "rounds": 1,
        "notes": "short optional note"
    }}

    User Question: {question}
    """.strip()

    plan = generate_json(prompt)
    if not isinstance(plan, dict):
        return {"queries": [question], "top_k": 10, "rounds": 1, "notes": ""}
    queries = plan.get("queries") or [question]
    return {
        "queries": [q for q in queries if isinstance(q, str) and q.strip()][:4],
        "top_k": min(int(plan.get("top_k", 10)), 15),
        "rounds": min(int(plan.get("rounds", 1)), 2),
        "notes": str(plan.get("notes", "")),
    }


def followup_queries(question: str, intermediate_summary: str) -> List[str]:
    prompt = f"""
    Propose up to 3 follow-up search queries to fill gaps.
    Return ONLY JSON: {{"queries": ["...", "..."]}}

    Question: {question}

    Summary so far: {intermediate_summary}
    """.strip()

    obj = generate_json(prompt)
    qs = []
    if isinstance(obj, dict):
        qs = obj.get("queries") or []
    return [q for q in qs if isinstance(q, str) and q.strip()]

