from typing import Dict, Any, Optional
import requests

UA = "Mozilla/5.0 (compatible; EmployabilityBot/0.1)"
HEADERS = {"User-Agent": UA}
TIMEOUT = 15

def _github(username: Optional[str]) -> Dict[str, Any]:
    if not username:
        return {"username": "", "repos": 0, "top_langs": [], "recent_activity": []}
    try:
        r = requests.get(f"https://api.github.com/users/{username}", headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        prof = r.json()
        r2 = requests.get(f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated", headers=HEADERS, timeout=TIMEOUT)
        r2.raise_for_status()
        repos = r2.json()
        langs = {}
        for repo in repos:
            lang = repo.get("language")
            if lang:
                langs[lang] = langs.get(lang, 0) + 1
        top_langs = sorted(langs, key=langs.get, reverse=True)[:5]
        recent = [{"repo": repo["name"], "pushed_at": repo["pushed_at"]} for repo in repos[:5]]
        return {"username": username, "repos": prof.get("public_repos", len(repos)), "top_langs": top_langs, "recent_activity": recent}
    except Exception:
        return {"username": username, "repos": 0, "top_langs": [], "recent_activity": []}

def _stackoverflow(user_id: Optional[int]) -> Dict[str, Any]:
    if not user_id:
        return {"user_id": 0, "reputation": 0, "top_tags": []}
    try:
        r = requests.get(f"https://api.stackexchange.com/2.3/users/{user_id}?site=stackoverflow", headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        items = data.get("items", [])
        rep = items[0]["reputation"] if items else 0
        r2 = requests.get(f"https://api.stackexchange.com/2.3/users/{user_id}/top-tags?site=stackoverflow", headers=HEADERS, timeout=TIMEOUT)
        r2.raise_for_status()
        tags = [t["tag_name"] for t in r2.json().get("items", [])][:10]
        return {"user_id": user_id, "reputation": rep, "top_tags": tags}
    except Exception:
        return {"user_id": user_id, "reputation": 0, "top_tags": []}

def scan(github_username: Optional[str], stackoverflow_user_id: Optional[int]) -> Dict[str, Any]:
    return {
        "github": _github(github_username),
        "stackoverflow": _stackoverflow(stackoverflow_user_id)
    }
