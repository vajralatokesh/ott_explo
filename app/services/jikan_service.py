import time
import requests
from flask import current_app
from app import cache
from app.services.tmdb_service import tmdb_request

JIKAN_BASE_URL = "https://api.jikan.moe/v4"
_last_request_time = 0

def jikan_request(path):
    """
    Execute Jikan requests with strict local rate-limiting throttle (330ms minimum between calls)
    """
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < 0.33:
        time.sleep(0.33 - elapsed)
        
    url = f"{JIKAN_BASE_URL}{path}"
    _last_request_time = time.time()
    
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 429: # Rate limited
                time.sleep(1.5)
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            if attempt == 2:
                current_app.logger.error(f"Jikan API fail [{path}]: {e}")
                return {}
            time.sleep(1.0)
    return {}

@cache.memoize(timeout=3600)
def fetch_anime_list(search=None, genre=None, page=1, limit=24):
    if search:
        # Search Anime
        data = jikan_request(f"/anime?q={search}&page={page}&limit={limit}")
    else:
        # Top Anime
        data = jikan_request(f"/top/anime?page={page}&limit={limit}")
        
    anime_list = data.get("data", [])
    if genre:
        # Filter local genre names
        anime_list = [a for a in anime_list
                      if any(genre.lower() == g["name"].lower() for g in a.get("genres", []))]
    return anime_list

@cache.memoize(timeout=3600)
def fetch_anime_details(mal_id):
    return jikan_request(f"/anime/{mal_id}").get("data")

@cache.memoize(timeout=86400) # cache matching mappings for 24 hours
def match_jikan_to_tmdb(mal_id):
    """
    Highly refined Jikan MAL to TMDB ID cross-matching engine.
    Fetches anime details, extracts Romaji, English and Synonym titles, 
    and searches TMDB TV & Movie catalogs with fuzzy selection.
    """
    anime = fetch_anime_details(mal_id)
    if not anime:
        return None
        
    titles_to_try = []
    eng = (anime.get("title_english") or "").strip()
    romaji = (anime.get("title") or "").strip()
    
    if eng:
        titles_to_try.append((eng, "tv"))
        titles_to_try.append((eng, "movie"))
    if romaji and romaji != eng:
        titles_to_try.append((romaji, "tv"))
        titles_to_try.append((romaji, "movie"))
        
    for syn in (anime.get("title_synonyms") or []):
        s = (syn or "").strip()
        if s and s not in [t[0] for t in titles_to_try]:
            titles_to_try.append((s, "tv"))
            titles_to_try.append((s, "movie"))
            
    # Try searching TMDB with each variation
    for title, media_type in titles_to_try:
        path = f"/search/{media_type}"
        results = tmdb_request(path, {"query": title}).get("results", [])
        
        # Look for a strong match
        for r in results:
            tname = r.get("name") if media_type == "tv" else r.get("title")
            if not tname:
                continue
            
            # Substring score / fuzzy match
            if title.lower() in tname.lower() or tname.lower() in title.lower():
                return {
                    "id": r["id"],
                    "media_type": media_type,
                    "title": tname,
                    "poster_path": r.get("poster_path")
                }
                
        # Retry by stripping suffixes (e.g. "Attack on Titan: The Final Season" -> "Attack on Titan")
        base_title = title.split(":")[0].split(" - ")[0].strip()
        if base_title != title and len(base_title) > 2:
            results = tmdb_request(path, {"query": base_title}).get("results", [])
            for r in results:
                tname = r.get("name") if media_type == "tv" else r.get("title")
                if tname and (base_title.lower() in tname.lower() or tname.lower() in base_title.lower()):
                    return {
                        "id": r["id"],
                        "media_type": media_type,
                        "title": tname,
                        "poster_path": r.get("poster_path")
                    }
                    
    return None
