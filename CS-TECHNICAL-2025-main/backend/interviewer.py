from typing import Dict, Any, List, Optional

BASE_QUESTIONS = [
    {"id": "q1", "text": "Walk me through your most impactful project.", "topic": "experience"},
    {"id": "q2", "text": "Tell me about a time you improved performance. How did you measure it?", "topic": "impact"},
    {"id": "q3", "text": "Pick one key skill on your resume and go deep. What do you actually know?", "topic": "skill"},
    {"id": "q4", "text": "Describe a failure. What did you learn and change next time?", "topic": "learning"}
]

def generate_questions(parsed: Dict[str, Any], role: Optional[str]) -> List[Dict[str, str]]:
    qs = BASE_QUESTIONS.copy()
    if role:
        qs.append({"id": "q5", "text": f"What makes you a fit for {role}?", "topic": "fit"})
    return qs

def score_answer(answer: str) -> float:
    base = 0.3 + 0.01 * min(50, len(answer.split()))
    if any(x in answer for x in ["%", "users", "ms", "latency", "revenue", "cost"]):
        base += 0.2
    if any(x in answer.lower() for x in ["situation", "task", "action", "result"]):
        base += 0.2
    return round(min(1.0, base), 2)
