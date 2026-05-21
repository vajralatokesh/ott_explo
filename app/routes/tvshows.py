from flask import Blueprint, render_template, redirect, url_for, g, request
from app.models import db, RecentlyWatched, Watchlist, ContinueWatching
from app.services.tmdb_service import fetch_tv_shows, fetch_tv_details, fetch_tv_imdb_id, fetch_tv_season, fetch_similar_tv

tvshows_bp = Blueprint('tvshows', __name__)

@tvshows_bp.route("/tvshows")
def tvshows_index():
    profile = g.current_profile
    if not profile:
        return redirect(url_for('main.landing'))
        
    search = request.args.get("search", "").strip()
    language = request.args.get("language", "").strip()
    genre = request.args.get("genre", "").strip()
    sort_by = request.args.get("sort_by", "").strip()
    
    # Kids safety enforcement
    if profile.is_kids:
        if genre:
            if genre not in ["16", "10762"]:
                genre = "16,10762"
        else:
            genre = "16,10762"
            
    res = fetch_tv_shows(search=search or None, 
                         language=language or None, 
                         genre=genre or None, 
                         sort_by=sort_by or None)
                         
    tv_list = res.get("results", [])
    watchlist = Watchlist.query.filter_by(profile_id=profile.id).all()
    
    return render_template("tvshows.html", 
                           tv_list=tv_list, 
                           search=search, 
                           language=language, 
                           genre=genre, 
                           sort_by=sort_by,
                           watchlist=watchlist)

@tvshows_bp.route("/tv/<int:tv_id>")
def detail(tv_id):
    profile = g.current_profile
    if not profile:
        return redirect(url_for('main.landing'))
        
    tv = fetch_tv_details(tv_id)
    if not tv:
        return redirect(url_for('main.dashboard'))
        
    imdb_id = fetch_tv_imdb_id(tv_id)
    
    # Check if there is viewing progress
    progress_item = ContinueWatching.query.filter_by(
        profile_id=profile.id,
        content_id=str(tv_id),
        content_type="tv"
    ).first()
    
    # Load saved season & episode or fall back to 1
    default_season = progress_item.season if progress_item and progress_item.season else 1
    default_episode = progress_item.episode if progress_item and progress_item.episode else 1
    
    season_num = int(request.args.get("season", default_season))
    episode_num = int(request.args.get("episode", default_episode))
    
    season_data = fetch_tv_season(tv_id, season_num)
    similar = fetch_similar_tv(tv_id)
    
    # Watchlist status
    in_watchlist = Watchlist.query.filter_by(
        profile_id=profile.id,
        content_id=str(tv_id),
        content_type="tv"
    ).first() is not None
    
    # Save to history
    existing_history = RecentlyWatched.query.filter_by(
        profile_id=profile.id,
        content_id=str(tv_id),
        content_type="tv"
    ).first()
    if existing_history:
        db.session.delete(existing_history)
        
    new_history = RecentlyWatched(
        profile_id=profile.id,
        content_id=str(tv_id),
        content_type="tv",
        title=tv.get("name", "Untitled TV Show"),
        poster=tv.get("poster_path")
    )
    db.session.add(new_history)
    db.session.commit()
    
    # Limit history to 15
    total_history = RecentlyWatched.query.filter_by(profile_id=profile.id).order_by(RecentlyWatched.watched_at.asc()).all()
    if len(total_history) > 15:
        db.session.delete(total_history[0])
        db.session.commit()
        
    active_server = int(request.args.get("server", 1))
    
    return render_template("tv_detail.html",
                           tv=tv,
                           imdb_id=imdb_id,
                           season=season_data,
                           current_season=season_num,
                           current_episode=episode_num,
                           similar=similar,
                           in_watchlist=in_watchlist,
                           continue_watching=progress_item,
                           active_server=active_server)
