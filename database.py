import logging
import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

from config import PRACTICE_AREAS, MINING_WATCHLIST

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")


@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                source TEXT,
                published_at TEXT,
                practice_area TEXT,
                relevance_score REAL DEFAULT 0,
                summary TEXT,
                is_read INTEGER DEFAULT 0,
                is_dismissed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_url ON articles(url)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_practice_area ON articles(practice_area)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_relevance ON articles(relevance_score DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_dismissed ON articles(is_dismissed)")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS keywords (
                id SERIAL PRIMARY KEY,
                keyword TEXT NOT NULL,
                practice_area TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(keyword, practice_area)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id SERIAL PRIMARY KEY,
                label TEXT NOT NULL,
                pattern TEXT NOT NULL,
                group_name TEXT NOT NULL DEFAULT 'company',
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(pattern)
            )
        """)

        # Seed watchlist from config if empty
        cur.execute("SELECT COUNT(*) FROM watchlist")
        count = cur.fetchone()[0]
        if count == 0:
            for entry in MINING_WATCHLIST:
                pattern = entry["pattern"]
                if isinstance(pattern, tuple):
                    pattern = " + ".join(pattern)
                try:
                    cur.execute(
                        "INSERT INTO watchlist (label, pattern, group_name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                        (entry["label"], pattern, entry["group"]),
                    )
                except Exception:
                    pass


def insert_article(title, url, source, published_at, practice_area, relevance_score, summary):
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO articles (title, url, source, published_at, practice_area, relevance_score, summary)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (url) DO NOTHING""",
                (title, url, source, published_at, practice_area, relevance_score, summary),
            )
            return cur.rowcount > 0
    except Exception as e:
        logger.error("Failed to insert article %s: %s", url, e)
        return False


def url_exists(url):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM articles WHERE url = %s", (url,))
        return cur.fetchone() is not None


def get_articles(practice_area=None, min_score=0, search=None, include_dismissed=False, sort="score"):
    query = "SELECT * FROM articles WHERE created_at >= NOW() - INTERVAL '30 days'"
    params = []

    if not include_dismissed:
        query += " AND is_dismissed = 0"

    if practice_area and practice_area != "All":
        query += " AND practice_area = %s"
        params.append(practice_area)

    if min_score > 0:
        query += " AND relevance_score >= %s"
        params.append(min_score)

    if search:
        query += " AND (title ILIKE %s OR summary ILIKE %s)"
        params.extend([f"%{search}%", f"%{search}%"])

    if sort == "recent":
        query += " ORDER BY published_at DESC, created_at DESC"
    else:
        query += " ORDER BY relevance_score DESC, created_at DESC"

    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def mark_read(article_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE articles SET is_read = 1 WHERE id = %s", (article_id,))


def mark_dismissed(article_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE articles SET is_dismissed = 1 WHERE id = %s", (article_id,))


def get_last_fetch_time():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT created_at FROM articles ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        return str(row[0]) if row else None


def get_stats():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM articles WHERE is_dismissed = 0")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM articles WHERE is_read = 0 AND is_dismissed = 0")
        unread = cur.fetchone()[0]
        cur.execute("""
            SELECT practice_area, COUNT(*) as count
            FROM articles WHERE is_dismissed = 0
            GROUP BY practice_area
        """)
        by_area = {row[0]: row[1] for row in cur.fetchall()}
        return {"total": total, "unread": unread, "by_area": by_area}


# ── Keyword management ────────────────────────────────────────────────────────

def get_keywords():
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM keywords ORDER BY practice_area, keyword")
        result = {area: [] for area in PRACTICE_AREAS.keys()}
        for row in cur.fetchall():
            area = row["practice_area"]
            if area not in result:
                result[area] = []
            result[area].append({"id": row["id"], "keyword": row["keyword"]})
        return result


def add_keyword(keyword, practice_area):
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO keywords (keyword, practice_area) VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING id",
                (keyword.strip(), practice_area),
            )
            row = cur.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error("Failed to add keyword: %s", e)
        return None


def delete_keyword(keyword_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM keywords WHERE id = %s", (keyword_id,))


# ── Watchlist management ──────────────────────────────────────────────────────

def get_watchlist_db():
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM watchlist ORDER BY group_name, label")
        return [dict(row) for row in cur.fetchall()]


def add_watchlist_entry(label, pattern, group_name):
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO watchlist (label, pattern, group_name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING RETURNING id",
                (label.strip(), pattern.strip().lower(), group_name),
            )
            row = cur.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error("Failed to add watchlist entry: %s", e)
        return None


def delete_watchlist_entry(entry_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM watchlist WHERE id = %s", (entry_id,))


def get_all_keywords_for_scraper():
    result = {area: list(kws) for area, kws in PRACTICE_AREAS.items()}
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT keyword, practice_area FROM keywords")
        for row in cur.fetchall():
            area, kw = row[1], row[0]
            if area in result and kw not in result[area]:
                result[area].append(kw)
    return result


def get_watchlist_for_scraper():
    entries = list(MINING_WATCHLIST)
    existing_patterns = {
        e["pattern"] if isinstance(e["pattern"], str) else " + ".join(e["pattern"])
        for e in MINING_WATCHLIST
    }
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT label, pattern, group_name FROM watchlist")
        for row in cur.fetchall():
            label, pattern, group_name = row
            if pattern not in existing_patterns:
                entries.append({"label": label, "pattern": pattern, "group": group_name})
    return entries
