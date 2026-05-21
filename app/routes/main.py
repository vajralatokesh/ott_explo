from flask import Blueprint, render_template, redirect, url_for, request, make_response, g, jsonify, flash
from app.models import db, Profile, Watchlist, ContinueWatching, RecentlyWatched
from app.services.tmdb_service import fetch_trending_all, fetch_movies, fetch_tv_shows, tmdb_request
from app.services.jikan_service import fetch_anime_list
from app.services.recommender import get_profile_recommendations
import random

main_bp = Blueprint('main', __name__)

PRESET_AVATARS = [
    {"id": "avatar_red", "name": "Classic Red", "gradient": "linear-gradient(135deg, #e50914 0%, #9e060e 100%)"},
    {"id": "avatar_blue", "name": "Deep Space Blue", "gradient": "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)"},
    {"id": "avatar_yellow", "name": "Retro Gold", "gradient": "linear-gradient(135deg, #f1c40f 0%, #f39c12 100%)"},
    {"id": "avatar_green", "name": "Matrix Green", "gradient": "linear-gradient(135deg, #11998e 0%, #38ef7d 100%)"},
    {"id": "avatar_purple", "name": "Cyberpunk Neon", "gradient": "linear-gradient(135deg, #8a2be2 0%, #4a00e0 100%)"},
    {"id": "avatar_orange", "name": "Vibrant Sunset", "gradient": "linear-gradient(135deg, #ff9900 0%, #ff5500 100%)"},
    {"id": "avatar_pink", "name": "Anime Chibi Pink", "gradient": "linear-gradient(135deg, #ec008c 0%, #fc6767 100%)"},
    {"id": "avatar_grey", "name": "Dark Knight Grey", "gradient": "linear-gradient(135deg, #3a3d40 0%, #181719 100%)"}
]

@main_bp.route("/")
def landing():
    # If profile cookie is already active, redirect directly to dashboard
    if g.current_profile:
        return redirect(url_for('main.dashboard'))
    
    # Showcase standard popular trending movies on landing background
    trending = fetch_trending_all("movie", "week")
    background_movie = random.choice(trending) if trending else None
    
    return render_template("landing.html", 
                           background_movie=background_movie, 
                           trending=trending[:5])

@main_bp.route("/profiles", methods=["GET"])
def profiles():
    all_profiles = Profile.query.all()
    return render_template("profiles.html", 
                           profiles=all_profiles, 
                           avatars=PRESET_AVATARS)

@main_bp.route("/profiles/create", methods=["POST"])
def create_profile():
    name = request.form.get("name", "").strip()
    avatar = request.form.get("avatar", "avatar_red")
    is_kids = request.form.get("is_kids") == "on"
    pin = request.form.get("pin", "").strip()
    
    if not name:
        flash("Profile name is required", "error")
        return redirect(url_for('main.profiles'))
        
    # Check limit of 5 profiles
    if Profile.query.count() >= 5:
        flash("You can have a maximum of 5 profiles.", "error")
        return redirect(url_for('main.profiles'))
        
    new_profile = Profile(name=name, avatar=avatar, is_kids=is_kids)
    if pin:
        new_profile.set_pin(pin)
        
    db.session.add(new_profile)
    db.session.commit()
    
    # Autoselect profile if first profile
    response = make_response(redirect(url_for('main.dashboard')))
    if Profile.query.count() == 1:
        response.set_cookie('active_profile_id', str(new_profile.id), max_age=31536000) # 1 year
        return response
        
    return redirect(url_for('main.profiles'))

@main_bp.route("/profiles/select/<int:profile_id>", methods=["GET"])
def select_profile(profile_id):
    profile = Profile.query.get_or_404(profile_id)
    
    # If PIN locked, client handles pin check before entering OTT
    if profile.pin_hash:
        return redirect(url_for('main.profiles', require_pin=profile_id))
        
    response = make_response(redirect(url_for('main.dashboard')))
    response.set_cookie('active_profile_id', str(profile.id), max_age=31536000)
    return response

@main_bp.route("/profiles/verify-pin", methods=["POST"])
def verify_profile_pin():
    profile_id = request.form.get("profile_id")
    pin = request.form.get("pin", "").strip()
    
    profile = Profile.query.get_or_404(profile_id)
    if profile.verify_pin(pin):
        response = make_response(jsonify({"success": True}))
        response.set_cookie('active_profile_id', str(profile.id), max_age=31536000)
        return response
    else:
        return jsonify({"success": False, "message": "Invalid 4-digit Profile PIN."})

@main_bp.route("/profiles/edit/<int:profile_id>", methods=["POST"])
def edit_profile(profile_id):
    profile = Profile.query.get_or_404(profile_id)
    name = request.form.get("name", "").strip()
    avatar = request.form.get("avatar")
    is_kids = request.form.get("is_kids") == "on"
    pin = request.form.get("pin", "").strip()
    clear_pin = request.form.get("clear_pin") == "on"
    
    if name:
        profile.name = name
    if avatar:
        profile.avatar = avatar
    profile.is_kids = is_kids
    
    if clear_pin:
        profile.pin_hash = None
    elif pin:
        profile.set_pin(pin)
        
    db.session.commit()
    return redirect(url_for('main.profiles'))

@main_bp.route("/profiles/delete/<int:profile_id>", methods=["POST"])
def delete_profile(profile_id):
    profile = Profile.query.get_or_404(profile_id)
    
    # If deleting the active profile, clear the active cookie
    active_id = request.cookies.get('active_profile_id')
    
    db.session.delete(profile)
    db.session.commit()
    
    response = make_response(redirect(url_for('main.profiles')))
    if active_id and int(active_id) == profile_id:
        response.delete_cookie('active_profile_id')
        
    return response

@main_bp.route("/profiles/logout")
def logout():
    response = make_response(redirect(url_for('main.landing')))
    response.delete_cookie('active_profile_id')
    return response

@main_bp.route("/dashboard")
def dashboard():
    profile = g.current_profile
    if not profile:
        return redirect(url_for('main.landing'))
        
    # billboard hero banner: Select popular high-vibe movie
    trending_movies = fetch_trending_all("movie", "week")
    hero_item = trending_movies[0] if trending_movies else None
    
    # Custom rows data
    continue_watching = ContinueWatching.query.filter_by(profile_id=profile.id).order_by(ContinueWatching.updated_at.desc()).limit(12).all()
    watchlist = Watchlist.query.filter_by(profile_id=profile.id).order_by(Watchlist.added_at.desc()).limit(12).all()
    
    # AI recommendations list
    ai_recommendations = get_profile_recommendations(profile)
    
    # General categories
    trending_all = fetch_trending_all("all", "day")[:15]
    trending_tv = fetch_trending_all("tv", "week")[:15]
    
    if profile.is_kids:
        # Kids filters: Family-only movies
        popular_movies = fetch_movies(genre="10751,16") # Family, Animation
        popular_tv = fetch_tv_shows(genre="10762,16") # Kids, Animation
        anime_list = fetch_anime_list(genre="Fantasy")[:15]
    else:
        popular_movies = fetch_movies()[:15]
        popular_tv = fetch_tv_shows()[:15]
        anime_list = fetch_anime_list()[:15]
        
    return render_template("dashboard.html",
                           hero=hero_item,
                           continue_watching=continue_watching,
                           watchlist=watchlist,
                           ai_recs=ai_recommendations,
                           trending=trending_all,
                           popular_movies=popular_movies,
                           popular_tv=popular_tv,
                           trending_tv=trending_tv,
                           anime=anime_list,
                           avatars=PRESET_AVATARS)

@main_bp.route("/search")
def search():
    profile = g.current_profile
    if not profile:
        return redirect(url_for('main.landing'))
        
    q = request.args.get("q", "").strip()
    
    movies = []
    tv_shows = []
    anime_items = []
    
    if q:
        # Save to search history
        from app.models import SearchHistory
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
            
        # 1. Fetch TMDB Movies
        from app.services.tmdb_service import fetch_movies
        try:
            movies = fetch_movies(search=q).get("results", [])
        except Exception:
            pass
            
        # 2. Fetch TMDB TV Shows
        from app.services.tmdb_service import fetch_tv_shows
        try:
            tv_shows = fetch_tv_shows(search=q).get("results", [])
        except Exception:
            pass
            
        # 3. Fetch Jikan Anime
        from app.services.jikan_service import fetch_anime_list
        try:
            anime_items = fetch_anime_list(search=q)
        except Exception:
            pass
            
    # Also fetch the watchlist for card action indicators
    from app.models import Watchlist
    watchlist = Watchlist.query.filter_by(profile_id=profile.id).all()
            
    return render_template("search.html",
                           query=q,
                           movies=movies,
                           tv_shows=tv_shows,
                           anime=anime_items,
                           watchlist=watchlist)

@main_bp.route("/trending")
def trending_catalog():
    profile = g.current_profile
    if not profile:
        return redirect(url_for('main.landing'))
        
    if profile.is_kids:
        # For kids, fetch family/animation movies and kids/animation TV shows, then blend them
        movies = fetch_movies(genre="10751,16", sort_by="popularity.desc").get("results", [])
        tv = fetch_tv_shows(genre="10762,16", sort_by="popularity.desc").get("results", [])
    else:
        movies = fetch_trending_all("movie", "week")
        tv = fetch_trending_all("tv", "week")
        
    # Interleave results for dynamic visual flow
    items = []
    for m, t in zip(movies, tv):
        items.extend([m, t])
    if len(movies) > len(tv):
        items.extend(movies[len(tv):])
    elif len(tv) > len(movies):
        items.extend(tv[len(movies):])
        
    return render_template("catalog.html",
                           title="Trending Now",
                           icon="🔥",
                           description="The most watched movies and TV shows this week.",
                           items=items)

@main_bp.route("/top-rated")
def top_rated_catalog():
    profile = g.current_profile
    if not profile:
        return redirect(url_for('main.landing'))
        
    if profile.is_kids:
        movies = fetch_movies(genre="10751,16", sort_by="vote_average.desc").get("results", [])
        tv = fetch_tv_shows(genre="10762,16", sort_by="vote_average.desc").get("results", [])
    else:
        movies = tmdb_request("/movie/top_rated").get("results", [])
        tv = tmdb_request("/tv/top_rated").get("results", [])
        
    items = []
    for m, t in zip(movies, tv):
        items.extend([m, t])
    if len(movies) > len(tv):
        items.extend(movies[len(tv):])
    elif len(tv) > len(movies):
        items.extend(tv[len(movies):])
        
    return render_template("catalog.html",
                           title="Top Rated",
                           icon="⭐",
                           description="Highly acclaimed movies and TV shows rated by viewers worldwide.",
                           items=items)

@main_bp.route("/new-releases")
def new_releases_catalog():
    profile = g.current_profile
    if not profile:
        return redirect(url_for('main.landing'))
        
    if profile.is_kids:
        movies = fetch_movies(genre="10751,16", sort_by="primary_release_date.desc").get("results", [])
        tv = fetch_tv_shows(genre="10762,16", sort_by="first_air_date.desc").get("results", [])
    else:
        movies = tmdb_request("/movie/now_playing").get("results", [])
        tv = tmdb_request("/tv/on_the_air").get("results", [])
        
    items = []
    for m, t in zip(movies, tv):
        items.extend([m, t])
    if len(movies) > len(tv):
        items.extend(movies[len(tv):])
    elif len(tv) > len(movies):
        items.extend(tv[len(movies):])
        
    return render_template("catalog.html",
                           title="New Releases",
                           icon="📅",
                           description="Freshly added titles and currently airing shows.",
                           items=items)

@main_bp.route("/genres")
def genres_catalog():
    profile = g.current_profile
    if not profile:
        return redirect(url_for('main.landing'))
        
    genre_id = request.args.get("genre", "").strip()
    
    GENRE_MAP = {
        "28": "Action",
        "12": "Adventure",
        "16": "Animation",
        "35": "Comedy",
        "80": "Crime",
        "99": "Documentary",
        "18": "Drama",
        "10751": "Family",
        "14": "Fantasy",
        "27": "Horror",
        "9648": "Mystery",
        "10749": "Romance",
        "878": "Sci-Fi",
        "53": "Thriller",
        "37": "Western",
        "10759": "Action & Adventure",
        "10762": "Kids",
        "10765": "Sci-Fi & Fantasy"
    }
    
    if not genre_id:
        all_genres = [
            {"id": "28", "name": "Action", "icon": "🔥", "gradient": "linear-gradient(135deg, #FF416C 0%, #FF4B2B 100%)", "kids": False},
            {"id": "12", "name": "Adventure", "icon": "🧭", "gradient": "linear-gradient(135deg, #00B4DB 0%, #0083B0 100%)", "kids": True},
            {"id": "16", "name": "Animation", "icon": "✨", "gradient": "linear-gradient(135deg, #a8c0ff 0%, #3f2b96 100%)", "kids": True},
            {"id": "35", "name": "Comedy", "icon": "😂", "gradient": "linear-gradient(135deg, #F12711 0%, #f5af19 100%)", "kids": True},
            {"id": "80", "name": "Crime", "icon": "🕵", "gradient": "linear-gradient(135deg, #1F1C2C 0%, #928DAB 100%)", "kids": False},
            {"id": "99", "name": "Documentary", "icon": "🎥", "gradient": "linear-gradient(135deg, #11998e 0%, #38ef7d 100%)", "kids": False},
            {"id": "18", "name": "Drama", "icon": "🎭", "gradient": "linear-gradient(135deg, #6441A5 0%, #2a0845 100%)", "kids": False},
            {"id": "10751", "name": "Family", "icon": "🏠", "gradient": "linear-gradient(135deg, #ff007f 0%, #ff80df 100%)", "kids": True},
            {"id": "14", "name": "Fantasy", "icon": "🧙", "gradient": "linear-gradient(135deg, #da22ff 0%, #9114ff 100%)", "kids": True},
            {"id": "27", "name": "Horror", "icon": "👻", "gradient": "linear-gradient(135deg, #141E30 0%, #243B55 100%)", "kids": False},
            {"id": "9648", "name": "Mystery", "icon": "❓", "gradient": "linear-gradient(135deg, #360033 0%, #0b8793 100%)", "kids": False},
            {"id": "10749", "name": "Romance", "icon": "💖", "gradient": "linear-gradient(135deg, #ff4e50 0%, #f9d423 100%)", "kids": False},
            {"id": "878", "name": "Sci-Fi", "icon": "👽", "gradient": "linear-gradient(135deg, #0575E6 0%, #00F260 100%)", "kids": True},
            {"id": "53", "name": "Thriller", "icon": "🔪", "gradient": "linear-gradient(135deg, #3A1C1C 0%, #d72638 100%)", "kids": False},
            {"id": "37", "name": "Western", "icon": "🤠", "gradient": "linear-gradient(135deg, #F3904F 0%, #3B4371 100%)", "kids": False}
        ]
        
        if profile.is_kids:
            genres_list = [g for g in all_genres if g["kids"]]
        else:
            genres_list = all_genres
            
        return render_template("genres.html", genres=genres_list)
        
    genre_name = GENRE_MAP.get(genre_id, "Discovery")
    
    if profile.is_kids and genre_id not in ["12", "16", "35", "10751", "14", "878"]:
        return redirect(url_for('main.genres_catalog'))
        
    movies = fetch_movies(genre=genre_id).get("results", [])
    tv = fetch_tv_shows(genre=genre_id).get("results", [])
    
    items = []
    for m, t in zip(movies, tv):
        items.extend([m, t])
    if len(movies) > len(tv):
        items.extend(movies[len(tv):])
    elif len(tv) > len(movies):
        items.extend(tv[len(movies):])
        
    return render_template("catalog.html",
                           title=genre_name,
                           icon="🎬",
                           description=f"Explore premium movies and TV shows in the {genre_name} category.",
                           items=items)


