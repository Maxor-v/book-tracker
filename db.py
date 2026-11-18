import sqlite3, os

DB_PATH = "books.db"
COVERS  = "covers"

def init_db():
    os.makedirs(COVERS, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        genre TEXT DEFAULT '',
        status TEXT DEFAULT 'planned',
        rating INTEGER DEFAULT 0,
        review TEXT DEFAULT '',
        cover_path TEXT DEFAULT '',
        starred INTEGER DEFAULT 0,
        date_added TEXT DEFAULT CURRENT_TIMESTAMP,
        date_read TEXT
    )""")
    con.commit(); con.close()

def db():
    return sqlite3.connect(DB_PATH)

def get_books(status=None, search=None):
    q = "SELECT id,title,author,genre,status,rating,cover_path,starred FROM books"
    where, args = [], []
    if status and status != "all":
        where.append("status=?"); args.append(status)
    if search:
        where.append("(title LIKE ? OR author LIKE ? OR genre LIKE ?)")
        s = f"%{search}%"
        args += [s, s, s]
    if where:
        q += " WHERE " + " AND ".join(where)
    q += " ORDER BY starred DESC, date_added DESC"
    con = db()
    rows = con.execute(q, args).fetchall()
    con.close()
    return rows

def get_book(bid):
    con = db()
    row = con.execute(
        "SELECT title,author,genre,status,rating,review,cover_path "
        "FROM books WHERE id=?", (bid,)
    ).fetchone()
    con.close()
    return row

def get_stats():
    con = db()
    total, read, avg = con.execute(
        "SELECT COUNT(*), SUM(status='read'), AVG(NULLIF(rating,0)) FROM books"
    ).fetchone()
    con.close()
    return {"total": total or 0, "read": read or 0, "avg": avg}

def add_book(data):
    con = db()
    con.execute(
        "INSERT INTO books (title,author,genre,status,rating,review,cover_path) "
        "VALUES (?,?,?,?,?,?,?)", data
    )
    con.commit(); con.close()

def update_book(bid, data):
    con = db()
    prev = con.execute("SELECT status FROM books WHERE id=?", (bid,)).fetchone()
    prev_status = prev[0] if prev else None
    con.execute(
        "UPDATE books SET title=?,author=?,genre=?,status=?,rating=?,"
        "review=?,cover_path=? WHERE id=?", data + (bid,)
    )
    new_status = data[3]
    if new_status == "read" and prev_status != "read":
        con.execute("UPDATE books SET date_read=CURRENT_TIMESTAMP WHERE id=?", (bid,))
    elif new_status != "read":
        con.execute("UPDATE books SET date_read=NULL WHERE id=?", (bid,))
    con.commit(); con.close()

def delete_book(bid):
    con = db()
    con.execute("DELETE FROM books WHERE id=?", (bid,))
    con.commit(); con.close()

def toggle_star(bid):
    con = db()
    cur = con.execute("SELECT starred FROM books WHERE id=?", (bid,)).fetchone()[0]
    con.execute("UPDATE books SET starred=? WHERE id=?", (0 if cur else 1, bid))
    con.commit(); con.close()

def set_status(bid, status):
    con = db()
    if status == "read":
        con.execute(
            "UPDATE books SET status=?, date_read=CURRENT_TIMESTAMP WHERE id=?",
            (status, bid)
        )
    else:
        con.execute("UPDATE books SET status=?, date_read=NULL WHERE id=?",
                    (status, bid))
    con.commit(); con.close()