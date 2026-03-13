from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
import requests, os

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
SECRET_KEY   = os.getenv("SECRET_KEY", "ott-secret-key")
IMAGE_BASE   = "https://image.tmdb.org/t/p/w500"
IMAGE_ORIG   = "https://image.tmdb.org/t/p/original"

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(db.Model, UserMixin):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))

class Watchlist(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer)
    content_id   = db.Column(db.Integer)
    content_type = db.Column(db.String(20))
    title        = db.Column(db.String(200))
    poster       = db.Column(db.String(500))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def tmdb(path, params=None):
    p = {"api_key": TMDB_API_KEY}
    if params: p.update(params)
    try:
        r = requests.get(f"https://api.themoviedb.org/3{path}", params=p, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"TMDB [{path}]:", e)
        return {}

def jikan(path):
    try:
        r = requests.get(f"https://api.jikan.moe/v4{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Jikan [{path}]:", e)
        return {}

def get_movies(search=None, language=None, genre=None, year=None, sort_by=None, decade=None):
    results = []
    if search:
        for pg in range(1, 5):
            batch = tmdb("/search/movie", {"query": search, "page": pg, "include_adult": False}).get("results", [])
            if not batch: break
            results.extend(batch)
    else:
        sort = sort_by or "popularity.desc"
        params = {"sort_by": sort, "include_adult": False, "include_video": False}
        if language: params["with_original_language"] = language
        if genre:    params["with_genres"] = genre
        if year:     params["primary_release_year"] = year
        if decade:
            s = int(decade)
            params["primary_release_date.gte"] = f"{s}-01-01"
            params["primary_release_date.lte"] = f"{s+9}-12-31"
        for pg in range(1, 7):
            params["page"] = pg
            batch = tmdb("/discover/movie", params).get("results", [])
            if not batch: break
            results.extend(batch)
    seen, unique = set(), []
    for m in results:
        if m.get("id") and m["id"] not in seen:
            seen.add(m["id"]); unique.append(m)
    return unique

def get_movie_details(movie_id):
    d = tmdb(f"/movie/{movie_id}")
    return d if d else None

def get_movie_imdb_id(movie_id):
    return tmdb(f"/movie/{movie_id}/external_ids").get("imdb_id", "")

def get_movie_videos(movie_id):
    return tmdb(f"/movie/{movie_id}/videos").get("results", [])

def get_tv_shows(search=None, language=None, genre=None, sort_by=None):
    results = []
    if search:
        for pg in range(1, 5):
            batch = tmdb("/search/tv", {"query": search, "page": pg}).get("results", [])
            if not batch: break
            results.extend(batch)
    else:
        sort = sort_by or "popularity.desc"
        params = {"sort_by": sort}
        if language: params["with_original_language"] = language
        if genre:    params["with_genres"] = genre
        for pg in range(1, 7):
            params["page"] = pg
            batch = tmdb("/discover/tv", params).get("results", [])
            if not batch: break
            results.extend(batch)
    seen, unique = set(), []
    for t in results:
        if t.get("id") and t["id"] not in seen:
            seen.add(t["id"]); unique.append(t)
    return unique

def get_tv_details(tv_id):
    d = tmdb(f"/tv/{tv_id}")
    return d if d else None

def get_tv_imdb_id(tv_id):
    return tmdb(f"/tv/{tv_id}/external_ids").get("imdb_id", "")

def get_tv_season(tv_id, season_number):
    d = tmdb(f"/tv/{tv_id}/season/{season_number}")
    return d if d else None

def get_anime(search=None, genre=None):
    data = jikan(f"/anime?q={search}&limit=24") if search else jikan("/top/anime?limit=24")
    anime_list = data.get("data", [])
    if genre:
        anime_list = [a for a in anime_list
                      if any(genre.lower() == g["name"].lower() for g in a.get("genres", []))]
    return anime_list

def get_anime_details(mal_id):
    return jikan(f"/anime/{mal_id}").get("data") or None

def search_tmdb_for_anime(anime_data):
    """
    Multi-strategy TMDB lookup for anime.
    Tries English title, romaji title, synonyms — returns TMDB TV id or None.
    """
    titles_to_try = []
    eng    = (anime_data.get("title_english") or "").strip()
    romaji = (anime_data.get("title")         or "").strip()

    if eng:    titles_to_try.append(eng)
    if romaji and romaji != eng: titles_to_try.append(romaji)

    for syn in (anime_data.get("title_synonyms") or []):
        s = (syn or "").strip()
        if s and s not in titles_to_try:
            titles_to_try.append(s)

    for title in titles_to_try:
        results = tmdb("/search/tv", {"query": title}).get("results", [])
        if results:
            return results[0]["id"]
        # strip subtitle after colon
        base = title.split(":")[0].strip()
        if base != title:
            results = tmdb("/search/tv", {"query": base}).get("results", [])
            if results:
                return results[0]["id"]
    return None

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        if not u or not p:
            error = "Please enter both username and password."
        else:
            user = User.query.filter_by(username=u, password=p).first()
            if user:
                login_user(user)
                return redirect(url_for("dashboard"))
            else:
                error = "Invalid username or password."
    return render_template("login.html", error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        if not u or not p:
            error = "Please fill in all fields."
        elif User.query.filter_by(username=u).first():
            error = "Username already exists."
        else:
            db.session.add(User(username=u, password=p))
            db.session.commit()
            return redirect(url_for("login"))
    return render_template("register.html", error=error)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    search   = request.args.get("search",   "").strip()
    language = request.args.get("language", "")
    genre    = request.args.get("genre",    "")
    year     = request.args.get("year",     "")
    sort_by  = request.args.get("sort_by",  "")
    decade   = request.args.get("decade",   "")
    movies   = get_movies(search or None, language or None, genre or None,
                          year or None, sort_by or None, decade or None)
    return render_template("dashboard.html",
        movies=movies, image_base=IMAGE_BASE,
        search=search, language=language, genre=genre,
        year=year, sort_by=sort_by, decade=decade)

@app.route("/movie/<int:id>")
@login_required
def movie_details(id):
    movie = get_movie_details(id)
    if not movie:
        return redirect(url_for("dashboard"))
    imdb_id = get_movie_imdb_id(id)
    videos  = get_movie_videos(id)
    trailer = next((v for v in videos if v.get("type") == "Trailer" and v.get("site") == "YouTube"), None)
    return render_template("detail.html",
        movie=movie, imdb_id=imdb_id,
        image_base=IMAGE_BASE, image_orig=IMAGE_ORIG, trailer=trailer)

@app.route("/tvshows")
@login_required
def tvshows():
    search   = request.args.get("search",   "").strip()
    language = request.args.get("language", "")
    genre    = request.args.get("genre",    "")
    sort_by  = request.args.get("sort_by",  "")
    tv_list  = get_tv_shows(search or None, language or None, genre or None, sort_by or None)
    return render_template("tvshows.html",
        tv_list=tv_list, image_base=IMAGE_BASE,
        search=search, language=language, genre=genre, sort_by=sort_by)

@app.route("/tv/<int:id>")
@login_required
def tv_details(id):
    tv = get_tv_details(id)
    if not tv:
        return redirect(url_for("tvshows"))
    imdb_id    = get_tv_imdb_id(id)
    season_num = int(request.args.get("season", 1))
    season     = get_tv_season(id, season_num)
    return render_template("tv_detail.html",
        tv=tv, imdb_id=imdb_id,
        season=season, current_season=season_num,
        image_base=IMAGE_BASE, image_orig=IMAGE_ORIG)

@app.route("/anime")
@login_required
def anime():
    anime_list = get_anime(request.args.get("search"), request.args.get("genre"))
    return render_template("anime.html", anime=anime_list)

@app.route("/anime/<int:id>")
@login_required
def anime_details(id):
    anime_data = get_anime_details(id)
    if not anime_data:
        return redirect(url_for("anime"))
    # Pass full anime_data so multi-strategy title search works
    tmdb_id  = search_tmdb_for_anime(anime_data)
    imdb_id  = get_tv_imdb_id(tmdb_id) if tmdb_id else ""
    episodes = anime_data.get("episodes") or 24
    return render_template("anime_detail.html",
        anime=anime_data, tmdb_id=tmdb_id,
        imdb_id=imdb_id, episodes=episodes)

@app.route("/watchlist/add_movie/<int:id>")
@login_required
def add_movie_watchlist(id):
    movie = get_movie_details(id)
    if movie and not Watchlist.query.filter_by(user_id=current_user.id, content_id=id, content_type="movie").first():
        db.session.add(Watchlist(user_id=current_user.id, content_id=id, content_type="movie",
            title=movie.get("title", ""), poster=movie.get("poster_path", "")))
        db.session.commit()
    return redirect(request.referrer or url_for("dashboard"))

@app.route("/watchlist/add_tv/<int:id>")
@login_required
def add_tv_watchlist(id):
    tv = get_tv_details(id)
    if tv and not Watchlist.query.filter_by(user_id=current_user.id, content_id=id, content_type="tv").first():
        db.session.add(Watchlist(user_id=current_user.id, content_id=id, content_type="tv",
            title=tv.get("name", ""), poster=tv.get("poster_path", "")))
        db.session.commit()
    return redirect(request.referrer or url_for("tvshows"))

@app.route("/watchlist/add_anime/<int:id>")
@login_required
def add_anime_watchlist(id):
    data = get_anime_details(id)
    if data and not Watchlist.query.filter_by(user_id=current_user.id, content_id=id, content_type="anime").first():
        db.session.add(Watchlist(user_id=current_user.id, content_id=id, content_type="anime",
            title=data.get("title", ""),
            poster=data.get("images", {}).get("jpg", {}).get("image_url", "")))
        db.session.commit()
    return redirect(request.referrer or url_for("anime"))

@app.route("/watchlist/remove/<int:id>")
@login_required
def remove_watchlist(id):
    item = Watchlist.query.filter_by(user_id=current_user.id, id=id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for("watchlist"))

@app.route("/watchlist")
@login_required
def watchlist():
    items = Watchlist.query.filter_by(user_id=current_user.id).all()
    return render_template("watchlist.html", items=items, image_base=IMAGE_BASE)

@app.route("/api/suggest")
@login_required
def suggest():
    q    = request.args.get("q", "").strip()
    kind = request.args.get("kind", "movie")
    if len(q) < 2:
        return jsonify([])
    try:
        if kind == "movie":
            rows = tmdb("/search/movie", {"query": q, "page": 1}).get("results", [])[:8]
            return jsonify([{"id": r["id"], "title": r.get("title", ""),
                "year": (r.get("release_date") or "")[:4],
                "poster": IMAGE_BASE + r["poster_path"] if r.get("poster_path") else ""} for r in rows])
        elif kind == "tv":
            rows = tmdb("/search/tv", {"query": q, "page": 1}).get("results", [])[:8]
            return jsonify([{"id": r["id"], "title": r.get("name", ""),
                "year": (r.get("first_air_date") or "")[:4],
                "poster": IMAGE_BASE + r["poster_path"] if r.get("poster_path") else ""} for r in rows])
        else:
            rows = jikan(f"/anime?q={q}&limit=8").get("data", [])
            return jsonify([{"id": r["mal_id"], "title": r.get("title", ""),
                "year": r.get("year") or "",
                "poster": r.get("images", {}).get("jpg", {}).get("image_url", "")} for r in rows])
    except Exception as e:
        print("Suggest error:", e)
        return jsonify([])

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

with app.app_context():
    db.create_all()
