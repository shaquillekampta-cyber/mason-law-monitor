import logging
import threading
from flask import Flask, jsonify, render_template, request
from apscheduler.schedulers.background import BackgroundScheduler

from config import FETCH_INTERVAL_HOURS, PRACTICE_AREAS, MINING_WATCHLIST
from database import (
    init_db, get_articles, mark_read, mark_dismissed,
    get_last_fetch_time, get_stats,
    get_keywords, add_keyword, delete_keyword,
    get_watchlist_db, add_watchlist_entry, delete_watchlist_entry,
    get_watchlist_for_scraper,
    get_pipeline, add_pipeline_company, update_pipeline_company, delete_pipeline_company,
    PIPELINE_STAGES,
)
from scraper import run_scraper
from digest import send_digest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

_scrape_lock = threading.Lock()
_scraping = False


def find_watchlist_triggers(article):
    text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    triggered = []
    watchlist = get_watchlist_for_scraper()
    for kw in watchlist:
        pattern = kw["pattern"]
        if isinstance(pattern, tuple):
            if all(part.lower() in text for part in pattern):
                triggered.append({"label": kw["label"], "group": kw["group"]})
        else:
            if pattern.lower() in text:
                triggered.append({"label": kw["label"], "group": kw["group"]})
    return triggered


def find_matched_keywords(article):
    from database import get_all_keywords_for_scraper
    text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    keywords = get_all_keywords_for_scraper().get(article.get('practice_area', ''), [])
    matched = []
    for kw in keywords:
        if isinstance(kw, tuple):
            if all(part.lower() in text for part in kw):
                matched.append(" + ".join(kw))
        else:
            if kw.lower() in text:
                matched.append(kw)
    return matched


def scheduled_scrape():
    global _scraping
    if _scraping:
        logger.info("Scrape already in progress, skipping")
        return
    _scraping = True
    try:
        run_scraper()
    finally:
        _scraping = False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/articles")
def api_articles():
    practice_area = request.args.get("practice_area", "All")
    min_score = float(request.args.get("min_score", 0))
    search = request.args.get("search", "").strip() or None
    include_dismissed = request.args.get("include_dismissed", "false").lower() == "true"
    sort = request.args.get("sort", "score")  # "score" or "recent"

    articles = get_articles(
        practice_area=practice_area,
        min_score=min_score,
        search=search,
        include_dismissed=include_dismissed,
        sort=sort,
    )
    for a in articles:
        a['matched_keywords'] = find_matched_keywords(a)
    last_fetch = get_last_fetch_time()
    stats = get_stats()

    return jsonify({
        "articles": articles,
        "last_fetch": last_fetch,
        "stats": stats,
        "scraping": _scraping,
    })


@app.route("/api/watchlist")
def api_watchlist():
    include_dismissed = request.args.get("include_dismissed", "false").lower() == "true"
    search = request.args.get("search", "").strip() or None
    sort = request.args.get("sort", "score")

    articles = get_articles(
        practice_area=None,
        min_score=0,
        search=search,
        include_dismissed=include_dismissed,
        sort=sort,
    )

    watchlist = get_watchlist_for_scraper()
    result = []
    for a in articles:
        triggers = find_watchlist_triggers(a)
        if triggers:
            a["watchlist_triggers"] = triggers
            result.append(a)

    return jsonify({
        "articles": result,
        "keywords": {
            "company": [kw["label"] for kw in watchlist if kw["group"] == "company"],
            "sector":  [kw["label"] for kw in watchlist if kw["group"] == "sector"],
        },
        "scraping": _scraping,
    })


@app.route("/api/articles/<int:article_id>/read", methods=["POST"])
def api_mark_read(article_id):
    mark_read(article_id)
    return jsonify({"ok": True})


@app.route("/api/articles/<int:article_id>/dismiss", methods=["POST"])
def api_dismiss(article_id):
    mark_dismissed(article_id)
    return jsonify({"ok": True})


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    global _scraping
    if _scraping:
        return jsonify({"ok": False, "message": "Scrape already running"}), 409
    thread = threading.Thread(target=scheduled_scrape, daemon=True)
    thread.start()
    return jsonify({"ok": True, "message": "Scrape started"})


@app.route("/api/digest", methods=["POST"])
def api_send_digest():
    thread = threading.Thread(target=send_digest, daemon=True)
    thread.start()
    return jsonify({"ok": True, "message": "Digest sending..."})


@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats())


# ── Keyword management routes ─────────────────────────────────────────────────

@app.route("/api/keywords", methods=["GET"])
def api_get_keywords():
    return jsonify(get_keywords())


@app.route("/api/keywords", methods=["POST"])
def api_add_keyword():
    data = request.get_json()
    keyword = (data.get("keyword") or "").strip()
    practice_area = (data.get("practice_area") or "").strip()
    if not keyword or not practice_area:
        return jsonify({"ok": False, "error": "keyword and practice_area required"}), 400
    if practice_area not in PRACTICE_AREAS:
        return jsonify({"ok": False, "error": "Invalid practice area"}), 400
    new_id = add_keyword(keyword, practice_area)
    if new_id is None:
        return jsonify({"ok": False, "error": "Keyword already exists"}), 409
    return jsonify({"ok": True, "id": new_id})


@app.route("/api/keywords/<int:keyword_id>", methods=["DELETE"])
def api_delete_keyword(keyword_id):
    delete_keyword(keyword_id)
    return jsonify({"ok": True})


# ── Watchlist management routes ───────────────────────────────────────────────

@app.route("/api/watchlist-keywords", methods=["GET"])
def api_get_watchlist_keywords():
    return jsonify(get_watchlist_db())


@app.route("/api/watchlist-keywords", methods=["POST"])
def api_add_watchlist_keyword():
    data = request.get_json()
    label = (data.get("label") or "").strip()
    pattern = (data.get("pattern") or "").strip()
    group_name = (data.get("group") or "company").strip()
    if not label or not pattern:
        return jsonify({"ok": False, "error": "label and pattern required"}), 400
    if group_name not in ("company", "sector"):
        group_name = "company"
    new_id = add_watchlist_entry(label, pattern, group_name)
    if new_id is None:
        return jsonify({"ok": False, "error": "Entry already exists"}), 409
    return jsonify({"ok": True, "id": new_id})


@app.route("/api/watchlist-keywords/<int:entry_id>", methods=["DELETE"])
def api_delete_watchlist_keyword(entry_id):
    delete_watchlist_entry(entry_id)
    return jsonify({"ok": True})


# ── Pipeline routes ───────────────────────────────────────────────────────────

@app.route("/api/pipeline", methods=["GET"])
def api_get_pipeline():
    return jsonify({"companies": get_pipeline(), "stages": PIPELINE_STAGES})


@app.route("/api/pipeline", methods=["POST"])
def api_add_pipeline():
    data = request.get_json()
    company_name = (data.get("company_name") or "").strip()
    if not company_name:
        return jsonify({"ok": False, "error": "company_name required"}), 400
    new_id = add_pipeline_company(
        company_name=company_name,
        ticker=data.get("ticker", ""),
        exchange=data.get("exchange", ""),
        commodity=data.get("commodity", ""),
        stage=data.get("stage", "Identified"),
        deal_type=data.get("deal_type", ""),
        estimated_deal_size=data.get("estimated_deal_size", ""),
        key_contacts=data.get("key_contacts", ""),
        notes=data.get("notes", ""),
        last_contact_date=data.get("last_contact_date", ""),
        source_article_url=data.get("source_article_url", ""),
    )
    return jsonify({"ok": True, "id": new_id})


@app.route("/api/pipeline/<int:company_id>", methods=["PATCH"])
def api_update_pipeline(company_id):
    data = request.get_json()
    update_pipeline_company(company_id, **data)
    return jsonify({"ok": True})


@app.route("/api/pipeline/<int:company_id>", methods=["DELETE"])
def api_delete_pipeline(company_id):
    delete_pipeline_company(company_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    init_db()

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        scheduled_scrape,
        "interval",
        hours=FETCH_INTERVAL_HOURS,
        id="scrape_job",
        max_instances=1,
    )
    scheduler.add_job(
        send_digest,
        "cron",
        hour=7,
        minute=30,
        id="digest_job",
    )
    scheduler.start()
    logger.info("Scheduler started — fetch interval: %dh, digest: 7:30 AM daily", FETCH_INTERVAL_HOURS)

    logger.info("Running initial scrape on startup...")
    thread = threading.Thread(target=scheduled_scrape, daemon=True)
    thread.start()

    app.run(host="0.0.0.0", port=5001, debug=False)
