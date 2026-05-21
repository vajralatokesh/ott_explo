from flask import Blueprint, jsonify, request, g
from app.models import db, ContinueWatching, SearchHistory
from app.services.tmdb_service import tmdb_request
from app.services.jikan_service import jikan_request
from datetime import datetime

api_bp = Blueprint('api', __name__)

@api_bp.route("/api/suggest")
def suggest():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
        
    results = []
    
    # 1. Query TMDB Movies
    try:
        movies = tmdb_request("/search/movie", {"query": q, "page": 1}).get("results", [])[:4]
        for m in movies:
            results.append({
                "id": m["id"],
                "title": m.get("title", ""),
                "type": "movie",
                "year": (m.get("release_date") or "")[:4],
                "poster": "https://image.tmdb.org/t/p/w92" + m["poster_path"] if m.get("poster_path") else ""
            })
    except Exception:
        pass
        
    # 2. Query TMDB TV Shows
    try:
        shows = tmdb_request("/search/tv", {"query": q, "page": 1}).get("results", [])[:4]
        for s in shows:
            results.append({
                "id": s["id"],
                "title": s.get("name", ""),
                "type": "tv",
                "year": (s.get("first_air_date") or "")[:4],
                "poster": "https://image.tmdb.org/t/p/w92" + s["poster_path"] if s.get("poster_path") else ""
            })
    except Exception:
        pass
        
    # 3. Query Jikan Anime
    try:
        anime = jikan_request(f"/anime?q={q}&limit=4").get("data", [])
        for a in anime:
            results.append({
                "id": a["mal_id"],
                "title": a.get("title", ""),
                "type": "anime",
                "year": str(a.get("year") or ""),
                "poster": a.get("images", {}).get("jpg", {}).get("image_url", "")
            })
    except Exception:
        pass
        
    return jsonify(results)

@api_bp.route("/api/progress", methods=["POST"])
def save_progress():
    profile = g.current_profile
    if not profile:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    content_id = str(data.get("content_id", "")).strip()
    content_type = str(data.get("content_type", "")).strip()
    progress = int(data.get("progress", 0))
    duration = int(data.get("duration", 0))
    season = data.get("season")
    episode = data.get("episode")
    title = str(data.get("title", "")).strip()
    poster = str(data.get("poster", "")).strip()
    
    if not content_id or not content_type:
        return jsonify({"success": False, "message": "Invalid parameters"}), 400
        
    # Check if user has watched > 95% of media. If so, remove continue watching entry (completed)
    if duration > 0 and (progress / duration) > 0.95:
        existing = ContinueWatching.query.filter_by(
            profile_id=profile.id,
            content_id=content_id,
            content_type=content_type
        ).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
        return jsonify({"success": True, "completed": True, "message": "Video marked as finished"})
        
    existing = ContinueWatching.query.filter_by(
        profile_id=profile.id,
        content_id=content_id,
        content_type=content_type
    ).first()
    
    if existing:
        existing.progress = progress
        existing.duration = duration
        if season is not None:
            existing.season = int(season)
        if episode is not None:
            existing.episode = int(episode)
        existing.updated_at = datetime.utcnow()
    else:
        # If missing titles/posters, fetch them dynamically
        if not title or not poster:
            from app.services.tmdb_service import fetch_movie_details, fetch_tv_details
            from app.services.jikan_service import fetch_anime_details
            if content_type == "movie":
                m = fetch_movie_details(content_id)
                title = m.get("title") if m else "Untitled Movie"
                poster = m.get("poster_path") if m else ""
            elif content_type == "tv":
                t = fetch_tv_details(content_id)
                title = t.get("name") if t else "Untitled Show"
                poster = t.get("poster_path") if t else ""
            elif content_type == "anime":
                a = fetch_anime_details(content_id)
                title = a.get("title") if a else "Untitled Anime"
                poster = a.get("images", {}).get("jpg", {}).get("image_url") if a else ""
                
        new_progress = ContinueWatching(
            profile_id=profile.id,
            content_id=content_id,
            content_type=content_type,
            title=title,
            poster=poster,
            progress=progress,
            duration=duration,
            season=int(season) if season is not None else None,
            episode=int(episode) if episode is not None else None
        )
        db.session.add(new_progress)
        
    db.session.commit()
    return jsonify({"success": True, "message": "Viewing progress logged successfully"})

@api_bp.route("/api/search-history", methods=["GET", "POST", "DELETE"])
def search_history():
    profile = g.current_profile
    if not profile:
        return jsonify([])
        
    if request.method == "GET":
        history = SearchHistory.query.filter_by(profile_id=profile.id).order_by(SearchHistory.searched_at.desc()).limit(10).all()
        return jsonify([h.query for h in history])
        
    elif request.method == "POST":
        data = request.get_json() or {}
        q = str(data.get("query", "")).strip()
        if not q or len(q) < 2:
            return jsonify({"success": False})
            
        # Avoid duplicate search log for profile
        existing = SearchHistory.query.filter_by(profile_id=profile.id, query=q).first()
        if existing:
            db.session.delete(existing)
            
        new_log = SearchHistory(profile_id=profile.id, query=q)
        db.session.add(new_log)
        db.session.commit()
        
        # Limit history records to 10
        all_logs = SearchHistory.query.filter_by(profile_id=profile.id).order_by(SearchHistory.searched_at.asc()).all()
        if len(all_logs) > 10:
            db.session.delete(all_logs[0])
            db.session.commit()
            
        return jsonify({"success": True})
        
    elif request.method == "DELETE":
        SearchHistory.query.filter_by(profile_id=profile.id).delete()
        db.session.commit()
        return jsonify({"success": True})
