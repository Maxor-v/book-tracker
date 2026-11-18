import configparser, os

FILE = "settings.ini"

DEFAULTS = {"geometry": "960x760", "status": "all", "search": ""}

def load():
    c = configparser.ConfigParser()
    if os.path.exists(FILE):
        try:
            c.read(FILE, encoding="utf-8")
        except Exception:
            return dict(DEFAULTS)
    return {
        "geometry": c.get("window", "geometry", fallback=DEFAULTS["geometry"]),
        "status":   c.get("filters", "status",  fallback=DEFAULTS["status"]),
        "search":   c.get("filters", "search",  fallback=DEFAULTS["search"]),
    }

def save(geometry=None, status=None, search=None):
    c = configparser.ConfigParser()
    if os.path.exists(FILE):
        try:
            c.read(FILE, encoding="utf-8")
        except Exception:
            pass
    if "window" not in c: c["window"] = {}
    if "filters" not in c: c["filters"] = {}
    if geometry:  c["window"]["geometry"] = geometry
    if status is not None: c["filters"]["status"] = status
    if search is not None: c["filters"]["search"] = search
    with open(FILE, "w", encoding="utf-8") as f:
        c.write(f)