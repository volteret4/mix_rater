#!/usr/bin/env python3
import argparse
import os
import sqlite3
import subprocess
from pathlib import Path
from mutagen import File as AudioFile

DB = os.path.expanduser("~/Scripts/dbs/music_rater.db")

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


# ---------------- DB ----------------

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row

    c.execute("""
    CREATE TABLE IF NOT EXISTS tracks (
        id INTEGER PRIMARY KEY,
        path TEXT UNIQUE,
        artist TEXT,
        album TEXT,
        title TEXT,
        genre TEXT,
        year TEXT,
        bpm REAL,
        key TEXT,
        comments TEXT,
        label TEXT
    )
    """)

    for d in DIMENSIONS:
        c.execute(f"""
        CREATE TABLE IF NOT EXISTS d_{d} (
            track_id INTEGER PRIMARY KEY,
            value INTEGER
        )
        """)

    return c


# ---------------- METADATA ----------------

def meta(path):
    audio = AudioFile(path, easy=True)
    if not audio:
        return {}

    def g(x):
        return audio.get(x, [None])[0]

    return {
        "artist": g("artist"),
        "album": g("album"),
        "title": g("title"),
        "genre": g("genre"),
        "year": g("date"),
        "bpm": g("bpm"),
        "key": g("initialkey"),
        "comments": g("comment"),
        "label": g("label"),
    }


# ---------------- SCAN ----------------

def scan(root):
    c = conn()
    cur = c.cursor()

    exts = {".flac", ".mp3", ".ogg", ".wav", ".m4a"}

    for f in Path(root).rglob("*"):
        if f.suffix.lower() not in exts:
            continue

        m = meta(f)

        cur.execute("""
        INSERT OR IGNORE INTO tracks
        (path, artist, album, title, genre, year, bpm, key, comments, label)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(f),
            m.get("artist"),
            m.get("album"),
            m.get("title"),
            m.get("genre"),
            m.get("year"),
            m.get("bpm"),
            m.get("key"),
            m.get("comments"),
            m.get("label"),
        ))

    c.commit()
    c.close()


# ---------------- PLAY ----------------

def play(path):
    subprocess.Popen(["deadbeef", path])


# ---------------- NEXT TRACK ----------------

def next_track(c, dim, force):
    table = f"d_{dim}"

    if force:
        return c.execute("""
        SELECT * FROM tracks ORDER BY id LIMIT 1
        """).fetchone()

    return c.execute(f"""
        SELECT t.*
        FROM tracks t
        LEFT JOIN {table} r
        ON t.id = r.track_id
        WHERE r.value IS NULL
        ORDER BY t.id
        LIMIT 1
    """).fetchone()


# ---------------- SAVE ----------------

def save(c, track_id, dim, value):
    table = f"d_{dim}"

    c.execute(f"""
    INSERT OR REPLACE INTO {table} (track_id, value)
    VALUES (?, ?)
    """, (track_id, value))

    c.commit()


# ---------------- RATING LOOP ----------------

def rate(dim, force):
    if dim not in DIMENSIONS:
        print("Dimensión inválida")
        return

    c = conn()

    while True:
        row = next_track(c, dim, force)

        if not row:
            print("✔ FIN de canciones para esta dimensión")
            break

        track_id = row["id"]
        path = row["path"]
        artist = row["artist"] or "Unknown"
        album = row["album"] or "Unknown"
        title = row["title"] or Path(path).stem
        genre = row["genre"] or "Unknown"
        year = row["year"] or "Unknown"

        print("\n" + "=" * 70)
        print(f"{artist} - {title}")
        print(f"{album} | {genre} | {year}")
        print("=" * 70)

        print(f"\nDIMENSION: {dim}")
        print("Escala: -5 .. 5")
        print("q = salir | s = saltar\n")

        play(path)

        while True:
            v = input("valor> ").strip()

            if v == "q":
                c.close()
                return

            if v == "s":
                break

            try:
                val = int(v)
                if val < -5 or val > 5:
                    raise ValueError()
            except ValueError:
                print("Valor inválido")
                continue

            save(c, track_id, dim, val)
            break

    c.close()


# ---------------- CLI ----------------

def main():
    p = argparse.ArgumentParser()

    sub = p.add_subparsers(dest="cmd")

    sc = sub.add_parser("scan")
    sc.add_argument("root")

    rt = sub.add_parser("rate")
    rt.add_argument("dimension")
    rt.add_argument("--force-update", action="store_true")

    args = p.parse_args()

    if args.cmd == "scan":
        scan(args.root)

    if args.cmd == "rate":
        rate(args.dimension, args.force_update)


if __name__ == "__main__":
    main()
