# 🎬 OTT Explorer

OTT Explorer is a modern movie and TV show discovery platform inspired by popular streaming services. Users can browse movies, TV shows, and anime, create personal profiles, maintain watchlists, and stream content through multiple servers.

## ✨ Features

### 👤 User Accounts
- User Registration & Login
- Secure Session Management
- Profile-based Experience
- PIN Protected Profiles

### 🎥 Content Discovery
- Trending Movies
- Popular TV Shows
- Anime Collection
- Genre-Based Browsing
- Detailed Content Information
- Cast & Ratings Information

### 🔍 Advanced Search
- Live Search Suggestions
- Fuzzy Search Matching
- Mobile Optimized Search
- Poster-Based Search Results

### ❤️ Personalization
- Personal Watchlist
- Profile Management
- Continue Watching Support
- Recently Viewed Content

### 📱 Responsive Design
- Mobile Friendly Interface
- Tablet Support
- Desktop Optimized Layout
- Modern Gold & Black Theme

### 🚀 Streaming Features
- Multiple Streaming Servers
- Fullscreen Support
- Subtitle Support
- Fast Content Loading

---

## 🛠️ Tech Stack

### Backend
- Python
- Flask
- SQLAlchemy
- Flask-Migrate
- Flask-Caching
- Gunicorn

### Frontend
- HTML5
- CSS3
- JavaScript
- Bootstrap

### Database
- SQLite (Development)
- PostgreSQL (Production Ready)

### Deployment
- Render
- GitHub

---

## 📂 Project Structure

```bash
OTT-Explorer/
│
├── app/
├── static/
├── templates/
├── instance/
├── migrations/
│
├── app.py
├── requirements.txt
├── Procfile
├── Dockerfile
└── README.md
```

---

## ⚙️ Installation

### Clone Repository

```bash
git clone https://github.com/vajralatokesh/ott_explo.git
cd ott_explo
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Environment

Windows:

```bash
venv\Scripts\activate
```

Linux/Mac:

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Application

```bash
python app.py
```

Application will run at:

```text
http://localhost:5000
```

---

## 🚀 Deployment on Render

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
gunicorn app:app
```

---

## 📸 Screenshots

- Home Page
- Profile Selection
- Movie Details
- Streaming Page
- Watchlist

(Add screenshots here)

---

## 🔮 Future Improvements

- AI Movie Recommendations
- User Reviews & Ratings
- Download Support
- Watch History Analytics
- Dark/Light Theme Toggle
- Multi-Language Support

---

## 👨‍💻 Author

**Tokesh Vajrala**

GitHub: https://github.com/vajralatokesh

---

## ⭐ Support

If you like this project, consider giving it a star on GitHub.

```

This version looks professional for recruiters, hackathons, GitHub visitors, and portfolio reviews.
