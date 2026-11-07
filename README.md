# Mood Playlist Tracker

#### Video Demo: [Watch on YouTube](<YOUR_YOUTUBE_DEMO_URL_HERE>)

- **Author:** Lim Jun Chuan
- **GitHub:** [limjunchuan567](https://github.com/limjunchuan567)
- **edX Username:** limjunchuan567
- **City & Country:** Singapore, Singapore
- **Date Recorded:** November 7, 2026

#### Description:
**Mood Playlist Tracker** is a full-stack web application developed as the final project for Harvard's **CS50x: Introduction to Computer Science**. The application helps users associate songs with specific emotional states or moods, and intelligently generates personalized playlists based on how they currently feel.

By integrating Spotify and YouTube track embeds alongside automatic mood tagging powered by the Last.fm AudioScrobbler API, the application creates a dynamic music companion that learns from user feedback over time.

---

## Key Features

1. **User Authentication & Session Management**:
   - Secure registration and login using Werkzeug's salted password hashing (`generate_password_hash` / `check_password_hash`).
   - Custom `@login_required` decorator to restrict access to authenticated users.
   - Dynamic UI with user sessions and flash notifications for feedback.

2. **Song Ingestion with Auto & Manual Mood Tagging**:
   - Accepts Spotify track links (`open.spotify.com/track/...`) and YouTube URLs (`youtube.com/watch?v=...` or `youtu.be/...`).
   - Automatically queries the **Last.fm API** (`track.gettoptags`) to fetch community tags for the artist and track title, automatically mapping them to preset moods (e.g., `chill` -> `calm`, `melancholy` -> `sad`, `workout` -> `hyped`).
   - Presents a confirmation screen allowing users to review, adjust, add, or remove moods manually before saving.

3. **Intelligent Weighted Playlist Generation**:
   - Allows users to select a mood and desired playlist length (up to 25 songs).
   - Generates customized playlists using a weighted sampling algorithm:
     - Songs rated highly by the user (1–5 scale) for that specific mood receive higher probability weights.
     - Recently played songs within the last 2 days are penalized with a decay factor to encourage variety and prevent repetitive selections.
     - Unrated songs start with a balanced default weight (`3.0`).

4. **Interactive Embedded Playback & Feedback**:
   - Seamlessly embeds Spotify and YouTube players directly in the browser so users can listen without leaving the application.
   - Users can rate each song from 1 to 5 stars on how well it matched their current mood, refining future playlist recommendations.

5. **History & Dashboard**:
   - The home dashboard displays total cataloged songs and the 5 most recent mood sessions.

---

## File Structure & Overview

* **`app.py`**:
  The central Flask web application containing all route definitions, API integrations, and database operations.
  - Handles authentication (`/register`, `/login`, `/logout`).
  - Implements link parsing for Spotify and YouTube embed URLs (`parse_link`).
  - Calls Last.fm to fetch tags and maps them to application moods (`get_lastfm_tags`).
  - Implements the weighted selection algorithm (`build_playlist`, `weighted_sample`, `days_since`).
  - Handles song submission, mood confirmation, playlist generation, and rating submissions (`/rate`).

* **`helpers.py`**:
  Contains utility decorators, specifically `@login_required`, ensuring protected routes redirect unauthorized visitors to the login page.

* **`schema.sql`**:
  The relational SQLite database schema. Enforces referential integrity with foreign key constraints and cascading deletes:
  - `users`: Stores user credentials (`id`, `username`, `hash`).
  - `moods`: Prepopulated global moods (`calm`, `sad`, `happy`, `hyped`, `focused`, `nostalgic`).
  - `songs`: Stores user-submitted songs with `embed_type` (`spotify`/`youtube`), `embed_id`, and `user_id`.
  - `song_moods`: Many-to-many junction table mapping songs to moods with tagging source metadata (`auto` vs `manual`).
  - `mood_logs`: Records each playlist generation request with UTC timestamp.
  - `listens`: Tracks song entries within each playlist session along with optional user ratings (1–5).
  - Explicit indexes (`idx_songs_user`, `idx_song_moods_mood`, `idx_mood_logs_user`, `idx_listens_log`, `idx_listens_song`) to ensure fast queries.

* **`requirements.txt`**:
  Specifies application dependencies:
  - `Flask`
  - `cs50`
  - `requests`

* **`templates/`**:
  Jinja2 templates providing a clean, responsive interface:
  - `layout.html`: Base template with Bootstrap navigation bar, flash message banner, and common styling.
  - `index.html`: Dashboard showing song library stats and recent mood logs.
  - `login.html`: User login form.
  - `register.html`: New user registration form.
  - `add.html`: Form to submit a song via Spotify/YouTube link, title, and artist.
  - `confirm.html`: Review step displaying parsed embed and suggested mood tags from Last.fm.
  - `playlist_form.html`: Form to choose a mood and playlist length.
  - `playlist.html`: Results page displaying embedded audio players and rating controls.

* **`.gitignore`**:
  Prevents tracking SQLite database files (`moodtracker.db`), virtual environments (`.venv`), temporary session data, and sensitive environment variables (`.env`).

---

## Design Decisions

1. **Dual Tagging Strategy (Automated API + Manual Override)**:
   Instead of forcing users to tag every mood by hand or relying solely on potentially noisy crowd-sourced tags, the app adopts a hybrid model. Last.fm's API provides immediate suggestions based on community listening habits, while the `/confirm` step gives users full agency to curate the tags before they enter the database.

2. **Weighted Probability Sampling vs. Simple Randomization**:
   Rather than picking songs completely at random or purely deterministically (like sorting strictly by highest rating), the app uses weighted exponential sampling (`random.random() ** (1 / weight)`). This guarantees that top-rated songs appear frequently while still allowing other tracks and newly added songs an opportunity to be discovered.

3. **Recency Penalty**:
   To avoid repetitive playback of the same favorite songs, a time-decay factor (`RECENT_PENALTY = 0.3`) discounts songs played within the last 48 hours.

4. **Embedded Media Flexibility**:
   Supporting both Spotify and YouTube ensures that users are not locked into a single streaming ecosystem and can catalog music from multiple platforms in one unified interface.

---

## Getting Started

### 1. Prerequisites
- Python 3.10+
- SQLite3

### 2. Installation
Clone the repository and install the requirements:
```bash
git clone https://github.com/limjunchuan567/cs50-final-project.git
cd cs50-final-project
pip install -r requirements.txt
```

### 3. Initialize Database
Initialize the SQLite database schema:
```bash
sqlite3 moodtracker.db < schema.sql
```

### 4. Configure Environment Variables (Optional for Last.fm Auto-Tagging)
Set your secret key and optional Last.fm API key:
```bash
# On Linux / macOS / Git Bash:
export SECRET_KEY="your-secret-key-here"
export LASTFM_API_KEY="your-lastfm-api-key"

# On Windows PowerShell:
$env:SECRET_KEY="your-secret-key-here"
$env:LASTFM_API_KEY="your-lastfm-api-key"
```
*(Note: If `LASTFM_API_KEY` is omitted, song addition will still function with manual mood selection).*

### 5. Run the Application
```bash
flask run
```
Visit `http://127.0.0.1:5000` in your web browser.
