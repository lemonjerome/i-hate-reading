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

    plan = generate_json(prompt, think=False)
    if not isinstance(plan, dict):
        return {"queries": [question], "top_k": 10, "rounds": 1, "notes": ""}
    queries = plan.get("queries") or [question]
    return {
        "queries": [q for q in queries if isinstance(q, str) and q.strip()][:4],
        "top_k": min(int(plan.get("top_k", 10)), 15),
        "rounds": 1,  # force single round for speed
        "notes": str(plan.get("notes", "")),
    }

