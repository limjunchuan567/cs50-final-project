"""Mood playlist tracker: link songs to moods and get playlists for how you feel."""
import os
import random
import re
from datetime import datetime

import requests
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required

app = Flask(__name__)
# Set real values in your shell:  export SECRET_KEY=...  and  export LASTFM_API_KEY=...
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

db = SQL("sqlite:///moodtracker.db")

LASTFM_KEY = os.environ.get("LASTFM_API_KEY")

# Last.fm tag -> your mood names (must match rows in the moods table)
MOOD_MAP = {
    "chill": "calm", "relax": "calm", "mellow": "calm",
    "sad": "sad", "melancholy": "sad", "heartbreak": "sad",
    "happy": "happy", "feel good": "happy", "upbeat": "happy",
    "energetic": "hyped", "workout": "hyped", "party": "hyped",
    "focus": "focused", "study": "focused", "instrumental": "focused",
}

DEFAULT_LENGTH = 10
MAX_LENGTH = 25
DEFAULT_WEIGHT = 3.0     # weight for songs with no ratings yet (ratings are 1-5)
RECENT_DAYS = 2          # songs played this recently get down-weighted
RECENT_PENALTY = 0.3


@app.after_request
def after_request(response):
    """Stop browsers caching pages, so the back button doesn't show logged-out data."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = "0"
    response.headers["Pragma"] = "no-cache"
    return response


# ---------- Home ----------

@app.route("/")
@login_required
def index():
    uid = session["user_id"]
    song_count = db.execute(
        "SELECT COUNT(*) AS n FROM songs WHERE user_id = ?", uid
    )[0]["n"]
    recent = db.execute(
        "SELECT ml.id, ml.timestamp, m.name AS mood "
        "FROM mood_logs ml JOIN moods m ON m.id = ml.mood_id "
        "WHERE ml.user_id = ? ORDER BY ml.id DESC LIMIT 5",
        uid,
    )
    return render_template("index.html", song_count=song_count, recent=recent)


# ---------- Auth ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirmation = request.form.get("confirmation", "")

    if not username or not password:
        flash("Username and password are required")
        return redirect("/register")
    if password != confirmation:
        flash("Passwords do not match")
        return redirect("/register")

    try:
        user_id = db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)",
            username, generate_password_hash(password),
        )
    except ValueError:  # UNIQUE constraint on username
        flash("Username already taken")
        return redirect("/register")

    session.clear()
    session["user_id"] = user_id
    return redirect("/")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    rows = db.execute("SELECT id, hash FROM users WHERE username = ?", username)

    if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
        flash("Invalid username or password")
        return redirect("/login")

    session["user_id"] = rows[0]["id"]
    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------- Adding songs ----------

def parse_link(url):
    """Return (embed_type, embed_id) from a Spotify or YouTube link, else None."""
    m = re.search(r"open\.spotify\.com/track/(\w+)", url)
    if m:
        return ("spotify", m.group(1))
    m = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", url)
    if m:
        return ("youtube", m.group(1))
    return None


def get_lastfm_tags(artist, title):
    """Return a list of tag names for a track, or [] if anything goes wrong."""
    if not LASTFM_KEY:
        return []
    try:
        r = requests.get(
            "https://ws.audioscrobbler.com/2.0/",
            params={
                "method": "track.gettoptags",
                "artist": artist,
                "track": title,
                "api_key": LASTFM_KEY,
                "format": "json",
                "autocorrect": 1,
            },
            timeout=5,
        )
        data = r.json()
        return [t["name"] for t in data.get("toptags", {}).get("tag", [])]
    except (requests.RequestException, ValueError):
        return []


def suggest_moods(tags):
    """Map raw Last.fm tags to your mood names."""
    return list({MOOD_MAP[t.lower()] for t in tags if t.lower() in MOOD_MAP})


@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Step 1: paste a link + title/artist, see suggested moods."""
    if request.method == "GET":
        return render_template("add.html")

    title = request.form.get("title", "").strip()
    artist = request.form.get("artist", "").strip()
    link = parse_link(request.form.get("url", ""))

    if not title or not artist:
        flash("Title and artist are required")
        return redirect("/add")
    if link is None:
        flash("Paste a valid Spotify track or YouTube link")
        return redirect("/add")

    embed_type, embed_id = link
    suggested = suggest_moods(get_lastfm_tags(artist, title))

    moods = db.execute("SELECT id, name FROM moods ORDER BY name")
    for m in moods:
        m["suggested"] = m["name"] in suggested

    return render_template(
        "confirm.html",
        title=title, artist=artist,
        embed_type=embed_type, embed_id=embed_id,
        moods=moods,
    )


@app.route("/save", methods=["POST"])
@login_required
def save():
    """Step 2: save the song with the moods the user confirmed."""
    title = request.form.get("title", "").strip()
    artist = request.form.get("artist", "").strip()
    embed_type = request.form.get("embed_type")
    embed_id = request.form.get("embed_id")

    if not (title and artist and embed_type in ("spotify", "youtube") and embed_id):
        flash("Something went wrong, please try again")
        return redirect("/add")

    chosen = request.form.getlist("moods")           # mood ids the user kept checked
    auto = set(request.form.getlist("auto_moods"))   # mood ids that were suggested

    song_id = db.execute(
        "INSERT INTO songs (user_id, title, artist, embed_type, embed_id) "
        "VALUES (?, ?, ?, ?, ?)",
        session["user_id"], title, artist, embed_type, embed_id,
    )
    for mood_id in chosen:
        db.execute(
            "INSERT INTO song_moods (song_id, mood_id, source) VALUES (?, ?, ?)",
            song_id, mood_id, "auto" if mood_id in auto else "manual",
        )

    flash("Song added!")
    return redirect("/")


# ---------- Playlists ----------

def days_since(timestamp):
    """Days since a SQLite 'YYYY-MM-DD HH:MM:SS' UTC timestamp."""
    then = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    return (datetime.utcnow() - then).total_seconds() / 86400


def weighted_sample(items, weights, k):
    """Pick up to k items without replacement, favouring higher weights."""
    keyed = [(random.random() ** (1 / w), item) for item, w in zip(items, weights)]
    keyed.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in keyed[:k]]


def build_playlist(user_id, mood_id, length):
    """Return songs tagged with the mood, chosen by past ratings and recency."""
    songs = db.execute(
        "SELECT s.id, s.title, s.artist, s.embed_type, s.embed_id "
        "FROM songs s JOIN song_moods sm ON sm.song_id = s.id "
        "WHERE s.user_id = ? AND sm.mood_id = ?",
        user_id, mood_id,
    )

    # Past ratings (AVG ignores NULLs) and last play time, for this mood only
    history = {
        row["song_id"]: row
        for row in db.execute(
            "SELECT l.song_id, AVG(l.rating) AS avg_rating, MAX(ml.timestamp) AS last_played "
            "FROM listens l JOIN mood_logs ml ON ml.id = l.mood_log_id "
            "WHERE ml.user_id = ? AND ml.mood_id = ? GROUP BY l.song_id",
            user_id, mood_id,
        )
    }

    weights = []
    for song in songs:
        past = history.get(song["id"])
        weight = DEFAULT_WEIGHT
        if past:
            if past["avg_rating"] is not None:
                weight = max(past["avg_rating"], 0.5)
            if past["last_played"] and days_since(past["last_played"]) < RECENT_DAYS:
                weight *= RECENT_PENALTY
        weights.append(weight)

    return weighted_sample(songs, weights, length)


@app.route("/playlist", methods=["GET", "POST"])
@login_required
def playlist():
    """GET: mood picker. POST: generate, save the listens, redirect to the result."""
    moods = db.execute("SELECT id, name FROM moods ORDER BY name")

    if request.method == "GET":
        return render_template("playlist_form.html", moods=moods, default_length=DEFAULT_LENGTH)

    valid_ids = {str(m["id"]) for m in moods}
    mood_id = request.form.get("mood_id")
    if mood_id not in valid_ids:
        flash("Pick a mood")
        return redirect("/playlist")

    try:
        length = int(request.form.get("length", DEFAULT_LENGTH))
    except ValueError:
        length = DEFAULT_LENGTH
    length = max(1, min(length, MAX_LENGTH))

    songs = build_playlist(session["user_id"], mood_id, length)
    if not songs:
        flash("No songs tagged with that mood yet. Add some first!")
        return redirect("/playlist")

    log_id = db.execute(
        "INSERT INTO mood_logs (user_id, mood_id) VALUES (?, ?)",
        session["user_id"], mood_id,
    )
    for song in songs:
        db.execute(
            "INSERT INTO listens (mood_log_id, song_id) VALUES (?, ?)",
            log_id, song["id"],
        )
    return redirect(f"/playlist/{log_id}")


@app.route("/playlist/<int:log_id>")
@login_required
def view_playlist(log_id):
    """Show a generated playlist with embedded players and rating buttons."""
    log = db.execute(
        "SELECT ml.id, ml.timestamp, m.name AS mood "
        "FROM mood_logs ml JOIN moods m ON m.id = ml.mood_id "
        "WHERE ml.id = ? AND ml.user_id = ?",
        log_id, session["user_id"],
    )
    if not log:
        flash("Playlist not found")
        return redirect("/playlist")

    tracks = db.execute(
        "SELECT l.id AS listen_id, l.rating, s.title, s.artist, s.embed_type, s.embed_id "
        "FROM listens l JOIN songs s ON s.id = l.song_id "
        "WHERE l.mood_log_id = ? ORDER BY l.id",
        log_id,
    )
    return render_template("playlist.html", log=log[0], tracks=tracks)


@app.route("/rate", methods=["POST"])
@login_required
def rate():
    """Save a 1-5 rating for how well a song fit the mood."""
    try:
        listen_id = int(request.form.get("listen_id"))
        rating = int(request.form.get("rating"))
    except (TypeError, ValueError):
        flash("Invalid rating")
        return redirect("/playlist")
    if not 1 <= rating <= 5:
        flash("Rating must be between 1 and 5")
        return redirect("/playlist")

    # Make sure this listen belongs to the logged-in user
    row = db.execute(
        "SELECT l.id, l.mood_log_id FROM listens l "
        "JOIN mood_logs ml ON ml.id = l.mood_log_id "
        "WHERE l.id = ? AND ml.user_id = ?",
        listen_id, session["user_id"],
    )
    if not row:
        flash("Not found")
        return redirect("/playlist")

    db.execute("UPDATE listens SET rating = ? WHERE id = ?", rating, listen_id)
    return redirect(f"/playlist/{row[0]['mood_log_id']}")
