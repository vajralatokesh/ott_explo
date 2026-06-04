from flask import Blueprint, render_template, redirect, url_for, g, request, jsonify
from app.models import db, Watchlist, RecentlyWatched
from app.services.tmdb_service import fetch_movie_details, fetch_tv_details
from app.services.jikan_service import fetch_anime_details

watchlist_bp = Blueprint('watchlist', __name__)

@watchlist_bp.route("/watchlist")
def index():
    profile = g.current_profile
    if not profile:
        return redirect(url_for('main.landing'))
        
    items = Watchlist.query.filter_by(profile_id=profile.id).order_by(Watchlist.added_at.desc()).all()
    
    # Split items by content type to support multi-tab view
    movies = [i for i in items if i.content_type == "movie"]
    tv_shows = [i for i in items if i.content_type == "tv"]
    anime = [i for i in items if i.content_type == "anime"]
    
    # Fetch profile's recently watched
    recent = RecentlyWatched.query.filter_by(profile_id=profile.id).order_by(RecentlyWatched.watched_at.desc()).limit(12).all()
    
    return render_template("watchlist.html",
                           watchlist=items,
                           movies=movies,
                           tv_shows=tv_shows,
                           anime=anime,
                           recent=recent)

@watchlist_bp.route("/watchlist/toggle", methods=["POST"])
def toggle():
    profile = g.current_profile
    if not profile:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    content_id = str(data.get("content_id", "")).strip()
    content_type = str(data.get("content_type", "")).strip() # 'movie', 'tv', 'anime'
    title = str(data.get("title", "")).strip()
    poster = str(data.get("poster", "")).strip()
    
    if not content_id or not content_type:
        return jsonify({"success": False, "message": "Missing arguments"}), 400
        
    # Check if already exists
    existing = Watchlist.query.filter_by(
        profile_id=profile.id,
        content_id=content_id,
        content_type=content_type
    ).first()
    
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"success": True, "added": False, "message": "Removed from Watchlist"})
        
    # If not exists, add to watchlist. Fetch detailed title/poster if missing
    if not title or not poster:
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
            
    new_item = Watchlist(
        profile_id=profile.id,
        content_id=content_id,
        content_type=content_type,
        title=title,
        poster=poster
    )
    db.session.add(new_item)
    db.session.commit()
    
    return jsonify({"success": True, "added": True, "message": "Added to Watchlist!"})

@watchlist_bp.route("/watchlist/remove/<int:item_id>", methods=["POST", "DELETE"])
def remove(item_id):
    profile = g.current_profile
    if not profile:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
        
    item = Watchlist.query.filter_by(id=item_id, profile_id=profile.id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"success": True, "message": "Item removed"})
        
    return jsonify({"success": False, "message": "Item not found"}), 404
