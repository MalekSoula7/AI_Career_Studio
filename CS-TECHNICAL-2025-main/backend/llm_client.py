from __future__ import annotations
import json
import os
from typing import Any, Dict, List

from openai import OpenAI


_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY or OPENAI_API_KEY must be set")
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
    return _client


def analyze_resume_with_llm(raw_text: str) -> Dict[str, Any]:
    """Call OpenRouter LLM to analyze a resume and return structured JSON.

    The model is instructed to respond with a single JSON object containing:
        - structured: candidate info, skills, education, experience, roles, soft skills
        - review: resume review (ats_score, gaps, strengths, weaknesses, suggestions)
        - career_report: recommended roles, learning plan, and market insights
    """
    client = get_client()

    system_prompt = (
        "You are a career coach and ATS resume expert. "
        "Given the raw text of a CV and optionally some interview and market context, "
        "you MUST respond with a single JSON object only, no markdown, no explanation. "
        "The JSON schema is exactly: "
        "{ "
        "\"structured\": { "
        "  \"candidate\": {\"name\": string, \"email\": string, \"phone\": string}, "
        "  \"skills_hard\": string[], "
        "  \"skills_soft\": string[], "
        "  \"education\": [{\"institution\": string, \"degree\": string, \"field\": string, \"start_year\": number|null, \"end_year\": number|null, \"location\": string}], "
        "  \"experience\": [{\"title\": string, \"company\": string, \"location\": string, \"start\": string, \"end\": string, \"bullets\": string[]}], "
        "  \"roles\": string[], "
        "  \"location\": string, \"region\": string "
        "}, "
        "\"review\": { "
        "  \"ats_score\": number, "
        "  \"summary\": string, "
        "  \"strengths\": string[], "
        "  \"weaknesses\": string[], "
        "  \"gaps\": string[], "
        "  \"suggestions\": string[] "
        "}, "
        "\"career_report\": { "
        "  \"summary\": string, "
        "  \"six_month_focus\": { "
        "    \"headline\": string, "
        "    \"themes\": string[], "
        "    \"target_roles\": string[] "
        "  }, "
        "  \"target_roles\": [{\"role\": string, \"fit_score\": number, \"why\": string}], "
        "  \"skills_to_double_down\": string[], "
        "  \"skills_to_learn\": string[], "
        "  \"certifications\": string[], "
        "  \"learning_plan\": [{\"month\": number, \"focus\": string, \"actions\": string[]}], "
        "  \"market_insights\": {\"target_regions\": string[], \"hot_skills\": string[], \"notes\": string}, "
        "  \"interview_tips\": string[], "
        "  \"narrative_summary\": string "
        "} "
        "}. "
        "Return ONLY this JSON, nothing else."
    )

    user_prompt = (
        "Here is the raw text of a candidate resume. "
        "You are also helping the candidate plan the next 6 months: "
        "which roles they should aim for, which skills to deepen, which new tools to learn, "
        "and which certifications or projects would strengthen their profile in MENA/SSA-friendly tech markets. "
        "Focus on realistic, concrete steps, not generic advice.\n\n" + raw_text
    )

    print(f"[llm_client] Calling LLM, raw_text length={len(raw_text)}")

    completion = client.chat.completions.create(
        model="meta-llama/llama-3.3-70b-instruct:free",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = completion.choices[0].message.content or "{}"
    print(f"[llm_client] Raw LLM response snippet: {content[:200]}...")

    # Clean up markdown code fences if present
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # Remove first fence line (```json or ```)
        cleaned = "\n".join(lines[1:])
    if cleaned.endswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[:-1])
    cleaned = cleaned.strip()

    # Try direct JSON parse first
    try:
        data = json.loads(cleaned)
        print(f"[llm_client] Successfully parsed JSON with keys: {list(data.keys())}")
        return data
    except Exception as e:
        print(f"[llm_client] JSON parse failed (first attempt): {e}")

    # Some models append commentary after JSON. Try to cut at last closing brace.
    last_brace = cleaned.rfind("}")
    if last_brace != -1:
        candidate = cleaned[: last_brace + 1].strip()
        try:
            data = json.loads(candidate)
            print("[llm_client] Parsed JSON after trimming trailing text.")
            return data
        except Exception as e2:
            print(f"[llm_client] Trim-then-parse still failed: {e2}")

    # Fallback: return raw content so frontend can at least show something
    return {"raw_response": content}


def analyze_resume_review_llm(raw_text: str) -> Dict[str, Any]:
    """Call OpenRouter LLM to produce a resume review with detailed scoring.

    Expected JSON schema:
    {
      "overall": { "score": number, "label": string, "out_of": 100 },
      "breakdown": {
        "skills_coverage": number,
        "structure_formatting": number,
        "clarity_impact": number,
        "regional_relevance": number
      },
      "strengths": string[],
      "areas_for_improvement": string[],
      "notes": string
    }
    """
    client = get_client()

    system_prompt = (
        "You are an ATS and resume review expert. "
        "Given a resume's raw text, return ONLY a single JSON object that follows this exact schema: "
        "{ "
        "  \"overall\": { \"score\": number, \"label\": string, \"out_of\": 100 }, "
        "  \"breakdown\": { "
        "    \"skills_coverage\": number, "
        "    \"structure_formatting\": number, "
        "    \"clarity_impact\": number, "
        "    \"regional_relevance\": number "
        "  }, "
        "  \"strengths\": string[], "
        "  \"areas_for_improvement\": string[], "
        "  \"notes\": string "
        "}. "
        "Scoring rules: all scores are integers 0–100. "
        "Map overall.label by score: 90–100=\"Excellent\", 75–89=\"Good\", 60–74=\"Fair\", 0–59=\"Needs Improvement\". "
        "Consider the resume's content for skills coverage, structure/formatting quality, clarity/impact of bullets, and regional relevance of experience and education. "
        "Return ONLY valid JSON, no extra text."
    )

    user_prompt = (
        "Resume raw text follows. Review it per the schema.\n\n" + raw_text
    )

    print(f"[llm_client] Calling LLM for review, raw_text length={len(raw_text)}")
    completion = client.chat.completions.create(
        model="meta-llama/llama-3.3-70b-instruct:free",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = completion.choices[0].message.content or "{}"
    print(f"[llm_client] Review LLM response snippet: {content[:200]}...")

    # Some models wrap JSON in markdown fences like ```json ... ```; strip them.
    cleaned = content.strip()
    if cleaned.startswith("```"):
        # remove first fence line
        cleaned = "\n".join(cleaned.splitlines()[1:])
    if cleaned.endswith("```"):
        cleaned = "\n".join(cleaned.splitlines()[:-1])
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except Exception:
        data = {"raw_response": content}
    return data


def refine_resume_for_job_llm(raw_text: str, job: Dict[str, Any]) -> Dict[str, Any]:
    """Given a resume's raw_text and a job object, return tailored resume guidance.

    Returns JSON:
    {
      "summary_suggestion": string,
      "keywords_to_emphasize": string[],
      "experience_bullets": string[],
      "skills_to_add": string[],
      "notes": string
    }
    """
    client = get_client()

    system_prompt = (
        "You are an expert resume tailor for ATS. Return ONLY JSON. "
        "Given a candidate resume and a target job (title, company, tags, snippet), "
        "produce specific, concise tailoring suggestions following this exact schema: "
        "{ \n"
        "  \"summary_suggestion\": string, \n"
        "  \"keywords_to_emphasize\": string[], \n"
        "  \"experience_bullets\": string[], \n"
        "  \"skills_to_add\": string[], \n"
        "  \"notes\": string \n"
        "}."
    )

    user_prompt = (
        "Resume (raw text):\n" + raw_text + "\n\n" +
        "Target job JSON (title, company, tags, snippet):\n" + json.dumps(job) + "\n\n" +
        "Return ONLY valid JSON per schema."
    )

    completion = client.chat.completions.create(
        model="meta-llama/llama-3.3-70b-instruct:free",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = completion.choices[0].message.content or "{}"
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = "\n".join(cleaned.splitlines()[1:])
    if cleaned.endswith("```"):
        cleaned = "\n".join(cleaned.splitlines()[:-1])
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except Exception:
        return {"raw_response": content}


def generate_cover_letter_llm(raw_text: str, job: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a concise, personalized cover letter for the target job.

    Returns JSON: { "cover_letter": string }
    """
    client = get_client()
    system_prompt = (
        "You are a career assistant. Return ONLY JSON. "
        "Write a concise, personalized cover letter (250-350 words) tailored to the target job, "
        "grounded in the candidate's resume. Use a professional yet warm tone. "
        "Schema: { \"cover_letter\": string }."
    )
    user_prompt = (
        "Resume (raw text):\n" + raw_text + "\n\n" +
        "Target job JSON (title, company, tags, snippet):\n" + json.dumps(job)
    )

    completion = client.chat.completions.create(
        model="meta-llama/llama-3.3-70b-instruct:free",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = completion.choices[0].message.content or "{}"
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = "\n".join(cleaned.splitlines()[1:])
    if cleaned.endswith("```"):
        cleaned = "\n".join(cleaned.splitlines()[:-1])
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except Exception:
        return {"raw_response": content}
