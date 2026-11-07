-- Mood playlist tracker schema (SQLite)
-- Create the database with:  sqlite3 moodtracker.db < schema.sql

PRAGMA foreign_keys = ON;

CREATE TABLE users (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    hash     TEXT NOT NULL
);

-- Moods are shared by all users. Names must match the values in MOOD_MAP (add_song.py).
CREATE TABLE moods (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE songs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    title      TEXT NOT NULL,
    artist     TEXT NOT NULL,
    embed_type TEXT NOT NULL CHECK (embed_type IN ('spotify', 'youtube')),
    embed_id   TEXT NOT NULL,
    added_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Many-to-many: a song can have several moods, a mood has many songs.
-- source records whether the mood came from Last.fm ('auto') or the user ('manual').
CREATE TABLE song_moods (
    song_id INTEGER NOT NULL,
    mood_id INTEGER NOT NULL,
    source  TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('auto', 'manual')),
    PRIMARY KEY (song_id, mood_id),
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
    FOREIGN KEY (mood_id) REFERENCES moods(id) ON DELETE CASCADE
);

-- One row each time the user asks for a playlist for a mood. Timestamp is UTC.
CREATE TABLE mood_logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL,
    mood_id   INTEGER NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (mood_id) REFERENCES moods(id) ON DELETE CASCADE
);

-- The songs included in each generated playlist, plus the optional 1-5 rating.
CREATE TABLE listens (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mood_log_id INTEGER NOT NULL,
    song_id     INTEGER NOT NULL,
    rating      INTEGER CHECK (rating IS NULL OR rating BETWEEN 1 AND 5),
    FOREIGN KEY (mood_log_id) REFERENCES mood_logs(id) ON DELETE CASCADE,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
);

-- Indexes for the queries the app runs most
CREATE INDEX idx_songs_user      ON songs(user_id);
CREATE INDEX idx_song_moods_mood ON song_moods(mood_id);
CREATE INDEX idx_mood_logs_user  ON mood_logs(user_id, mood_id);
CREATE INDEX idx_listens_log     ON listens(mood_log_id);
CREATE INDEX idx_listens_song    ON listens(song_id);

-- Starting moods (the first five are the ones Last.fm tags map to)
INSERT INTO moods (name) VALUES
    ('calm'), ('sad'), ('happy'), ('hyped'), ('focused'), ('nostalgic');
