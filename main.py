import os, sys, shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageDraw, ImageFont, ImageTk

import db as dbm
import logic
import settings

# ---------- CONFIG ----------
BG, SURFACE, SURFACE2 = "#1e1f29", "#282a3a", "#32344a"
ACCENT, ACCENT2 = "#7c5cff", "#6a4ae0"
TEXT, MUTED = "#e8e8f0", "#8a8fa8"
STAR, STAR_OFF = "#ffcc33", "#4a4d66"
GREEN = "#3ddc97"

def pick_font():
    return {"win32": "Segoe UI",
            "darwin": "Helvetica Neue"}.get(sys.platform, "DejaVu Sans")
FONT = pick_font()

# ---------- ICONS (PIL) ----------
def make_book_icon(size=28):
    """Открытая книга: две страницы."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = 3
    mid = size // 2
    d.rounded_rectangle([pad, pad + 1, mid - 1, size - pad],
                        radius=3, fill=ACCENT)
    d.rounded_rectangle([mid + 1, pad + 1, size - pad, size - pad],
                        radius=3, fill="#a08aff")
    return img

def make_search_icon(size=16):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([1, 1, size - 5, size - 5], outline=MUTED, width=2)
    d.line([size - 6, size - 6, size - 1, size - 1], fill=MUTED, width=2)
    return img

# ---------- IMAGES ----------
_ph_cache = {}
def placeholder(text, size=(64, 90)):
    letter = ((text or "").strip()[:1] or "?").upper()
    key = (letter, size)
    if key in _ph_cache:
        return _ph_cache[key]
    img = Image.new("RGB", size, SURFACE2)
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype(
            "arial.ttf" if sys.platform == "win32"
            else "DejaVuSans-Bold.ttf", 40)
    except Exception:
        f = ImageFont.load_default()
    bb = d.textbbox((0, 0), letter, font=f)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    d.text(((size[0] - w) // 2 - bb[0], (size[1] - h) // 2 - bb[1]),
           letter, fill=TEXT, font=f)
    _ph_cache[key] = img
    return img

def load_cover(path, size=(64, 90)):
    if path and os.path.exists(path):
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail(size, Image.LANCZOS)
            canvas = Image.new("RGB", size, SURFACE2)
            canvas.paste(img,
                         ((size[0] - img.width) // 2,
                          (size[1] - img.height) // 2))
            return canvas
        except Exception:
            pass
    return None

def rounded(img, r=6):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, img.width - 1, img.height - 1], radius=r, fill=255)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out

# ---------- APP ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Трекер книг")
        cfg = settings.load()
        self.geometry(cfg["geometry"])
        self.configure(bg=BG)
        self._imgs, self._rec_imgs = {}, {}
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._style()
        self._ui()
        self.status_var.set(cfg["status"])
        self.search_var.set(cfg["search"])
        self.refresh()
        self.refresh_recommendations()

    def _on_close(self):
        settings.save(geometry=self.winfo_geometry(),
                      status=self.status_var.get(),
                      search=self.search_var.get())
        self.destroy()

    # ---------- STYLE ----------
    def _style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure(".", background=BG, foreground=TEXT, font=(FONT, 10))

        # Notebook: выбранная вкладка заметно больше
        s.configure("TNotebook", background=BG, borderwidth=0,
                    tabmargins=(8, 6, 8, 0))
        s.configure("TNotebook.Tab",
                    background=SURFACE, foreground=MUTED,
                    padding=(16, 9), borderwidth=0, font=(FONT, 10))
        s.map("TNotebook.Tab",
              background=[("selected", ACCENT)],
              foreground=[("selected", "#ffffff")],
              font=[("selected", (FONT, 12, "bold")),
                    ("!selected", (FONT, 10))],
              padding=[("selected", (24, 14)),
                       ("!selected", (16, 9))],
              expand=[("selected", (3, 3, 3, 0)),
                      ("!selected", (0, 0, 0, 0))])

        s.configure("Treeview", background=SURFACE, fieldbackground=SURFACE,
                    foreground=TEXT, rowheight=100, borderwidth=0,
                    font=(FONT, 10))
        s.map("Treeview",
              background=[("selected", ACCENT)],
              foreground=[("selected", "#ffffff")])
        s.configure("Treeview.Heading", background=BG, foreground=MUTED,
                    borderwidth=0, font=(FONT, 9, "bold"))
        s.map("Treeview.Heading", background=[("active", BG)])

        s.configure("Accent.TButton", background=ACCENT, foreground="white",
                    borderwidth=0, padding=(14, 10),
                    font=(FONT, 10, "bold"))
        s.map("Accent.TButton", background=[("active", ACCENT2)])
        s.configure("Ghost.TButton", background=SURFACE, foreground=TEXT,
                    borderwidth=0, padding=(12, 10), font=(FONT, 10))
        s.map("Ghost.TButton", background=[("active", SURFACE2)])

    # ---------- UI ----------
    def _ui(self):
        # --- HEADER ---
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=16, pady=(16, 8))

        title_frame = tk.Frame(header, bg=BG)
        title_frame.pack(side="left")
        self._header_icon = ImageTk.PhotoImage(make_book_icon(30))
        tk.Label(title_frame, image=self._header_icon, bg=BG).pack(
            side="left", padx=(0, 10))
        tk.Label(title_frame, text="Трекер книг", bg=BG, fg=TEXT,
                 font=(FONT, 20, "bold")).pack(side="left")

        # Кнопки справа: [✎ Редактировать] [+ Добавить]
        ttk.Button(header, text="+ Добавить", style="Accent.TButton",
                   command=self.add_book).pack(side="right", padx=(8, 0))
        ttk.Button(header, text="✎ Редактировать", style="Ghost.TButton",
                   command=self.edit_selected).pack(side="right")

        # --- NOTEBOOK ---
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.books_tab = tk.Frame(self.notebook, bg=BG)
        self.recs_tab = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.books_tab, text="Мои книги")
        self.notebook.add(self.recs_tab, text="Рекомендации")
        self.notebook.bind("<<NotebookTabChanged>>",
                           lambda e: self.refresh_recommendations())

        self._build_books_tab()
        self._build_recs_tab()

        self.search_var.trace_add("write", lambda *a: self.refresh())

    def _build_books_tab(self):
        tab = self.books_tab
        top = tk.Frame(tab, bg=BG)
        top.pack(fill="x", pady=(12, 8))

        self.status_var = tk.StringVar(value="all")
        self.search_var = tk.StringVar(value="")

        for lbl, val in [("Все", "all"), ("Читаю", "reading"),
                         ("Прочитано", "read"), ("В планах", "planned")]:
            tk.Radiobutton(top, text=lbl, value=val,
                           variable=self.status_var, command=self.refresh,
                           bg=BG, fg=MUTED, selectcolor=SURFACE,
                           activebackground=BG, activeforeground=ACCENT,
                           indicatoron=False, padx=12, pady=6, bd=0,
                           font=(FONT, 9)).pack(side="left", padx=(0, 6))

        # Поиск
        search_wrap = tk.Frame(top, bg=SURFACE, padx=10, pady=2)
        search_wrap.pack(side="right")
        self._search_icon = ImageTk.PhotoImage(make_search_icon(16))
        tk.Label(search_wrap, image=self._search_icon, bg=SURFACE).pack(
            side="left", padx=(0, 6))
        tk.Entry(search_wrap, textvariable=self.search_var, bg=SURFACE,
                 fg=TEXT, insertbackground=TEXT, bd=0, width=22,
                 font=(FONT, 10)).pack(side="left", ipady=6)

        # Дерево
        wrap = tk.Frame(tab, bg=BG)
        wrap.pack(fill="both", expand=True)
        cols = ("title", "author", "genre", "status", "rating", "star")
        self.tree = ttk.Treeview(wrap, columns=cols, show="tree headings",
                                 selectmode="browse")
        self.tree.heading("#0", text="")
        self.tree.column("#0", width=76, stretch=False)
        for c, txt, w, anchor, stretch in [
            ("title", "Название", 260, "w", True),
            ("author", "Автор", 160, "w", False),
            ("genre", "Жанр", 110, "w", False),
            ("status", "Статус", 120, "center", False),
            ("rating", "Оценка", 120, "center", False),
            ("star", "", 36, "center", False),
        ]:
            self.tree.heading(c, text=txt, anchor=anchor)
            self.tree.column(c, width=w, anchor=anchor, stretch=stretch)
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)

        self.tree.bind("<Double-1>", self._toggle_star)
        self.tree.bind("<Button-3>", self._ctx_menu)

        footer = tk.Frame(tab, bg=BG)
        footer.pack(fill="x", pady=12)
        self.stats_lbl = tk.Label(footer, text="", bg=BG, fg=MUTED,
                                  font=(FONT, 9))
        self.stats_lbl.pack(side="left")
        ttk.Button(footer, text="✕ Удалить", style="Ghost.TButton",
                   command=self.delete_selected).pack(side="right")

    def _build_recs_tab(self):
        tab = self.recs_tab
        tk.Label(tab, text="Персональные рекомендации",
                 bg=BG, fg=TEXT, font=(FONT, 16, "bold")).pack(
            anchor="w", pady=(14, 4))
        self.rec_info = tk.Label(tab, text="", bg=BG, fg=MUTED,
                                 justify="left", font=(FONT, 10))
        self.rec_info.pack(anchor="w", pady=(0, 12))

        wrap = tk.Frame(tab, bg=BG)
        wrap.pack(fill="both", expand=True)
        cols = ("title", "author", "genre", "status")
        self.rec_tree = ttk.Treeview(wrap, columns=cols,
                                     show="tree headings", selectmode="browse")
        self.rec_tree.heading("#0", text="")
        self.rec_tree.column("#0", width=76, stretch=False)
        for c, txt, w, anchor, stretch in [
            ("title", "Название", 260, "w", True),
            ("author", "Автор", 160, "w", False),
            ("genre", "Жанр", 140, "w", False),
            ("status", "Статус", 140, "center", False),
        ]:
            self.rec_tree.heading(c, text=txt, anchor=anchor)
            self.rec_tree.column(c, width=w, anchor=anchor, stretch=stretch)
        self.rec_tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(wrap, orient="vertical",
                           command=self.rec_tree.yview)
        sb.pack(side="right", fill="y")
        self.rec_tree.configure(yscrollcommand=sb.set)
        self.rec_tree.bind("<Double-1>", lambda e: self.rec_mark_read())

        btns = tk.Frame(tab, bg=BG)
        btns.pack(fill="x", pady=12)
        ttk.Button(btns, text="▶ Начать читать", style="Ghost.TButton",
                   command=self.rec_start_reading).pack(side="left")
        ttk.Button(btns, text="✓ Прочитано", style="Accent.TButton",
                   command=self.rec_mark_read).pack(side="left", padx=8)

    # ---------- DATA ----------
    def on_data_changed(self):
        self.refresh()
        self.refresh_recommendations()

    def refresh(self):
        prev = self.tree.selection()
        prev_id = prev[0] if prev else None
        self.tree.delete(*self.tree.get_children())
        self._imgs.clear()

        rows = dbm.get_books(status=self.status_var.get(),
                             search=self.search_var.get().strip())
        stats = dbm.get_stats()

        for bid, title, author, genre, status, rating, cover, starred in rows:
            img = rounded(load_cover(cover) or placeholder(title), 6)
            photo = ImageTk.PhotoImage(img)
            self._imgs[bid] = photo
            status_lbl = {"planned": "В планах", "reading": "Читаю",
                          "read": "✓ Прочитано"}.get(status, status)
            rating_txt = ("★" * rating + "☆" * (5 - rating)) if rating else "—"
            star_txt = "★" if starred else ""
            self.tree.insert("", "end", iid=str(bid), image=photo,
                             values=(title, author, genre or "—",
                                     status_lbl, rating_txt, star_txt))

        if prev_id and self.tree.exists(prev_id):
            self.tree.selection_set(prev_id)
            self.tree.focus(prev_id)

        avg = stats["avg"]
        avg_s = f"{avg:.1f}" if avg else "—"
        self.stats_lbl.config(
            text=f"Всего: {stats['total']}    "
                 f"Прочитано: {stats['read']}    "
                 f"Средняя оценка: {avg_s}")

    def refresh_recommendations(self):
        if not hasattr(self, "rec_tree"):
            return
        self.rec_tree.delete(*self.rec_tree.get_children())
        self._rec_imgs.clear()

        recs, genres = logic.recommendations()

        if not genres:
            self.rec_info.config(
                text="Пока нет оценок. Оцените прочитанные книги (4-5★), "
                     "и здесь появятся рекомендации.")
        else:
            parts = [f"{g} — {c} кн., ср. {a:.1f}★" for g, c, a in genres]
            self.rec_info.config(
                text="На основе ваших высоких оценок вы любите:\n  • "
                     + "\n  • ".join(parts)
                     + "\n\nВот что из ваших планов подходит под эти жанры:")

        if not recs:
            if genres:
                self.rec_info.config(
                    text=self.rec_info.cget("text")
                    + "\n\n(в планах пока нет книг этих жанров — добавьте)")
            return

        for rid, title, author, genre, cover in recs:
            img = rounded(load_cover(cover) or placeholder(title), 6)
            ph = ImageTk.PhotoImage(img)
            self._rec_imgs[rid] = ph
            self.rec_tree.insert("", "end", iid=str(rid), image=ph,
                                 values=(title, author, genre or "—",
                                         "В планах"))

    # ---------- ACTIONS ----------
    def add_book(self):
        BookForm(self, on_save=self.on_data_changed)

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Редактировать",
                                "Сначала выберите книгу в списке.")
            return
        BookForm(self, book_id=int(sel[0]), on_save=self.on_data_changed)

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Удалить", "Сначала выберите книгу.")
            return
        if not messagebox.askyesno("Удалить", "Удалить выбранную книгу?"):
            return
        dbm.delete_book(int(sel[0]))
        self.on_data_changed()

    def _toggle_star(self, _e=None):
        sel = self.tree.selection()
        if not sel:
            return
        dbm.toggle_star(int(sel[0]))
        self.on_data_changed()

    def _ctx_menu(self, e):
        iid = self.tree.identify_row(e.y)
        if iid:
            self.tree.selection_set(iid)
        m = tk.Menu(self, tearoff=0)
        m.add_command(label="★ Переключить закладку", command=self._toggle_star)
        m.add_command(label="Редактировать", command=self.edit_selected)
        m.add_separator()
        m.add_command(label="Удалить", command=self.delete_selected)
        m.tk_popup(e.x_root, e.y_root)

    def rec_start_reading(self):
        sel = self.rec_tree.selection()
        if not sel:
            return
        dbm.set_status(int(sel[0]), "reading")
        self.on_data_changed()

    def rec_mark_read(self):
        sel = self.rec_tree.selection()
        if not sel:
            return
        dbm.set_status(int(sel[0]), "read")
        self.on_data_changed()

# ---------- BOOK FORM ----------
class BookForm(tk.Toplevel):
    def __init__(self, parent, book_id=None, on_save=None):
        super().__init__(parent)
        self.on_save, self.book_id, self.cover_src = on_save, book_id, ""
        self.configure(bg=BG)
        self.title("Редактировать книгу" if book_id else "Новая книга")
        self.geometry("480x820")
        self.minsize(460, 700)
        self.transient(parent)
        self.grab_set()
        self._build()
        if book_id:
            self._load()

    def _entry(self, parent, label):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=20, pady=(8, 0))
        tk.Label(row, text=label, bg=BG, fg=MUTED,
                 font=(FONT, 9)).pack(anchor="w")
        e = tk.Entry(row, bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                     bd=0, font=(FONT, 11))
        e.pack(fill="x", ipady=6, pady=(4, 0))
        return e

    def _build(self):
        # Кнопки — первыми, прижаты к низу, всегда видны
        btns = tk.Frame(self, bg=BG)
        btns.pack(side="bottom", fill="x", padx=20, pady=14)
        ttk.Button(btns, text="Отмена", style="Ghost.TButton",
                   command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btns, text="Сохранить", style="Accent.TButton",
                   command=self._save).pack(side="right")

        # Тело — обычный Frame без скролла
        body = tk.Frame(self, bg=BG)
        body.pack(side="top", fill="both", expand=True)

        tk.Label(body, text="Книга", bg=BG, fg=TEXT,
                 font=(FONT, 16, "bold")).pack(padx=20, pady=(14, 0),
                                               anchor="w")
        self.title_e = self._entry(body, "Название")
        self.author_e = self._entry(body, "Автор")
        self.genre_e = self._entry(body, "Жанр")

        # статус
        r = tk.Frame(body, bg=BG)
        r.pack(fill="x", padx=20, pady=(8, 0))
        tk.Label(r, text="Статус", bg=BG, fg=MUTED,
                 font=(FONT, 9)).pack(anchor="w")
        self.status_v = tk.StringVar(value="planned")
        st = tk.Frame(r, bg=BG)
        st.pack(anchor="w", pady=4)
        for lbl, val in [("В планах", "planned"), ("Читаю", "reading"),
                         ("Прочитано", "read")]:
            tk.Radiobutton(st, text=lbl, value=val,
                           variable=self.status_v, bg=BG, fg=TEXT,
                           selectcolor=SURFACE, activebackground=BG,
                           indicatoron=False, padx=10, pady=6, bd=0,
                           font=(FONT, 9)).pack(side="left", padx=4)

        # оценка
        r = tk.Frame(body, bg=BG)
        r.pack(fill="x", padx=20, pady=(8, 0))
        tk.Label(r, text="Оценка", bg=BG, fg=MUTED,
                 font=(FONT, 9)).pack(anchor="w")
        self.rating_v = tk.IntVar(value=0)
        self.star_lbls = []
        sf = tk.Frame(r, bg=BG)
        sf.pack(anchor="w", pady=2)
        for i in range(1, 6):
            lb = tk.Label(sf, text="☆", bg=BG, fg=STAR_OFF,
                          font=(FONT, 20), cursor="hand2")
            lb.pack(side="left", padx=2)
            lb.bind("<Button-1>", lambda e, n=i: self._set_rating(n))
            self.star_lbls.append(lb)

        # обложка
        r = tk.Frame(body, bg=BG)
        r.pack(fill="x", padx=20, pady=(8, 0))
        tk.Label(r, text="Обложка", bg=BG, fg=MUTED,
                 font=(FONT, 9)).pack(anchor="w")
        cf = tk.Frame(r, bg=BG)
        cf.pack(fill="x", pady=4)
        self.cover_lbl = tk.Label(cf, bg=SURFACE2, width=12, height=5,
                                  text="нет", fg=MUTED)
        self.cover_lbl.pack(side="left")
        ttk.Button(cf, text="Выбрать...", style="Ghost.TButton",
                   command=self._pick_cover).pack(side="left",
                                                 padx=8, anchor="n")

        # рецензия
        r = tk.Frame(body, bg=BG)
        r.pack(fill="x", padx=20, pady=(8, 8))
        tk.Label(r, text="Рецензия", bg=BG, fg=MUTED,
                 font=(FONT, 9)).pack(anchor="w")
        self.review_t = tk.Text(r, bg=SURFACE, fg=TEXT,
                                insertbackground=TEXT, bd=0, height=5,
                                wrap="word", font=(FONT, 10))
        self.review_t.pack(fill="x", pady=(4, 0))

    def _set_rating(self, n):
        self.rating_v.set(n)
        for i, lb in enumerate(self.star_lbls, 1):
            lb.config(text="★" if i <= n else "☆",
                      fg=STAR if i <= n else STAR_OFF)

    def _pick_cover(self):
        p = filedialog.askopenfilename(
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.webp *.bmp")])
        if not p:
            return
        dst = os.path.join(dbm.COVERS,
                           f"{os.urandom(4).hex()}{os.path.splitext(p)[1]}")
        shutil.copy(p, dst)
        self.cover_src = dst
        img = load_cover(dst, (96, 132))
        if img:
            ph = ImageTk.PhotoImage(img)
            self.cover_lbl.config(image=ph, width=96, height=132, text="")
            self.cover_lbl.image = ph

    def _load(self):
        row = dbm.get_book(self.book_id)
        if not row:
            return
        title, author, genre, status, rating, review, cover = row
        self.title_e.insert(0, title)
        self.author_e.insert(0, author)
        self.genre_e.insert(0, genre or "")
        self.status_v.set(status)
        self._set_rating(rating or 0)
        self.review_t.insert("1.0", review or "")
        if cover:
            self.cover_src = cover
            img = load_cover(cover, (96, 132))
            if img:
                ph = ImageTk.PhotoImage(img)
                self.cover_lbl.config(image=ph, width=96, height=132, text="")
                self.cover_lbl.image = ph

    def _save(self):
        title = self.title_e.get().strip()
        author = self.author_e.get().strip()
        if not title or not author:
            messagebox.showwarning("Проверка",
                                   "Название и автор обязательны")
            return
        data = (title, author, self.genre_e.get().strip(),
                self.status_v.get(), self.rating_v.get(),
                self.review_t.get("1.0", "end").strip(), self.cover_src)
        if self.book_id:
            dbm.update_book(self.book_id, data)
        else:
            dbm.add_book(data)
        if self.on_save:
            self.on_save()
        self.destroy()

# ---------- MAIN ----------
if __name__ == "__main__":
    dbm.init_db()
    App().mainloop()