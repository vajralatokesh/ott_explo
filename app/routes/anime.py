from flask import Blueprint, render_template, redirect, url_for, g, request
from app.models import db, RecentlyWatched, Watchlist, ContinueWatching
from app.services.jikan_service import fetch_anime_list, fetch_anime_details, match_jikan_to_tmdb
from app.services.tmdb_service import fetch_tv_imdb_id

anime_bp = Blueprint('anime', __name__)

@anime_bp.route("/anime")
def anime_index():
    profile = g.current_profile
    if not profile:
        return redirect(url_for('main.landing'))
        
    search = request.args.get("search", "").strip()
    genre = request.args.get("genre", "").strip()
    
    anime_list = fetch_anime_list(search=search or None, genre=genre or None)
    return render_template("anime.html", anime=anime_list, search=search, genre=genre)

@anime_bp.route("/anime/<int:anime_id>")
def detail(anime_id):
    profile = g.current_profile
    if not profile:
        return redirect(url_for('main.landing'))
        
    anime = fetch_anime_details(anime_id)
    if not anime:
        return redirect(url_for('anime.anime_index'))
        
    # Multi-strategy TMDB matching
    match = match_jikan_to_tmdb(anime_id)
    tmdb_id = match["id"] if match else None
    imdb_id = fetch_tv_imdb_id(tmdb_id) if tmdb_id else ""
    
    # Retrieve continue watching progress
    progress_item = ContinueWatching.query.filter_by(
        profile_id=profile.id,
        content_id=str(anime_id),
        content_type="anime"
    ).first()
    
    default_episode = progress_item.episode if progress_item and progress_item.episode else 1
    episode_num = int(request.args.get("episode", default_episode))
    
    # Total episodes (fallbacks to Jikan detail or 24 default)
    episodes_count = anime.get("episodes") or 24
    
    # Check watchlist status
    in_watchlist = Watchlist.query.filter_by(
        profile_id=profile.id,
        content_id=str(anime_id),
        content_type="anime"
    ).first() is not None
    
    # Save viewing history
    existing_history = RecentlyWatched.query.filter_by(
        profile_id=profile.id,
        content_id=str(anime_id),
        content_type="anime"
    ).first()
    if existing_history:
        db.session.delete(existing_history)
        
    new_history = RecentlyWatched(
        profile_id=profile.id,
        content_id=str(anime_id),
        content_type="anime",
        title=anime.get("title", "Untitled Anime"),
        poster=anime.get("images", {}).get("jpg", {}).get("image_url")
    )
    db.session.add(new_history)
    db.session.commit()
    
    # Limit history list
    total_history = RecentlyWatched.query.filter_by(profile_id=profile.id).order_by(RecentlyWatched.watched_at.asc()).all()
    if len(total_history) > 15:
        db.session.delete(total_history[0])
        db.session.commit()
        
    active_server = int(request.args.get("server", 1))
    
    return render_template("anime_detail.html",
                           anime=anime,
                           tmdb_id=tmdb_id,
                           imdb_id=imdb_id,
                           episodes=episodes_count,
                           current_episode=episode_num,
                           in_watchlist=in_watchlist,
                           continue_watching=progress_item,
                           active_server=active_server)
