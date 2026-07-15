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

        cur.execute("""
            CREATE TABLE IF NOT EXISTS pipeline (
                id SERIAL PRIMARY KEY,
                company_name TEXT NOT NULL,
                ticker TEXT,
                exchange TEXT,
                commodity TEXT,
                stage TEXT NOT NULL DEFAULT 'Identified',
                deal_type TEXT,
                estimated_deal_size TEXT,
                key_contacts TEXT,
                notes TEXT,
                last_contact_date TEXT,
                source_article_url TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                ticker TEXT,
                exchange TEXT,
                market_cap TEXT,
                province TEXT,
                executives TEXT,
                board_members TEXT,
                legal_counsel TEXT,
                projects TEXT,
                commodity TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(name)")

        # Seed companies from spreadsheet if table is empty
        cur.execute("SELECT COUNT(*) FROM companies")
        if cur.fetchone()[0] == 0:
            _seed_companies(cur)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                keywords TEXT DEFAULT '',
                practice_area TEXT DEFAULT 'Any',
                min_score REAL DEFAULT 5,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS alert_matches (
                id SERIAL PRIMARY KEY,
                alert_id INTEGER REFERENCES alerts(id) ON DELETE CASCADE,
                article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
                matched_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(alert_id, article_id)
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


# ── Pipeline management ───────────────────────────────────────────────────────

PIPELINE_STAGES = ["Identified", "Researched", "Contacted", "Active Mandate"]


def get_pipeline():
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM pipeline ORDER BY updated_at DESC")
        return [dict(row) for row in cur.fetchall()]


def add_pipeline_company(company_name, ticker="", exchange="", commodity="",
                          stage="Identified", deal_type="", estimated_deal_size="",
                          key_contacts="", notes="", last_contact_date="",
                          source_article_url=""):
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO pipeline
                    (company_name, ticker, exchange, commodity, stage, deal_type,
                     estimated_deal_size, key_contacts, notes, last_contact_date, source_article_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (company_name, ticker, exchange, commodity, stage, deal_type,
                  estimated_deal_size, key_contacts, notes, last_contact_date, source_article_url))
            return cur.fetchone()[0]
    except Exception as e:
        logger.error("Failed to add pipeline company: %s", e)
        return None


def update_pipeline_company(company_id, **fields):
    allowed = {"company_name", "ticker", "exchange", "commodity", "stage", "deal_type",
               "estimated_deal_size", "key_contacts", "notes", "last_contact_date"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    updates["updated_at"] = "NOW()"
    set_clause = ", ".join(
        f"{k} = NOW()" if v == "NOW()" else f"{k} = %s"
        for k, v in updates.items()
    )
    values = [v for v in updates.values() if v != "NOW()"]
    values.append(company_id)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE pipeline SET {set_clause} WHERE id = %s", values)


def delete_pipeline_company(company_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM pipeline WHERE id = %s", (company_id,))


# ── Company profiles ──────────────────────────────────────────────────────────

_COMPANY_SEED = [
    ("GoldQuest Mining Corp.", "GQC", "TSXV", "~$241.75M USD", "Dominican Republic / BC",
     "Luis Santana - CEO & Director",
     "Frank Balint - Chairman; Bill Fisher - Director; Julio Espaillat - Director; Patrick Michaels - Director; Charles Reid - Director; Florian Siegfried - Director",
     "Blake Cassels & Graydon LLP", "Romero Project, Dominican Republic", "Gold & Copper"),
    ("Chesapeake Gold Corp.", "CKG", "TSXV", "~$161.70M USD", "British Columbia",
     "Jean-Paul Tsotsos - CEO; Rajesh Vyas - CFO; Justin Black - Chief Metallurgical Officer; Gary Parkison - VP Development; Alberto Galicia - VP Exploration",
     "P. Randy Reifel - Executive Chairman; Randy Buffington - Director; Doug Flegg - Director; Lian Li - Director; John Preston - Director; Jeff Stieber - Director; Paul West-Sells - Director",
     "", "Metates Project, Durango, Mexico; Lucy Project, Sinaloa, Mexico", "Gold & Silver"),
    ("1911 Gold Corp.", "AUMB", "TSXV", "~$135M–$145M USD", "British Columbia",
     "Shaun Heinrichs - President & CEO; Max Satel - CFO",
     "", "", "True North Gold Project, Rice Lake Greenstone Belt, Manitoba", "Gold"),
    ("Azimut Exploration Inc.", "AZM", "TSXV", "~$47.06M USD", "Quebec",
     "Jean-Marc Lulin - President & CEO; Moniroth Lim - CFO & Corporate Secretary; Rock Lefrancois - VP Exploration; Jonathan Rosset - VP Corporate Development",
     "Glenn Mullan - Chair; Christiane Bergevin - Director; Michel Brunet - Director; Vanessa Laplante - Director; Jean-Charles Potvin - Director; Jacques Simoneau - Director",
     "Marc Pothier (internal)", "Elmer Property (Patwon Gold Deposit); Wabamisk Property; James Bay Region, Quebec", "Gold"),
    ("Goldgroup Mining Inc.", "GGA", "TSXV", "~$100–200M USD", "British Columbia",
     "Ralph Shearing - CEO; Anthony Balic - CFO & Director",
     "Anthony Balic - Director; Corry Silbernagel - Director; Blair Jordan - Director; Roberto Guzman - Director",
     "Cozen O'Connor LLP (Company); McMillan LLP (Special committee)", "Mexico-focused gold & silver assets (Business combination with Gold Resource Corp. pending)", "Gold & Silver"),
    ("K2 Gold Corp.", "KTO", "TSXV", "~$117.69M USD", "British Columbia",
     "Anthony Margarit - President & CEO",
     "", "", "Mojave Project, California; Si2 Project, Nevada", "Gold"),
    ("Onyx Gold Corp.", "ONYX", "TSXV", "~$76.3M–$80.3M USD", "British Columbia",
     "Brock Colterjohn - President & CEO; Vanessa Pickering - VP Investor Relations",
     "Brock Colterjohn - Director; Darwin Green - Director; Michael Cinnamond - Director; Gwen Preston - Director; Kiran Patankar - Director",
     "", "Timmins, Ontario; Yukon Territory", "Gold"),
    ("Prospector Metals Corp.", "PPP", "TSXV", "~$150M–$155M USD", "British Columbia",
     "Dr. Rob Carpenter - President, CEO & Co-Chairman; Jordan Laker - CFO; Danica Topolewski - Corporate Secretary",
     "Dr. Rob Carpenter - Co-Chairman; Craig Roberts - Co-Chairman; Andrew Rockandel - Executive Director",
     "", "Yukon exploration portfolio, Tintina Gold Belt", "Gold"),
    ("NorthIsle Copper & Gold Inc.", "NCX", "TSXV", "~$655.21M USD", "British Columbia",
     "Sam Lee - President, CEO & Director; Nicholas Van Dyk - CFO; Kevin O'Kane - COO & Director",
     "Alex Davidson - Chairman; Jill Donaldson - Director; Kevin O'Kane - Director; Sam Lee - Director; Hume Kyle - Director",
     "", "North Island Project, near Port Hardy, British Columbia", "Copper & Gold"),
    ("Guanajuato Silver Company Ltd.", "GSVR", "TSXV", "~$353M USD", "",
     "James Anderson - Chairman & CEO",
     "David Paxton - Director", "", "Bolanitos Mine, Guanajuato, Mexico", "Silver & Gold"),
    ("Cerrado Gold Inc.", "CERT", "TSXV", "~$170–257M USD", "Ontario",
     "Mark Brennan - CEO & Chairman; Mike McAllister - VP Investor Relations",
     "Mark Brennan - CEO & Chairman; Kurt Menchen - Director; Robert Campbell - Director; Robert Sellars - Director; Christopher Jones - Director; Maria Virginia Anzola - Director; Rui Santos - Director",
     "", "Minera Don Nicolas Mine, Santa Cruz Province, Argentina", "Gold"),
    ("Silver X Mining Corp.", "AGX", "TSXV", "~$100–200M USD", "British Columbia",
     "Jose Garcia Jimenez - CEO; Susan Xu - Investor Relations",
     "Mark NJ Ashcroft - Director; Joseph Gallucci - Director; A. David Heyl - Consultant",
     "", "Multi-asset precious metals platform, Peru", "Silver & Gold"),
    ("Silver47 Exploration Corp.", "AGA", "TSXV", "~$89–96M USD", "British Columbia",
     "Galen McNamara - CEO & Director; Giordy Belfiore - Investor Relations",
     "Gary R. Thompson - Director; Galen McNamara - Director; Thomas O'Neill - Director; Ryan Goodman - Director",
     "Fasken Martineau DuMoulin LLP", "Project locations TBC", "Silver"),
    ("Surge Battery Metals Inc.", "NILI", "TSXV", "~$121M USD", "British Columbia",
     "Greg Reimer - President & CEO; Brian Paes-Braga - Strategic Funding Co-Lead; Michael Hess - Strategic Funding Co-Lead",
     "Graham Harris - Chair; Ted O'Connor - Director",
     "", "Nevada North Lithium Project, Northern Nevada", "Lithium"),
    ("Amarc Resources Ltd.", "AHR", "TSXV", "~$205M USD", "British Columbia",
     "Dr. Diane Nicolson - President, CEO & Director; Carol Li - CFO; Rick Roe - Senior Operations Manager",
     "Dr. Diane Nicolson - Director/CEO",
     "", "JOY, DUKE & IKE Porphyry Projects, British Columbia", "Copper & Gold"),
    ("OMAI Gold Mines Corp.", "OMG", "TSXV", "~$100–300M USD", "Ontario",
     "Elaine Ellingham - President & CEO",
     "Don Dudek - Chairman; Drew Anwyll - Independent Director",
     "", "Omai Gold Project (Wenot & Gilt Creek deposits), Guyana — 8.0 Moz resource (April 2026)", "Gold"),
    ("San Lorenzo Gold Corp.", "SLG", "TSXV", "~$330M–$360M USD", "Alberta",
     "Al Kroontje - CEO & Director; Terence Walker - VP Exploration",
     "Al Kroontje - Director; Kevin Baker - Director; Terence Walker - Director; Kelly Kimbley - Director",
     "", "Salvadora Property & Mega Porphyry Belt, Chile", "Copper-Gold & Gold-Silver"),
    ("Precipitate Gold Corp.", "PRG", "TSXV", "~$35M–$50M USD", "British Columbia",
     "Jeff Wilson - President & CEO",
     "Jose Acebal - Director",
     "", "Juan de Herrera, Pueblo Grande & Pont Projects, Dominican Republic", "Gold & Base Metals"),
    ("Tectonic Metals Inc.", "TECT", "TSXV", "~$200M–$280M USD", "British Columbia",
     "Tony Reda - Founder, President, CEO & Director; Maggie Layman - VP Exploration; Peter Kleespies - Chief Geological Officer; Oliver Foeste - CFO",
     "Eira Thomas - Founder & Chair; Dr. John P. Armstrong - Director; Michael Roper - Director; Allison Rippin Armstrong - Director; Joseph J. Perkins - Director",
     "Blake Cassels & Graydon LLP", "Flat Gold Project, Aniak, Alaska", "Gold"),
    ("Silver Mountain Resources Inc.", "AGMR", "TSX", "~$155M–$160M USD", "Ontario",
     "Alvaro Espinoza - CEO; Jean Pierre Fort - President & Director",
     "W. John DeCooman Jr. - Director; Alfredo Bazo - Director",
     "", "Reliquias Mine, Huancavelica, Peru (restarting Q3 2026)", "Silver"),
]


def _seed_companies(cur):
    for row in _COMPANY_SEED:
        name, ticker, exchange, market_cap, province, executives, board_members, legal_counsel, projects, commodity = row
        cur.execute("""
            INSERT INTO companies (name, ticker, exchange, market_cap, province, executives, board_members, legal_counsel, projects, commodity)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING
        """, (name, ticker, exchange, market_cap, province, executives, board_members, legal_counsel, projects, commodity))


def get_companies(search=None, commodity=None):
    query = "SELECT * FROM companies WHERE 1=1"
    params = []
    if search:
        query += " AND (name ILIKE %s OR ticker ILIKE %s OR executives ILIKE %s OR legal_counsel ILIKE %s)"
        params.extend([f"%{search}%"] * 4)
    if commodity:
        query += " AND commodity ILIKE %s"
        params.append(f"%{commodity}%")
    query += " ORDER BY name"
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def get_company(company_id):
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM companies WHERE id = %s", (company_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def add_company(name, ticker="", exchange="", market_cap="", province="",
                executives="", board_members="", legal_counsel="", projects="",
                commodity="", notes=""):
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO companies (name, ticker, exchange, market_cap, province, executives, board_members, legal_counsel, projects, commodity, notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """, (name, ticker, exchange, market_cap, province, executives, board_members, legal_counsel, projects, commodity, notes))
            return cur.fetchone()[0]
    except Exception as e:
        logger.error("Failed to add company: %s", e)
        return None


def update_company(company_id, **fields):
    allowed = {"name","ticker","exchange","market_cap","province","executives",
               "board_members","legal_counsel","projects","commodity","notes"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    updates["updated_at"] = "NOW()"
    set_clause = ", ".join(f"{k} = NOW()" if v == "NOW()" else f"{k} = %s" for k, v in updates.items())
    values = [v for v in updates.values() if v != "NOW()"]
    values.append(company_id)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE companies SET {set_clause} WHERE id = %s", values)


def delete_company(company_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM companies WHERE id = %s", (company_id,))


def get_related_articles(company_name, ticker, limit=5):
    """Find recent articles mentioning this company."""
    search_terms = [company_name]
    if ticker:
        search_terms.append(ticker)
    conditions = " OR ".join(["(title ILIKE %s OR summary ILIKE %s)"] * len(search_terms))
    params = []
    for t in search_terms:
        params.extend([f"%{t}%", f"%{t}%"])
    params.append(limit)
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(f"""
            SELECT id, title, url, source, published_at, relevance_score, practice_area
            FROM articles WHERE ({conditions}) AND is_dismissed = 0
            ORDER BY created_at DESC LIMIT %s
        """, params)
        return [dict(row) for row in cur.fetchall()]


# ── Alert management ──────────────────────────────────────────────────────────

def get_alerts():
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM alerts ORDER BY created_at DESC")
        return [dict(row) for row in cur.fetchall()]


def add_alert(name, keywords="", practice_area="Any", min_score=5.0):
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO alerts (name, keywords, practice_area, min_score)
                   VALUES (%s, %s, %s, %s) RETURNING id""",
                (name.strip(), keywords.strip().lower(), practice_area, float(min_score)),
            )
            return cur.fetchone()[0]
    except Exception as e:
        logger.error("Failed to add alert: %s", e)
        return None


def update_alert(alert_id, **fields):
    allowed = {"name", "keywords", "practice_area", "min_score", "active"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [alert_id]
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE alerts SET {set_clause} WHERE id = %s", values)


def delete_alert(alert_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM alerts WHERE id = %s", (alert_id,))


def get_article_alert_names():
    """Return {article_id: [alert_name, ...]} for all alert matches."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT am.article_id, a.name
            FROM alert_matches am
            JOIN alerts a ON a.id = am.alert_id
            ORDER BY am.matched_at DESC
        """)
        result = {}
        for article_id, alert_name in cur.fetchall():
            result.setdefault(article_id, []).append(alert_name)
        return result


def check_new_articles_against_alerts():
    """
    Check articles created in the last 2 hours against all active alerts.
    Returns list of (alert_dict, article_dict) new matches.
    """
    new_matches = []
    try:
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Get active alerts
            cur.execute("SELECT * FROM alerts WHERE active = TRUE")
            alerts = [dict(r) for r in cur.fetchall()]
            if not alerts:
                return []

            # Get articles from the last 2 hours not already matched
            cur.execute("""
                SELECT a.* FROM articles a
                WHERE a.created_at >= NOW() - INTERVAL '2 hours'
                  AND a.is_dismissed = 0
            """)
            recent_articles = [dict(r) for r in cur.fetchall()]
            if not recent_articles:
                return []

            for alert in alerts:
                kws = [k.strip() for k in alert["keywords"].split(",") if k.strip()]
                pa = alert["practice_area"]
                min_score = float(alert["min_score"])

                for article in recent_articles:
                    # Score filter
                    if article["relevance_score"] < min_score:
                        continue
                    # Practice area filter
                    if pa and pa != "Any" and article.get("practice_area") != pa:
                        continue
                    # Keyword filter — at least one keyword must match
                    if kws:
                        text = f"{article['title']} {article.get('summary') or ''}".lower()
                        if not any(kw in text for kw in kws):
                            continue

                    # Try to insert match (skip if already exists)
                    try:
                        cur2 = conn.cursor()
                        cur2.execute(
                            """INSERT INTO alert_matches (alert_id, article_id)
                               VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING id""",
                            (alert["id"], article["id"]),
                        )
                        if cur2.fetchone():  # only new matches return a row
                            new_matches.append((alert, article))
                    except Exception:
                        pass

            conn.commit()
    except Exception as e:
        logger.error("Alert check failed: %s", e)

    return new_matches
