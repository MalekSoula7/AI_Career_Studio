# interview_insights.py
import re
from statistics import mean

def _text_strengths(answer: str) -> list[str]:
    """Find textual strengths inside an answer."""
    strengths = []
    if len(answer.split()) > 50:
        strengths.append("Provides detailed, in-depth responses")
    if re.search(r"\b(team|collaborat|lead|mentor)\b", answer, re.I):
        strengths.append("Demonstrates teamwork or leadership")
    if re.search(r"\b(achiev|deliver|impact|result|increase|reduce)\b", answer, re.I):
        strengths.append("Highlights measurable achievements")
    if re.search(r"\b(problem|solve|debug|design)\b", answer, re.I):
        strengths.append("Shows analytical and problem-solving skills")
    return strengths

def _text_weaknesses(answer: str) -> list[str]:
    weaknesses = []
    if len(answer.split()) < 15:
        weaknesses.append("Answers are too short; may lack elaboration")
    if not re.search(r"\b(i|we)\b", answer.lower()):
        weaknesses.append("Lacks personal engagement or examples")
    if re.search(r"\bumm|uhh|maybe|sort of|kind of\b", answer.lower()):
        weaknesses.append("Hesitation words reduce confidence")
    return weaknesses

def generate_insights(scores: dict, transcripts: list[str], face_summary: dict) -> dict:
    """Produce strengths/weaknesses and an overall engagement score."""
    text_strengths, text_weaknesses = [], []

    # --- textual content analysis ---
    for a in transcripts:
        text_strengths += _text_strengths(a)
        text_weaknesses += _text_weaknesses(a)

    # --- aggregate quantitative data ---
    avg_score = mean(scores.values()) if scores else 0.5
    attn = face_summary.get("overall", {}).get("avg_attention", 0.5)
    smile = face_summary.get("overall", {}).get("smile_ratio", 0.0)
    presence = face_summary.get("overall", {}).get("presence_ratio", 0.5)

    overall_score = round(0.5*avg_score + 0.3*attn + 0.2*presence, 2)

    # --- behavioral strengths/weaknesses ---
    if attn > 0.7:
        text_strengths.append("Maintains good eye contact and focus")
    else:
        text_weaknesses.append("Shows fluctuating attention or camera avoidance")

    # Deduplicate while preserving order
    def uniq(seq): seen=set(); return [x for x in seq if not (x in seen or seen.add(x))]
    strengths = uniq(text_strengths)
    weaknesses = uniq(text_weaknesses)

    summary = {
        "overall_score": overall_score,
        "strengths": strengths[:5],
        "weaknesses": weaknesses[:5]
    }
    return summary
