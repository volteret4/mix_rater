# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

`mix_rater` is a personal music collection rating tool. It scans audio files into a SQLite database, lets the user rate each track across 12 subjective dimensions (e.g. alegre/melancólica, relajada/energética), and then surfaces recommendations based on cosine similarity between track vectors.

There are two interfaces:
- **CLI** (`music_rater.py`): scan a directory of audio files, then interactively rate tracks dimension-by-dimension via terminal + deadbeef playback.
- **Web** (`web/app.py`): Flask app on port 5001 with a richer UI for rating, random playback, vector search, and collection stats.

## Running

```bash
# CLI — scan a music directory
python music_rater.py scan /path/to/music

# CLI — rate tracks on a dimension
python music_rater.py rate alegre_melancolica

# Web app (default: 127.0.0.1:5001)
python web/app.py
python web/app.py --port 5002 --host 0.0.0.0
```

Dependencies: `flask`, `mutagen`. Playback uses `deadbeef` (must be in PATH).

## Database

SQLite at `~/Scripts/dbs/music_rater.db`. Schema: one `tracks` table with audio metadata, plus one table per dimension named `d_<dimension>` (e.g. `d_alegre_melancolica`) storing `track_id → value` (integer −5 to +5).

The `conn()` function in both `music_rater.py` and `web/app.py` creates all tables on first connect — no separate migration step needed.

## Architecture

### Dimensions

The 12 dimensions are defined as a list constant `DIMENSIONS` in both `music_rater.py` and `web/app.py` (duplicated) and also in every frontend template/JS file. Any new dimension must be added to all four locations: both Python files and all HTML/JS files that reference `DIMS`.

### Web API endpoints

| Route | Method | Purpose |
|---|---|---|
| `GET /api/random` | GET | Random track (plays it via deadbeef, returns full row) |
| `GET /api/similar/<tid>` | GET | Top-20 cosine-similar tracks to a given track ID |
| `POST /api/search` | POST | Vector search: `{vector: [12 ints]}` → top-30 results |
| `POST /api/save` | POST | Save ratings: `{id, ratings: {dim: value}}` |
| `GET /api/stats` | GET | Coverage, value distributions, genre counts |

### Similarity

Both `similar` and `search` use cosine similarity on the 12-dimensional rating vector. Unrated dimensions default to 0 in `vec()`. The `similar` endpoint iterates all tracks on every request (no index).

### Frontend

Each page (`rate.html`, `recs_random.html`, `recs_vector.html`, `stats.html`) is self-contained — styles are inline, JS is inline or loaded from `web/static/`. The `web/static/recs.js` and `recs_random.js`/`recs_vector.js` files are older standalone JS; the primary UI lives in the HTML templates.
