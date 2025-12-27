# sources/noauth_jobs.py
from __future__ import annotations
from typing import List, Iterable, Dict, Any, Set
import time, os, logging, re
import requests
from bs4 import BeautifulSoup

UA = os.getenv("SCRAPER_UA", "Mozilla/5.0 (compatible; EmployabilityBot/0.2)")
HEADERS = {"User-Agent": UA, "Accept": "application/json,text/html,*/*"}
TIMEOUT = 20

LOG = logging.getLogger("scrape")
LOG.setLevel(logging.INFO)

def _norm(s): return (s or "").strip()
def _canon(skill: str) -> str:
    s = skill.lower().strip()
    s = re.sub(r"[^a-z0-9+.#\-\s]", "", s)
    alias = {
        "py": "python", "python3": "python",
        "js": "javascript", "node.js":"nodejs", "node":"nodejs",
        "ts": "typescript", "tf":"tensorflow", "tfjs":"tensorflow",
        "sklearn":"scikit-learn", "postgres":"postgresql",
        "fast api":"fastapi", "fast-api":"fastapi"
    }
    return alias.get(s, s)

def _match(skills: List[str], texts: Iterable[str], tags: Iterable[str] = ()):
    text = " ".join([t for t in texts if t]).lower()
    tagset = {str(t).lower() for t in tags if t}
    for k in ( _canon(x) for x in skills ):
        if k and (k in text or k in tagset):
            return True
    return False

def remoteok(skills: List[str]) -> List[Dict[str, Any]]:
    url = "https://remoteok.com/api"
    out = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        for it in data[1:]:
            title = _norm(it.get("position") or it.get("title"))
            company = _norm(it.get("company"))
            location = _norm(it.get("location") or "Remote")
            url_i = _norm(it.get("url") or it.get("apply_url"))
            tags = it.get("tags") or []
            desc = _norm(it.get("description") or "")
            if title and company and url_i and _match(skills, [title, company, location, desc], tags):
                # keep longer portion of the description so the UI can show more
                snippet = desc[:4000]
                out.append({"title": title, "company": company, "location": location, "url": url_i, "source": "RemoteOK", "tags": tags, "snippet": snippet})
    except Exception as e:
        LOG.warning("RemoteOK error: %s", e)
    LOG.info("RemoteOK jobs: %d", len(out))
    return out

def remotive(skills: List[str]) -> List[Dict[str, Any]]:
    url = "https://remotive.com/api/remote-jobs"
    out = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        for it in data.get("jobs", []):
            title = _norm(it.get("title"))
            company = _norm(it.get("company_name"))
            location = _norm(it.get("candidate_required_location") or "Remote")
            url_i = _norm(it.get("url"))
            tags = list(filter(None, [it.get("job_type"), it.get("category")] + (it.get("tags") or [])))
            desc = _norm(it.get("description") or it.get("job_description") or "")
            if title and company and url_i and _match(skills, [title, company, location, desc], tags):
                snippet = desc[:4000]
                out.append({"title": title, "company": company, "location": location, "url": url_i, "source": "Remotive", "tags": tags, "snippet": snippet})
    except Exception as e:
        LOG.warning("Remotive error: %s", e)
    LOG.info("Remotive jobs: %d", len(out))
    return out

def arbeitnow(skills: List[str], pages: int = 2) -> List[Dict[str, Any]]:
    base = "https://api.arbeitnow.com/api/job-board-api"
    out = []
    try:
        for p in range(1, pages + 1):
            r = requests.get(base, headers=HEADERS, timeout=TIMEOUT, params={"page": p})
            r.raise_for_status()
            data = r.json()
            for it in data.get("data", []):
                title = _norm(it.get("title"))
                company = _norm(it.get("company_name") or it.get("company"))
                location = _norm(it.get("location") or "Remote")
                url_i = _norm(it.get("url"))
                tags = it.get("tags") or []
                desc = _norm(it.get("description") or "")
                if title and company and url_i and _match(skills, [title, company, location, desc], tags):
                    snippet = desc[:4000]
                    out.append({"title": title, "company": company, "location": location, "url": url_i, "source": "Arbeitnow", "tags": tags, "snippet": snippet})
            time.sleep(0.7)
    except Exception as e:
        LOG.warning("Arbeitnow error: %s", e)
    LOG.info("Arbeitnow jobs: %d", len(out))
    return out

def weworkremotely(skills: List[str], max_pages: int = 1) -> List[Dict[str, Any]]:
    # HTML scraping — check robots/ToS first.
    query = "+".join([_canon(s).replace(" ", "+") for s in skills if s.strip()])
    if not query:
        return []
    base = "https://weworkremotely.com/remote-jobs/search"
    out = []
    try:
        for page in range(1, max_pages+1):
            params = {"term": query}
            if page > 1: params["page"] = page
            r = requests.get(base, headers=HEADERS, timeout=TIMEOUT, params=params)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            for li in soup.select("section.jobs ul li"):
                a = li.find("a", href=True)
                if not a: continue
                href = a["href"]
                # skip promo / view-all blocks
                if "/remote-jobs/" not in href: continue
                title_el = li.find("span", {"class": "title"})
                company_el = li.find("span", {"class": "company"})
                region_el = li.find("span", {"class": "region"})
                title = _norm(title_el.text if title_el else a.get("title",""))
                company = _norm(company_el.text if company_el else "")
                location = _norm(region_el.text if region_el else "Remote")
                url_i = "https://weworkremotely.com" + href
                tags = [t.text.strip() for t in li.select(".tag, .tags .tag") if t.text.strip()]
                teaser = " ".join(t.text.strip() for t in li.select(".tooltip, .featured") if t.text.strip())
                if title and company and _match(skills, [title, company, location, teaser], tags):
                    snippet = teaser[:4000]
                    out.append({"title": title, "company": company, "location": location, "url": url_i, "source": "WeWorkRemotely", "tags": tags, "snippet": snippet})
            time.sleep(1.0)
    except Exception as e:
        LOG.warning("WWR error: %s", e)
    LOG.info("WWR jobs: %d", len(out))
    return out

def dedupe(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Set[tuple] = set(); out = []
    for j in jobs:
        key = (j["title"].lower(), j["company"].lower(), j["location"].lower(), j["source"].lower())
        if key not in seen:
            seen.add(key); out.append(j)
    return out

def all_sources(skills: List[str]) -> List[Dict[str, Any]]:
    jobs = []
    jobs.extend(remoteok(skills))
    jobs.extend(remotive(skills))
    jobs.extend(arbeitnow(skills, pages=2))
    jobs.extend(weworkremotely(skills, max_pages=1))
    jobs = dedupe(jobs)
    LOG.info("TOTAL jobs: %d", len(jobs))
    return jobs
