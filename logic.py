from db import db

def top_genres(min_rating=4, limit=5):
    """Жанры, которые пользователь высоко оценил (4-5★)."""
    con = db()
    rows = con.execute("""
        SELECT genre, COUNT(*) AS c, AVG(rating) AS a
        FROM books
        WHERE status='read' AND rating >= ? AND genre <> ''
        GROUP BY genre
        ORDER BY c DESC, a DESC
        LIMIT ?
    """, (min_rating, limit)).fetchall()
    con.close()
    return rows  # [(genre, count, avg), ...]

def recommendations(limit=30):
    """Планируемые книги из топ-жанров пользователя."""
    genres_rows = top_genres()
    genres = [g[0] for g in genres_rows]
    con = db()
    if not genres:
        rows = con.execute("""
            SELECT id, title, author, genre, cover_path
            FROM books WHERE status='planned'
            ORDER BY date_added DESC LIMIT ?
        """, (limit,)).fetchall()
    else:
        ph = ",".join("?" * len(genres))
        rows = con.execute(f"""
            SELECT id, title, author, genre, cover_path
            FROM books
            WHERE status='planned' AND genre IN ({ph})
            ORDER BY date_added DESC LIMIT ?
        """, (*genres, limit)).fetchall()
    con.close()
    return rows, genres_rows