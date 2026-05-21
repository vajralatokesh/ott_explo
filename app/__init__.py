import os
from flask import Flask, g, request, redirect, url_for
from flask_migrate import Migrate
from flask_caching import Cache
from dotenv import load_dotenv
from app.models import db, Profile

# Load environments
load_dotenv()

# Initialize extensions
migrate = Migrate()
cache = Cache()

def create_app():
    app = Flask(__name__, 
                template_folder='../templates', 
                static_folder='../static')
    
    # Configure App
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "ott-secret-key")
    
    # Check if DATABASE_URL env var is set and normalize it if it's a relative SQLite URL
    env_db_url = os.getenv("DATABASE_URL")
    db_filename = 'database.db'
    if env_db_url and env_db_url.startswith("sqlite:///"):
        extracted = env_db_url.replace("sqlite:///", "")
        # If it's a simple relative database filename, use it, otherwise keep default 'database.db'
        if not os.path.isabs(extracted) and '/' not in extracted and '\\' not in extracted:
            db_filename = extracted

    # Resolve SQLite database path safely in instance directory
    db_path = os.path.join(app.instance_path, db_filename)
    os.makedirs(app.instance_path, exist_ok=True)
    
    # 1. Detect old SQLite schema mismatch
    schema_mismatch = False
    if os.path.exists(db_path):
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(watchlist);")
            columns = [row[1] for row in cursor.fetchall()]
            conn.close()
            # If watchlist exists but lacks 'profile_id', it's a legacy schema
            if columns and 'profile_id' not in columns:
                schema_mismatch = True
        except Exception:
            schema_mismatch = True
            
    # 2. Remove outdated database.db safely
    if schema_mismatch:
        print("WARNING: Outdated SQLite schema detected in database.db. Rebuilding safely...")
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
            print("Legacy database removed successfully.")
        except Exception as e:
            # Fallback if Windows file lock is active (development server running)
            print(f"WARNING: database file is locked ({e}). Bypassing via database_v2.db...")
            db_path = os.path.join(app.instance_path, 'database_v2.db')
            
            # Double check database_v2.db schema too
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA table_info(watchlist);")
                    columns = [row[1] for row in cursor.fetchall()]
                    conn.close()
                    if columns and 'profile_id' not in columns:
                        os.remove(db_path)
                except Exception:
                    pass

    # Ensure the final resolved absolute path is used, overriding any environment relative SQLite URI
    if env_db_url and not env_db_url.startswith("sqlite:///"):
        # Non-sqlite production DB (e.g. Postgres)
        app.config["SQLALCHEMY_DATABASE_URI"] = env_db_url
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Cache config - simple memory cache for web, extensible to redis
    app.config["CACHE_TYPE"] = "SimpleCache"
    app.config["CACHE_DEFAULT_TIMEOUT"] = 300 # 5 minutes default
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    
    # 3. Recreate database using latest SQLAlchemy models automatically
    with app.app_context():
        db.create_all()
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.movies import movies_bp
    from app.routes.tvshows import tvshows_bp
    from app.routes.anime import anime_bp
    from app.routes.watchlist import watchlist_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(movies_bp)
    app.register_blueprint(tvshows_bp)
    app.register_blueprint(anime_bp)
    app.register_blueprint(watchlist_bp)
    app.register_blueprint(api_bp)
    
    # Context processor for common templates helpers
    @app.context_processor
    def inject_helpers():
        return {
            'IMAGE_BASE': "https://image.tmdb.org/t/p/w500",
            'IMAGE_ORIG': "https://image.tmdb.org/t/p/original",
            'current_profile': getattr(g, 'current_profile', None)
        }
    
    # Request interceptor for active profile enforcement
    @app.before_request
    def load_active_profile():
        # Exclude static assets
        if request.path.startswith('/static'):
            return
            
        profile_id = request.cookies.get('active_profile_id') or request.environ.get('HTTP_X_PROFILE_ID')
        g.current_profile = None
        
        if profile_id:
            try:
                g.current_profile = Profile.query.get(int(profile_id))
            except Exception:
                g.current_profile = None
                
        # Secure endpoint restriction
        allowed_endpoints = [
            'main.landing',
            'main.profiles',
            'main.select_profile',
            'main.create_profile',
            'main.verify_profile_pin',
            'main.delete_profile',
            'main.edit_profile',
            'api.suggest' # Autocomplete api
        ]
        
        # If no profile active and route is NOT in allowed_endpoints, redirect to landing
        if not g.current_profile and request.endpoint and request.endpoint not in allowed_endpoints:
            return redirect(url_for('main.landing'))
            
    return app
