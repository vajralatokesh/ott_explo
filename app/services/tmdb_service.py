import os
import time
import requests
from flask import current_app
from app import cache

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "b8a45c0e4399cb242e0c6a486ca2542c")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

def tmdb_request(path, params=None, retries=3, backoff_factor=0.5):
    """
    Core TMDB request helper with caching and robust retry mechanisms
    """
    p = {"api_key": TMDB_API_KEY}
    if params:
        p.update(params)
        
    url = f"{TMDB_BASE_URL}{path}"
    
    # Try multiple times for network resiliency
    for attempt in range(retries):
        try:
            r = requests.get(url, params=p, timeout=8)
            
            # Handle rate limiting (HTTP 429)
            if r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", 1))
                time.sleep(retry_after)
                continue
                
            r.raise_for_status()
            return r.json()
            
        except requests.exceptions.RequestException as e:
            if attempt == retries - 1:
                current_app.logger.error(f"TMDB API failure [{path}] after {retries} retries: {e}")
                return {}
            time.sleep(backoff_factor * (2 ** attempt))
    return {}

@cache.memoize(timeout=3600) # cache results for 1 hour
def fetch_movies(search=None, language=None, genre=None, year=None, sort_by=None, decade=None, page=1):
    """
    Comprehensive movie search & discover wrapper
    """
    if search:
        return tmdb_request("/search/movie", {"query": search, "page": page, "include_adult": False})
    
    sort = sort_by or "popularity.desc"
    params = {"sort_by": sort, "include_adult": False, "include_video": False, "page": page}
    
    if language:
        params["with_original_language"] = language
    if genre:
        params["with_genres"] = genre
    if year:
        params["primary_release_year"] = year
    if decade:
        s = int(decade)
        params["primary_release_date.gte"] = f"{s}-01-01"
        params["primary_release_date.lte"] = f"{s+9}-12-31"
        
    return tmdb_request("/discover/movie", params)

@cache.memoize(timeout=3600)
def fetch_movie_details(movie_id):
    return tmdb_request(f"/movie/{movie_id}")

@cache.memoize(timeout=3600)
def fetch_movie_imdb_id(movie_id):
    return tmdb_request(f"/movie/{movie_id}/external_ids").get("imdb_id", "")

@cache.memoize(timeout=3600)
def fetch_movie_videos(movie_id):
    return tmdb_request(f"/movie/{movie_id}/videos").get("results", [])

@cache.memoize(timeout=3600)
def fetch_tv_shows(search=None, language=None, genre=None, sort_by=None, page=1):
    if search:
        return tmdb_request("/search/tv", {"query": search, "page": page})
        
    sort = sort_by or "popularity.desc"
    params = {"sort_by": sort, "page": page}
    
    if language:
        params["with_original_language"] = language
    if genre:
        params["with_genres"] = genre
        
    return tmdb_request("/discover/tv", params)

@cache.memoize(timeout=3600)
def fetch_tv_details(tv_id):
    return tmdb_request(f"/tv/{tv_id}")

@cache.memoize(timeout=3600)
def fetch_tv_imdb_id(tv_id):
    return tmdb_request(f"/tv/{tv_id}/external_ids").get("imdb_id", "")

@cache.memoize(timeout=3600)
def fetch_tv_season(tv_id, season_number):
    return tmdb_request(f"/tv/{tv_id}/season/{season_number}")

@cache.memoize(timeout=3600)
def fetch_similar_movies(movie_id):
    return tmdb_request(f"/movie/{movie_id}/similar").get("results", [])[:12]

@cache.memoize(timeout=3600)
def fetch_similar_tv(tv_id):
    return tmdb_request(f"/tv/{tv_id}/similar").get("results", [])[:12]

@cache.memoize(timeout=3600)
def fetch_trending_all(media_type="movie", time_window="week"):
    """
    Get top trending movie, tv, or all items for billboard showcases
    """
    return tmdb_request(f"/trending/{media_type}/{time_window}").get("results", [])
