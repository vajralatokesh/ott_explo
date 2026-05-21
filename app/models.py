from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Profile(db.Model):
    __tablename__ = 'profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    avatar = db.Column(db.String(255), nullable=False, default='avatar_red')
    is_kids = db.Column(db.Boolean, default=False)
    pin_hash = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    watchlist_items = db.relationship('Watchlist', backref='profile', cascade='all, delete-orphan', lazy=True)
    continue_watching_items = db.relationship('ContinueWatching', backref='profile', cascade='all, delete-orphan', lazy=True)
    recently_watched_items = db.relationship('RecentlyWatched', backref='profile', cascade='all, delete-orphan', lazy=True)
    search_history_items = db.relationship('SearchHistory', backref='profile', cascade='all, delete-orphan', lazy=True)

    def set_pin(self, pin):
        if pin:
            self.pin_hash = generate_password_hash(pin)
        else:
            self.pin_hash = None

    def verify_pin(self, pin):
        if not self.pin_hash:
            return True
        return check_password_hash(self.pin_hash, pin)

class Watchlist(db.Model):
    __tablename__ = 'watchlist'
    
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    content_id = db.Column(db.String(50), nullable=False, index=True)
    content_type = db.Column(db.String(20), nullable=False) # 'movie', 'tv', 'anime'
    title = db.Column(db.String(255), nullable=False)
    poster = db.Column(db.String(500), nullable=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('profile_id', 'content_id', 'content_type', name='uq_profile_content'),
    )

class ContinueWatching(db.Model):
    __tablename__ = 'continue_watching'
    
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    content_id = db.Column(db.String(50), nullable=False, index=True)
    content_type = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    poster = db.Column(db.String(500), nullable=True)
    progress = db.Column(db.Integer, default=0) # current playing position in seconds
    duration = db.Column(db.Integer, default=0) # total duration in seconds
    season = db.Column(db.Integer, nullable=True) # for tv/anime
    episode = db.Column(db.Integer, nullable=True) # for tv/anime
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('profile_id', 'content_id', 'content_type', name='uq_profile_continue'),
    )

class RecentlyWatched(db.Model):
    __tablename__ = 'watch_history'
    
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    content_id = db.Column(db.String(50), nullable=False)
    content_type = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    poster = db.Column(db.String(500), nullable=True)
    watched_at = db.Column(db.DateTime, default=datetime.utcnow)

class SearchHistory(db.Model):
    __tablename__ = 'search_history'
    
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    query = db.Column(db.String(255), nullable=False)
    searched_at = db.Column(db.DateTime, default=datetime.utcnow)
