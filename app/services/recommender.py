from collections import Counter
from app.models import Watchlist, RecentlyWatched
from app.services.tmdb_service import tmdb_request, fetch_trending_all
from app.services.jikan_service import fetch_anime_list

# Genre name mapping for TMDB genre IDs
TMDB_MOVIE_GENRES = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History",
    27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Sci-Fi",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"
}

TMDB_TV_GENRES = {
    10759: "Action & Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    99: "Documentary", 18: "Drama", 10751: "Family", 9648: "Mystery",
    10762: "Kids", 10763: "News", 10764: "Reality", 10765: "Sci-Fi & Fantasy",
    10766: "Soap", 10767: "Talk", 10768: "War & Politics", 37: "Western"
}

def get_profile_recommendations(profile):
    """
    Personalized AI recommendation engine.
    Extracts preferred genres from watchlist and viewing history,
    scores candidate content, and returns custom personalized titles.
    """
    # 1. Gather all content from profile list and history
    wl_items = Watchlist.query.filter_by(profile_id=profile.id).all()
    hist_items = RecentlyWatched.query.filter_by(profile_id=profile.id).all()
    
    # Track existing IDs to avoid recommending already watched/added items
    existing_ids = {f"{item.content_type}_{item.content_id}" for item in wl_items}
    existing_ids.update({f"{item.content_type}_{item.content_id}" for item in hist_items})
    
    # 2. If profile is brand new or lacks logs, return trending highlights
    if not wl_items and not hist_items:
        fallback_trends = fetch_trending_all("all", "week")[:12]
        formatted = []
        for item in fallback_trends:
            mtype = item.get("media_type", "movie")
            title = item.get("title") or item.get("name") or "Cinematic Pick"
            formatted.append({
                "id": item["id"],
                "content_type": mtype,
                "title": title,
                "poster": item.get("poster_path"),
                "rating": item.get("vote_average", 0),
                "reason": "Popular choice this week"
            })
        return formatted
        
    # 3. Compile all genres from watchlist and history to identify favorites
    genre_pool = []
    
    # Inspect movie and TV entries in watchlist and history
    for item in (wl_items + hist_items):
        if item.content_type == "movie":
            details = tmdb_request(f"/movie/{item.content_id}")
            if details:
                genre_pool.extend([g["id"] for g in details.get("genres", [])])
        elif item.content_type == "tv":
            details = tmdb_request(f"/tv/{item.content_id}")
            if details:
                genre_pool.extend([g["id"] for g in details.get("genres", [])])
        elif item.content_type == "anime":
            # Map Jikan genres to basic movie/TV categories
            genre_pool.extend([16]) # 16 = Animation
            
    # Find top 3 favorite genre IDs
    genre_counts = Counter(genre_pool)
    top_genres = [g_id for g_id, _ in genre_counts.most_common(3)]
    
    recommended = []
    
    # 4. Query TMDB Discover using favorite genre filters
    for idx, gid in enumerate(top_genres):
        gname = TMDB_MOVIE_GENRES.get(gid) or TMDB_TV_GENRES.get(gid) or "Custom Interest"
        
        # Search movies for this genre
        movie_results = tmdb_request("/discover/movie", {
            "with_genres": gid,
            "sort_by": "popularity.desc",
            "vote_average.gte": 7.0,
            "page": 1
        }).get("results", [])[:4]
        
        for m in movie_results:
            key = f"movie_{m['id']}"
            if key not in existing_ids and len(recommended) < 12:
                recommended.append({
                    "id": m["id"],
                    "content_type": "movie",
                    "title": m.get("title", "Untitled Movie"),
                    "poster": m.get("poster_path"),
                    "rating": m.get("vote_average", 0),
                    "reason": f"Top pick in {gname}"
                })
                existing_ids.add(key)
                
        # Search TV shows for this genre
        tv_results = tmdb_request("/discover/tv", {
            "with_genres": gid,
            "sort_by": "popularity.desc",
            "vote_average.gte": 7.0,
            "page": 1
        }).get("results", [])[:3]
        
        for t in tv_results:
            key = f"tv_{t['id']}"
            if key not in existing_ids and len(recommended) < 12:
                recommended.append({
                    "id": t["id"],
                    "content_type": "tv",
                    "title": t.get("name", "Untitled Show"),
                    "poster": t.get("poster_path"),
                    "rating": t.get("vote_average", 0),
                    "reason": f"Recommended TV in {gname}"
                })
                existing_ids.add(key)
                
    # 5. Add custom anime suggestions if user enjoys Animation/Anime
    if 16 in top_genres or any(item.content_type == "anime" for item in (wl_items + hist_items)):
        anime_hits = fetch_anime_list()[:6]
        for a in anime_hits:
            key = f"anime_{a['mal_id']}"
            if key not in existing_ids and len(recommended) < 12:
                recommended.append({
                    "id": a["mal_id"],
                    "content_type": "anime",
                    "title": a.get("title"),
                    "poster": a.get("images", {}).get("jpg", {}).get("image_url"),
                    "rating": a.get("score") or 0,
                    "reason": "Top Animé pick for you"
                })
                existing_ids.add(key)
                
    # 6. Ensure at least 6 recommendations by padding with top trending if needed
    if len(recommended) < 6:
        extra_trends = fetch_trending_all("movie", "week")
        for item in extra_trends:
            key = f"movie_{item['id']}"
            if key not in existing_ids and len(recommended) < 12:
                recommended.append({
                    "id": item["id"],
                    "content_type": "movie",
                    "title": item.get("title", "Cinematic Hit"),
                    "poster": item.get("poster_path"),
                    "rating": item.get("vote_average", 0),
                    "reason": "Highly Popular"
                })
                existing_ids.add(key)
                
    return recommended
