from flask import Blueprint, render_template, redirect, url_for, g, request
from app.models import db, RecentlyWatched, Watchlist, ContinueWatching
from app.services.tmdb_service import fetch_movie_details, fetch_movie_imdb_id, fetch_movie_videos, fetch_similar_movies

movies_bp = Blueprint('movies', __name__)

@movies_bp.route("/movie/<int:movie_id>")
def detail(movie_id):
    profile = g.current_profile
    if not profile:
        return redirect(url_for('main.landing'))
        
    movie = fetch_movie_details(movie_id)
    if not movie:
        return redirect(url_for('main.dashboard'))
        
    imdb_id = fetch_movie_imdb_id(movie_id)
    videos = fetch_movie_videos(movie_id)
    
    # Extract trailer URL key
    trailer = next((v for v in videos if v.get("type") == "Trailer" and v.get("site") == "YouTube"), None)
    
    # Similar movie recommendations
    similar = fetch_similar_movies(movie_id)
    
    # Check if this item is in the profile's watchlist
    in_watchlist = Watchlist.query.filter_by(
        profile_id=profile.id, 
        content_id=str(movie_id), 
        content_type="movie"
    ).first() is not None
    
    # Save to profile's recently watched history
    existing_history = RecentlyWatched.query.filter_by(
        profile_id=profile.id,
        content_id=str(movie_id),
        content_type="movie"
    ).first()
    
    if existing_history:
        db.session.delete(existing_history) # remove old entry to move it to the top
        
    new_history = RecentlyWatched(
        profile_id=profile.id,
        content_id=str(movie_id),
        content_type="movie",
        title=movie.get("title", "Untitled Movie"),
        poster=movie.get("poster_path")
    )
    db.session.add(new_history)
    db.session.commit()
    
    # Limit history list to 15 items to preserve space
    total_history = RecentlyWatched.query.filter_by(profile_id=profile.id).order_by(RecentlyWatched.watched_at.asc()).all()
    if len(total_history) > 15:
        db.session.delete(total_history[0])
        db.session.commit()
        
    # Get continue watching progress
    continue_watching = ContinueWatching.query.filter_by(
        profile_id=profile.id,
        content_id=str(movie_id),
        content_type="movie"
    ).first()

    # Get active streaming server from request args
    active_server = int(request.args.get("server", 1))
    
    return render_template("detail.html",
                           movie=movie,
                           imdb_id=imdb_id,
                           trailer=trailer,
                           similar=similar,
                           in_watchlist=in_watchlist,
                           continue_watching=continue_watching,
                           active_server=active_server)
