from flask import Flask, jsonify, request, render_template, Response
import sqlite3
import subprocess
import argparse
import math
import os
from mutagen import File as AudioFile

DB = os.environ.get("MUSIC_RATER_DB", os.path.expanduser("~/Scripts/dbs/music_rater.db"))

DIMENSIONS = [
    "alegre_melancolica",
    "relajada_energetica",
    "instrumental_cantada",
    "lenta_rapida",
    "bailable_nobailable",
    "comercial_experimental",
    "luminosa_oscura",
    "fondo_atencion",
    "fluida_percusiva",
    "estatica_dinamica",
    "reflexiva_fisica",
    "intima_epica",
]

app = Flask(__name__)


# ---------------- DB ----------------

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("""
    CREATE TABLE IF NOT EXISTS stars (
        track_id INTEGER,
        dimension TEXT,
        PRIMARY KEY (track_id, dimension)
    )
    """)
    return c


# ---------------- COVER ART ----------------

def get_cover(path):
    try:
        f = AudioFile(path)
        if f is None:
            return None, None
        if hasattr(f, 'pictures') and f.pictures:
            p = f.pictures[0]
            return p.data, p.mime
        tags = getattr(f, 'tags', None)
        if not tags:
            return None, None
        for key in list(tags.keys()):
            if key.startswith('APIC'):
                apic = tags[key]
                return apic.data, apic.mime
        if 'covr' in tags:
            from mutagen.mp4 import MP4Cover
            cover = tags['covr'][0]
            mime = 'image/jpeg' if cover.imageformat == MP4Cover.FORMAT_JPEG else 'image/png'
            return bytes(cover), mime
    except Exception:
        pass
    return None, None


# ---------------- METADATA WRITE ----------------

def save_meta(path, genre=None, comments=None):
    try:
        ext = os.path.splitext(path)[1].lower()
        f = AudioFile(path)
        if f is None:
            return False
        if ext in ('.flac', '.ogg', '.oga', '.opus'):
            if genre is not None:
                f.tags['genre'] = [genre]
            if comments is not None:
                f.tags['comment'] = [comments]
            f.save()
        elif ext == '.mp3':
            from mutagen.id3 import TCON, COMM
            if f.tags is None:
                f.add_tags()
            if genre is not None:
                f.tags.setall('TCON', [TCON(encoding=3, text=genre)])
            if comments is not None:
                f.tags.setall('COMM', [COMM(encoding=3, lang='eng', desc='', text=comments)])
            f.save()
        elif ext in ('.m4a', '.mp4', '.aac'):
            if genre is not None:
                f.tags['\xa9gen'] = [genre]
            if comments is not None:
                f.tags['\xa9cmt'] = [comments]
            f.save()
        return True
    except Exception:
        return False


# ---------------- PENDING HELPER ----------------

def rated_dims_expr():
    parts = [
        f"CASE WHEN EXISTS (SELECT 1 FROM d_{d} WHERE track_id=t.id) THEN 1 ELSE 0 END"
        for d in DIMENSIONS
    ]
    return "(" + " + ".join(parts) + ")"


# ---------------- VECTOR ----------------

def vec(c, track_id):
    v = []
    for d in DIMENSIONS:
        r = c.execute(
            f"SELECT value FROM d_{d} WHERE track_id=?",
            (track_id,)
        ).fetchone()
        v.append(r["value"] if r else 0)
    return v


def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(x*x for x in b))
    return dot / (na * nb) if na and nb else 0


# ---------------- PLAYER ----------------

def play(path):
    subprocess.Popen(["deadbeef", path])


# ---------------- PAGES ----------------

@app.route("/")
def rate():
    return render_template("rate.html")


@app.route("/recs/random")
def recs_random():
    return render_template("recs_random.html")


@app.route("/recs/vector")
def recs_vector():
    return render_template("recs_vector.html")


@app.route("/stats")
def stats():
    return render_template("stats.html")


@app.route("/dominios")
def dominios():
    return render_template("dominios.html")


# ---------------- API RANDOM ----------------

@app.route("/api/random")
def random_track():
    c = conn()
    row = c.execute("SELECT * FROM tracks ORDER BY RANDOM() LIMIT 1").fetchone()
    c.close()
    play(row["path"])
    return jsonify(dict(row))


# ---------------- API NEXT (smart selection) ----------------

def _track_genres(track):
    """Split genre field on ';' → list of stripped genre strings."""
    g = track["genre"] or ""
    return [x.strip() for x in g.split(";") if x.strip()]


@app.route("/api/next")
def next_track():
    last_id = request.args.get("last", type=int)
    folder  = request.args.get("folder")   # lock to this directory path
    genre   = request.args.get("genre")    # lock to this genre token
    c = conn()

    dim_expr = rated_dims_expr()
    n = len(DIMENSIONS)
    total = c.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    rated_count = c.execute(
        f"SELECT COUNT(*) FROM tracks t WHERE {dim_expr} = {n}"
    ).fetchone()[0]

    pending_cond = f"{dim_expr} < {n}"
    row = None

    if folder:
        # Filter to a specific directory (dirname comparison must happen in Python)
        candidates = c.execute(
            f"SELECT t.* FROM tracks t WHERE {pending_cond} ORDER BY t.id"
        ).fetchall()
        row = next((t for t in candidates if os.path.dirname(t["path"]) == folder), None)

    elif genre:
        # Filter by individual genre token (handles ";" separator)
        candidates = c.execute(
            f"SELECT t.* FROM tracks t WHERE {pending_cond} ORDER BY t.id"
        ).fetchall()
        row = next((t for t in candidates if genre in _track_genres(t)), None)

    else:
        # Smart selection: same dir > same artist > same album > any
        if last_id:
            last = c.execute(
                "SELECT path, artist, album FROM tracks WHERE id=?", (last_id,)
            ).fetchone()
            if last:
                last_dir = os.path.dirname(last["path"])

                all_pending = c.execute(
                    f"SELECT t.* FROM tracks t WHERE {pending_cond} AND t.id != ? ORDER BY t.id",
                    (last_id,)
                ).fetchall()

                for t in all_pending:
                    if os.path.dirname(t["path"]) == last_dir:
                        row = t
                        break

                if not row and last["artist"]:
                    row = c.execute(
                        f"SELECT t.* FROM tracks t WHERE {pending_cond} AND t.id != ? AND t.artist = ? ORDER BY t.id LIMIT 1",
                        (last_id, last["artist"])
                    ).fetchone()

                if not row and last["album"]:
                    row = c.execute(
                        f"SELECT t.* FROM tracks t WHERE {pending_cond} AND t.id != ? AND t.album = ? ORDER BY t.id LIMIT 1",
                        (last_id, last["album"])
                    ).fetchone()

                if not row and all_pending:
                    row = all_pending[0]

        if not row:
            row = c.execute(
                f"SELECT t.* FROM tracks t WHERE {pending_cond} ORDER BY t.id LIMIT 1"
            ).fetchone()

    if not row:
        c.close()
        return jsonify({"done": True, "total": total, "rated": rated_count, "pending": 0})

    starred_dims = [r["dimension"] for r in c.execute(
        "SELECT dimension FROM stars WHERE track_id=?", (row["id"],)
    ).fetchall()]
    c.close()

    play(row["path"])
    return jsonify({
        **dict(row),
        "total": total,
        "rated": rated_count,
        "pending": total - rated_count,
        "starred_dims": starred_dims,
    })


@app.route("/api/sidebar")
def sidebar():
    from collections import defaultdict
    c = conn()
    dim_expr = rated_dims_expr()
    n = len(DIMENSIONS)
    pending_cond = f"{dim_expr} < {n}"

    pending_rows = c.execute(
        f"SELECT path, genre FROM tracks t WHERE {pending_cond}"
    ).fetchall()
    c.close()

    # Folders: group by dirname, display as last 2 path components
    folder_counts = defaultdict(int)
    for r in pending_rows:
        folder_counts[os.path.dirname(r["path"])] += 1

    folders = []
    for path, count in sorted(folder_counts.items(), key=lambda x: x[0].lower()):
        parts = [p for p in path.split("/") if p]
        display = "/".join(parts[-2:]) if len(parts) >= 2 else (parts[-1] if parts else path)
        folders.append({"path": path, "display": display, "pending": count})

    # Genres: split on ";", count per token
    genre_counts = defaultdict(int)
    for r in pending_rows:
        for g in _track_genres(r):
            genre_counts[g] += 1

    genres = sorted(
        [{"genre": g, "pending": c} for g, c in genre_counts.items()],
        key=lambda x: (-x["pending"], x["genre"].lower()),
    )

    return jsonify({"folders": folders, "genres": genres})


# ---------------- API COVER ART ----------------

@app.route("/api/art/<int:tid>")
def art(tid):
    c = conn()
    row = c.execute("SELECT path FROM tracks WHERE id=?", (tid,)).fetchone()
    c.close()
    if not row:
        return '', 404
    data, mime = get_cover(row['path'])
    if not data:
        return '', 404
    resp = Response(data, mimetype=mime)
    resp.headers['Cache-Control'] = 'public, max-age=86400'
    return resp


# ---------------- API META SAVE ----------------

@app.route("/api/meta/<int:tid>", methods=["POST"])
def meta_save(tid):
    c = conn()
    row = c.execute("SELECT path FROM tracks WHERE id=?", (tid,)).fetchone()
    if not row:
        c.close()
        return jsonify({"ok": False}), 404
    data = request.json
    genre = data.get("genre")
    comments = data.get("comments")
    if genre is not None:
        c.execute("UPDATE tracks SET genre=? WHERE id=?", (genre, tid))
    if comments is not None:
        c.execute("UPDATE tracks SET comments=? WHERE id=?", (comments, tid))
    c.commit()
    c.close()
    ok = save_meta(row["path"], genre=genre, comments=comments)
    return jsonify({"ok": ok})


# ---------------- API PLAY ----------------

@app.route("/api/track/<int:tid>")
def track_by_id(tid):
    c = conn()
    row = c.execute("SELECT * FROM tracks WHERE id=?", (tid,)).fetchone()
    if not row:
        c.close()
        return jsonify({"error": "not found"}), 404
    dim_expr = rated_dims_expr()
    n = len(DIMENSIONS)
    total = c.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    rated_count = c.execute(
        f"SELECT COUNT(*) FROM tracks t WHERE {dim_expr} = {n}"
    ).fetchone()[0]
    starred_dims = [r["dimension"] for r in c.execute(
        "SELECT dimension FROM stars WHERE track_id=?", (tid,)
    ).fetchall()]
    ratings = {}
    for d in DIMENSIONS:
        r = c.execute(f"SELECT value FROM d_{d} WHERE track_id=?", (tid,)).fetchone()
        if r is not None:
            ratings[d] = r["value"]
    c.close()
    play(row["path"])
    return jsonify({
        **dict(row),
        "total": total,
        "rated": rated_count,
        "pending": total - rated_count,
        "starred_dims": starred_dims,
        "ratings": ratings,
    })


@app.route("/api/play/<int:tid>")
def play_track(tid):
    c = conn()
    row = c.execute("SELECT path FROM tracks WHERE id=?", (tid,)).fetchone()
    c.close()
    if not row:
        return jsonify({"ok": False}), 404
    play(row["path"])
    return jsonify({"ok": True})


# ---------------- API SIMILAR ----------------

def _track_summary(r, sim=None):
    d = {
        "id": r["id"],
        "artist": r["artist"],
        "title": r["title"],
        "album": r["album"],
        "genre": r["genre"],
        "year": r["year"],
        "bpm": r["bpm"],
        "label": r["label"],
        "comments": r["comments"],
    }
    if sim is not None:
        d["sim"] = sim
    return d


@app.route("/api/similar/<int:tid>")
def similar(tid):
    c = conn()
    base = vec(c, tid)
    tracks = c.execute("SELECT id FROM tracks").fetchall()
    scores = []
    for t in tracks:
        if t["id"] == tid:
            continue
        v = vec(c, t["id"])
        scores.append((cosine(base, v), t["id"]))
    scores.sort(reverse=True)
    out = []
    for s, tid2 in scores[:20]:
        r = c.execute("SELECT * FROM tracks WHERE id=?", (tid2,)).fetchone()
        out.append(_track_summary(r, sim=s))
    c.close()
    return jsonify(out)


# ---------------- API VECTOR SEARCH ----------------

@app.route("/api/search", methods=["POST"])
def search():
    c = conn()
    user = request.json["vector"]
    tracks = c.execute("SELECT id FROM tracks").fetchall()
    scores = []
    for t in tracks:
        v = vec(c, t["id"])
        scores.append((cosine(user, v), t["id"]))
    scores.sort(reverse=True)
    out = []
    for s, tid in scores[:30]:
        r = c.execute("SELECT * FROM tracks WHERE id=?", (tid,)).fetchone()
        out.append(_track_summary(r, sim=s))
    c.close()
    return jsonify(out)


# ---------------- API STAR ----------------

@app.route("/api/star", methods=["POST"])
def star_toggle():
    data = request.json
    tid = data["track_id"]
    dim = data["dimension"]
    if dim not in DIMENSIONS:
        return jsonify({"ok": False}), 400
    c = conn()
    existing = c.execute(
        "SELECT 1 FROM stars WHERE track_id=? AND dimension=?", (tid, dim)
    ).fetchone()
    if existing:
        c.execute("DELETE FROM stars WHERE track_id=? AND dimension=?", (tid, dim))
        starred = False
    else:
        c.execute("INSERT INTO stars (track_id, dimension) VALUES (?, ?)", (tid, dim))
        starred = True
    c.commit()
    c.close()
    return jsonify({"starred": starred})


# ---------------- API SAVE ----------------

@app.route("/api/save", methods=["POST"])
def save():
    c = conn()
    data = request.json
    tid = data["id"]
    ratings = data["ratings"]
    for d, v in ratings.items():
        c.execute(
            f"INSERT OR REPLACE INTO d_{d} (track_id, value) VALUES (?, ?)",
            (tid, v)
        )
    c.commit()
    c.close()
    return jsonify({"ok": True})


# ---------------- API STATS ----------------

@app.route("/api/stats")
def stats_api():
    c = conn()
    total = c.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    coverage = {}
    for d in DIMENSIONS:
        rated = c.execute(f"SELECT COUNT(*) FROM d_{d}").fetchone()[0]
        coverage[d] = {"rated": rated, "total": total, "pct": (rated / total) if total else 0}
    distributions = {}
    for d in DIMENSIONS:
        rows = c.execute(f"SELECT value, COUNT(*) as cnt FROM d_{d} GROUP BY value").fetchall()
        distributions[d] = {str(r["value"]): r["cnt"] for r in rows}
    genres = c.execute("""
        SELECT genre, COUNT(*) as count FROM tracks
        WHERE genre IS NOT NULL AND genre != ''
        GROUP BY genre ORDER BY count DESC LIMIT 50
    """).fetchall()
    c.close()
    return jsonify({
        "total_tracks": total,
        "coverage": coverage,
        "distributions": distributions,
        "genres": [{"genre": g["genre"], "count": g["count"]} for g in genres],
    })


# ---------------- API DIMENSION ----------------

@app.route("/api/dimension/<dim>")
def dimension_api(dim):
    if dim not in DIMENSIONS:
        return jsonify([]), 400
    include_unrated = request.args.get("unrated", "0") == "1"
    join_type = "LEFT JOIN" if include_unrated else "JOIN"
    c = conn()
    rows = c.execute(f"""
        SELECT t.id, t.path, t.artist, t.title, t.album, t.genre, r.value,
               CASE WHEN s.track_id IS NOT NULL THEN 1 ELSE 0 END AS starred
        FROM tracks t
        {join_type} d_{dim} r ON t.id = r.track_id
        LEFT JOIN stars s ON t.id = s.track_id AND s.dimension = ?
        ORDER BY
            CASE WHEN r.value IS NULL THEN 1 ELSE 0 END,
            r.value, t.artist, t.title
    """, (dim,)).fetchall()
    c.close()
    return jsonify([dict(r) for r in rows])


# ---------------- CLI ----------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=5001)
    p.add_argument("--host", default="127.0.0.1")
    args = p.parse_args()
    app.run(host=args.host, port=args.port, debug=True)


if __name__ == "__main__":
    main()
