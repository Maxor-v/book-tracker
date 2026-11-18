"""Первоначальное заполнение БД — 10 книг.
Запускать: python seed.py
Идемпотентно: если база не пуста, ничего не делает."""

import os, sys
from PIL import Image, ImageDraw, ImageFont

import db as dbm


BOOKS = [
    # (title, author, genre, status, rating, review, starred)
    ("Мастер и Маргарита", "Михаил Булгаков", "Роман", "read", 5,
     "Роман о добре и зле, любви и трусости. Одна из вершин мировой литературы.", 1),
    ("Преступление и наказание", "Фёдор Достоевский", "Роман", "read", 5,
     "Глубокое психологическое произведение о вине и искуплении.", 0),
    ("1984", "Джордж Оруэлл", "Антиутопия", "read", 5,
     "Пророческая антиутопия о тоталитаризме и свободе мысли.", 0),
    ("Солярис", "Станислав Лем", "Фантастика", "read", 4,
     "Умная фантастика о невозможности контакта с непознаваемым.", 0),
    ("Дюна", "Фрэнк Герберт", "Фантастика", "planned", 0, "", 0),
    ("Гарри Поттер и философский камень", "Дж. К. Роулинг", "Фэнтези", "read", 4,
     "Тёплая сказка для всех возрастов, начало большой истории.", 0),
    ("Властелин колец", "Дж. Р. Р. Толкин", "Фэнтези", "planned", 0, "", 1),
    ("Три товарища", "Эрих Мария Ремарк", "Роман", "read", 5,
     "История дружбы и любви на фоне потерянного поколения.", 0),
    ("Тень ветра", "Карлос Руис Сафон", "Роман", "planned", 0, "", 0),
    ("Автостопом по галактике", "Дуглас Адамс", "Фантастика", "planned", 0, "", 0),
]

COVER_COLORS = ["#7c5cff", "#3ddc97", "#ff8c42",
                "#4a9eff", "#e94f8a", "#50b4c8"]


def _make_cover(title: str, idx: int) -> str:
    """Простая цветная обложка с первой буквой названия."""
    color = COVER_COLORS[idx % len(COVER_COLORS)]
    size = (200, 300)
    img = Image.new("RGB", size, color)
    d = ImageDraw.Draw(img)
    letter = (title.strip()[:1] or "?").upper()
    try:
        fpath = "arial.ttf" if sys.platform == "win32" else "DejaVuSans-Bold.ttf"
        f = ImageFont.truetype(fpath, 110)
    except Exception:
        f = ImageFont.load_default()
    bb = d.textbbox((0, 0), letter, font=f)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text(((size[0] - w) // 2 - bb[0], (size[1] - h) // 2 - bb[1]),
           letter, fill="white", font=f)
    path = os.path.join(dbm.COVERS, f"seed_{idx + 1}.jpg")
    img.save(path, "JPEG", quality=88)
    return path


def seed(force: bool = False) -> None:
    dbm.init_db()
    con = dbm.db()
    existing = con.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    if existing > 0 and not force:
        print(f"ℹ️  В базе уже {existing} книг(и). Ничего не меняю.\n"
              f"   Для перезаписи: python seed.py --force")
        con.close()
        return

    for i, (title, author, genre, status, rating, review, starred) in \
            enumerate(BOOKS):
        cover = _make_cover(title, i)
        con.execute(
            "INSERT INTO books "
            "(title, author, genre, status, rating, review, cover_path, starred) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (title, author, genre, status, rating, review, cover, starred)
        )
    con.commit()
    con.close()
    print(f"✅ Добавлено {len(BOOKS)} книг, обложки в ./{dbm.COVERS}/")


if __name__ == "__main__":
    seed(force="--force" in sys.argv)