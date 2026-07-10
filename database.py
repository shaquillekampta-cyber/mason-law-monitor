import sqlite3
import logging
from contextlib import contextmanager
from config import DATABASE_PATH, PRACTICE_AREAS, MINING_WATCHLIST

logger = logging.getLogger(__name__)


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                source TEXT,
                published_at TEXT,
                practice_area TEXT,
                relevance_score REAL DEFAULT 0,
                summary TEXT,
                is_read INTEGER DEFAULT 0,
                is_dismissed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_url ON articles(url)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_practice_area ON articles(practice_area)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relevance ON articles(relevance_score DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dismissed ON articles(is_dismissed)")

        # User-managed keywords table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                practice_area TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(keyword, practice_area)
            )
        """)

        # User-managed watchlist table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                pattern TEXT NOT NULL,
                group_name TEXT NOT NULL DEFAULT 'company',
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(pattern)
            )
        """)

        # Seed watchlist from config if table is empty
        count = conn.execute("SELECT COUNT(*) as c FROM watchlist").fetchone()["c"]
        if count == 0:
            for entry in MINING_WATCHLIST:
                pattern = entry["pattern"]
                if isinstance(pattern, tuple):
                    pattern = " + ".join(pattern)
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO watchlist (label, pattern, group_name) VALUES (?, ?, ?)",
                        (entry["label"], pattern, entry["group"]),
                    )
                except Exception:
                    pass


@contextmanager
def get_conn():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def insert_article(title, url, source, published_at, practice_area, relevance_score, summary):
    try:
        with get_conn() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO articles
                   (title, url, source, published_at, practice_area, relevance_score, summary)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (title, url, source, published_at, practice_area, relevance_score, summary),
            )
            return True
    except Exception as e:
        logger.error("Failed to insert article %s: %s", url, e)
        return False


def url_exists(url):
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM articles WHERE url = ?", (url,)).fetchone()
        return row is not None


def get_articles(practice_area=None, min_score=0, search=None, include_dismissed=False, sort="score"):
    query = "SELECT * FROM articles WHERE published_at >= datetime('now', '-30 days')"
    params = []

    if not include_dismissed:
        query += " AND is_dismissed = 0"

    if practice_area and practice_area != "All":
        query += " AND practice_area = ?"
        params.append(practice_area)

    if min_score > 0:
        query += " AND relevance_score >= ?"
        params.append(min_score)

    if search:
        query += " AND (title LIKE ? OR summary LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if sort == "recent":
        query += " ORDER BY published_at DESC, created_at DESC"
    else:
        query += " ORDER BY relevance_score DESC, created_at DESC"

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def mark_read(article_id):
    with get_conn() as conn:
        conn.execute("UPDATE articles SET is_read = 1 WHERE id = ?", (article_id,))


def mark_dismissed(article_id):
    with get_conn() as conn:
        conn.execute("UPDATE articles SET is_dismissed = 1 WHERE id = ?", (article_id,))


def get_last_fetch_time():
    with get_conn() as conn:
        row = conn.execute(
            "SELECT created_at FROM articles ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return row["created_at"] if row else None


def get_stats():
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM articles WHERE is_dismissed = 0").fetchone()["c"]
        unread = conn.execute(
            "SELECT COUNT(*) as c FROM articles WHERE is_read = 0 AND is_dismissed = 0"
        ).fetchone()["c"]
        by_area = conn.execute(
            """SELECT practice_area, COUNT(*) as count
               FROM articles WHERE is_dismissed = 0
               GROUP BY practice_area"""
        ).fetchall()
        return {
            "total": total,
            "unread": unread,
            "by_area": {row["practice_area"]: row["count"] for row in by_area},
        }


# ── Keyword management ────────────────────────────────────────────────────────

def get_keywords():
    """Return all user-managed keywords grouped by practice area."""
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM keywords ORDER BY practice_area, keyword").fetchall()
        result = {area: [] for area in PRACTICE_AREAS.keys()}
        for row in rows:
            area = row["practice_area"]
            if area not in result:
                result[area] = []
            result[area].append({"id": row["id"], "keyword": row["keyword"]})
        return result


def add_keyword(keyword, practice_area):
    """Add a new user keyword. Returns the new row id or None if duplicate."""
    try:
        with get_conn() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO keywords (keyword, practice_area) VALUES (?, ?)",
                (keyword.strip(), practice_area),
            )
            return cursor.lastrowid if cursor.rowcount else None
    except Exception as e:
        logger.error("Failed to add keyword: %s", e)
        return None


def delete_keyword(keyword_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM keywords WHERE id = ?", (keyword_id,))


# ── Watchlist management ──────────────────────────────────────────────────────

def get_watchlist_db():
    """Return all watchlist entries from the database."""
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM watchlist ORDER BY group_name, label").fetchall()
        return [dict(row) for row in rows]


def add_watchlist_entry(label, pattern, group_name):
    """Add a new watchlist entry. Returns new id or None if duplicate."""
    try:
        with get_conn() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO watchlist (label, pattern, group_name) VALUES (?, ?, ?)",
                (label.strip(), pattern.strip().lower(), group_name),
            )
            return cursor.lastrowid if cursor.rowcount else None
    except Exception as e:
        logger.error("Failed to add watchlist entry: %s", e)
        return None


def delete_watchlist_entry(entry_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM watchlist WHERE id = ?", (entry_id,))


def get_all_keywords_for_scraper():
    """Return user-added keywords merged with config keywords, by practice area."""
    result = {area: list(kws) for area, kws in PRACTICE_AREAS.items()}
    with get_conn() as conn:
        rows = conn.execute("SELECT keyword, practice_area FROM keywords").fetchall()
        for row in rows:
            area = row["practice_area"]
            kw = row["keyword"]
            if area in result and kw not in result[area]:
                result[area].append(kw)
    return result


def get_watchlist_for_scraper():
    """Return combined config + DB watchlist entries in the same format as config.MINING_WATCHLIST."""
    from config import MINING_WATCHLIST
    entries = list(MINING_WATCHLIST)
    with get_conn() as conn:
        rows = conn.execute("SELECT label, pattern, group_name FROM watchlist").fetchall()
        existing_patterns = {e["pattern"] if isinstance(e["pattern"], str) else " + ".join(e["pattern"]) for e in MINING_WATCHLIST}
        for row in rows:
            if row["pattern"] not in existing_patterns:
                entries.append({"label": row["label"], "pattern": row["pattern"], "group": row["group_name"]})
    return entries
