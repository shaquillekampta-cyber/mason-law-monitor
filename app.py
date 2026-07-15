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
    get_alerts, add_alert, update_alert, delete_alert,
    check_new_articles_against_alerts, get_article_alert_names,
    get_companies, get_company, add_company, update_company, delete_company,
    get_related_articles,
)
from scraper import run_scraper
from digest import send_digest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Run init_db at module level so gunicorn creates all tables on startup
init_db()

_scrape_lock = threading.Lock()
_scraping = False


def find_watchlist_triggers(article, watchlist):
    """Pass watchlist in so it's fetched once per request, not per article."""
    text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    triggered = []
    for kw in watchlist:
        pattern = kw["pattern"]
        if isinstance(pattern, tuple):
            if all(part.lower() in text for part in pattern):
                triggered.append({"label": kw["label"], "group": kw["group"]})
        else:
            if pattern.lower() in text:
                triggered.append({"label": kw["label"], "group": kw["group"]})
    return triggered


def find_matched_keywords(article, all_keywords):
    """Pass all_keywords in so it's fetched once per request, not per article."""
    text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    keywords = all_keywords.get(article.get('practice_area', ''), [])
    matched = []
    for kw in keywords:
        if isinstance(kw, tuple):
            if all(part.lower() in text for part in kw):
                matched.append(" + ".join(kw))
        else:
            if kw.lower() in text:
                matched.append(kw)
    return matched


def send_alert_emails(matches):
    """Send one email per alert that fired, listing all matching articles."""
    import smtplib, os
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from collections import defaultdict

    email_from = os.environ.get("DIGEST_EMAIL_FROM", "")
    email_to   = os.environ.get("DIGEST_EMAIL_TO", "")
    email_pass = os.environ.get("DIGEST_EMAIL_PASS", "")
    if not all([email_from, email_to, email_pass]):
        logger.warning("Alert email skipped — email env vars not set")
        return

    # Group matches by alert
    by_alert = defaultdict(list)
    for alert, article in matches:
        by_alert[alert["name"]].append(article)

    for alert_name, articles in by_alert.items():
        try:
            subject = f"⚡ Deal Alert: {alert_name} — {len(articles)} new article{'s' if len(articles) > 1 else ''}"
            rows = ""
            for a in articles:
                score = a.get("relevance_score", 0)
                rows += f"""
                <tr>
                  <td style="padding:12px 0;border-bottom:1px solid #2a3347;">
                    <a href="{a['url']}" style="color:#3b82f6;font-size:14px;font-weight:600;text-decoration:none;">{a['title']}</a><br>
                    <span style="color:#8899b4;font-size:12px;">{a.get('source','')} · {a.get('practice_area','')} · Score: {score:.1f}</span>
                    {f'<p style="color:#cbd5e1;font-size:12px;margin:6px 0 0;">{a["summary"][:200]}…</p>' if a.get('summary') else ''}
                  </td>
                </tr>"""

            html = f"""
            <html><body style="background:#0f1117;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:32px;">
              <div style="max-width:600px;margin:0 auto;">
                <div style="background:#1e2535;border:1px solid #2a3347;border-radius:10px;padding:24px;">
                  <h2 style="color:#f59e0b;margin:0 0 4px;">⚡ Deal Alert Triggered</h2>
                  <p style="color:#8899b4;font-size:13px;margin:0 0 20px;">Alert: <strong style="color:#e2e8f0;">{alert_name}</strong></p>
                  <table style="width:100%;border-collapse:collapse;">{rows}</table>
                  <p style="color:#8899b4;font-size:11px;margin:20px 0 0;">
                    View full dashboard → <a href="https://mason-law-monitor.onrender.com" style="color:#3b82f6;">mason-law-monitor.onrender.com</a>
                  </p>
                </div>
              </div>
            </body></html>"""

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = email_from
            msg["To"] = email_to
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(email_from, email_pass)
                server.sendmail(email_from, email_to, msg.as_string())
            logger.info("Alert email sent for: %s (%d articles)", alert_name, len(articles))
        except Exception as e:
            logger.error("Failed to send alert email for %s: %s", alert_name, e)


def scheduled_scrape():
    global _scraping
    if _scraping:
        logger.info("Scrape already in progress, skipping")
        return
    _scraping = True
    try:
        run_scraper()
        # Check alerts after every scrape
        matches = check_new_articles_against_alerts()
        if matches:
            logger.info("Alert check: %d new match(es) found", len(matches))
            threading.Thread(target=send_alert_emails, args=(matches,), daemon=True).start()
        else:
            logger.info("Alert check: no new matches")
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
    # Fetch these once per request, not once per article
    from database import get_all_keywords_for_scraper
    all_keywords = get_all_keywords_for_scraper()
    alert_map = get_article_alert_names()
    for a in articles:
        a['matched_keywords'] = find_matched_keywords(a, all_keywords)
        a['alert_names'] = alert_map.get(a['id'], [])
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

    watchlist = get_watchlist_for_scraper()  # fetched once
    result = []
    for a in articles:
        triggers = find_watchlist_triggers(a, watchlist)
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


# ── Alert routes ─────────────────────────────────────────────────────────────

@app.route("/api/alerts", methods=["GET"])
def api_get_alerts():
    return jsonify(get_alerts())


@app.route("/api/alerts", methods=["POST"])
def api_add_alert():
    data = request.get_json()
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "name required"}), 400
    new_id = add_alert(
        name=name,
        keywords=data.get("keywords", ""),
        practice_area=data.get("practice_area", "Any"),
        min_score=float(data.get("min_score", 5)),
    )
    return jsonify({"ok": True, "id": new_id})


@app.route("/api/alerts/<int:alert_id>", methods=["PATCH"])
def api_update_alert(alert_id):
    data = request.get_json()
    update_alert(alert_id, **data)
    return jsonify({"ok": True})


@app.route("/api/alerts/<int:alert_id>", methods=["DELETE"])
def api_delete_alert(alert_id):
    delete_alert(alert_id)
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


# ── Company profile routes ────────────────────────────────────────────────────

@app.route("/api/companies", methods=["GET"])
def api_get_companies():
    search = request.args.get("search", "").strip() or None
    commodity = request.args.get("commodity", "").strip() or None
    return jsonify(get_companies(search=search, commodity=commodity))


@app.route("/api/companies/<int:company_id>", methods=["GET"])
def api_get_company(company_id):
    company = get_company(company_id)
    if not company:
        return jsonify({"error": "Not found"}), 404
    company["related_articles"] = get_related_articles(company["name"], company.get("ticker", ""))
    return jsonify(company)


@app.route("/api/companies", methods=["POST"])
def api_add_company():
    data = request.get_json()
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "name required"}), 400
    new_id = add_company(
        name=name,
        ticker=data.get("ticker", ""),
        exchange=data.get("exchange", ""),
        market_cap=data.get("market_cap", ""),
        province=data.get("province", ""),
        executives=data.get("executives", ""),
        board_members=data.get("board_members", ""),
        legal_counsel=data.get("legal_counsel", ""),
        projects=data.get("projects", ""),
        commodity=data.get("commodity", ""),
        notes=data.get("notes", ""),
    )
    return jsonify({"ok": True, "id": new_id})


@app.route("/api/companies/<int:company_id>", methods=["PATCH"])
def api_update_company(company_id):
    data = request.get_json()
    update_company(company_id, **data)
    return jsonify({"ok": True})


@app.route("/api/companies/<int:company_id>", methods=["DELETE"])
def api_delete_company(company_id):
    delete_company(company_id)
    return jsonify({"ok": True})


# ── AI Email Composer ─────────────────────────────────────────────────────────

@app.route("/api/compose-email", methods=["POST"])
def api_compose_email():
    import anthropic, os
    data = request.get_json()
    company_id = data.get("company_id")
    email_type = data.get("email_type", "introduction")  # introduction | follow_up
    recipient_name = (data.get("recipient_name") or "").strip()
    recipient_role = (data.get("recipient_role") or "").strip()
    sender_name = (data.get("sender_name") or "").strip()
    sender_firm = (data.get("sender_firm") or "").strip()
    custom_notes = (data.get("custom_notes") or "").strip()

    company = get_company(company_id) if company_id else None
    related = get_related_articles(company["name"], company.get("ticker", ""), limit=3) if company else []

    # Build context block
    company_context = ""
    if company:
        company_context = f"""
Company: {company['name']} ({company.get('ticker','')}:{company.get('exchange','')})
Commodity: {company.get('commodity','')}
Market Cap: {company.get('market_cap','')}
Province: {company.get('province','')}
Projects: {company.get('projects','')}
Key Executives: {company.get('executives','')}
Legal Counsel: {company.get('legal_counsel','Unknown')}
"""
    if related:
        company_context += "\nRecent news about this company:\n"
        for a in related:
            company_context += f"- {a['title']} ({a['source']})\n"

    type_instructions = {
        "introduction": "Write a concise, professional cold outreach email introducing the sender as a mining M&A lawyer seeking to establish a relationship. Reference the company's specific projects or recent activity to show genuine research.",
        "follow_up": "Write a warm, professional follow-up email referencing a prior conversation or outreach. Keep it brief — 3 paragraphs max. Include a clear call to action.",
    }
    instruction = type_instructions.get(email_type, type_instructions["introduction"])

    prompt = f"""You are drafting a professional email on behalf of a Canadian mining M&A lawyer.

Sender: {sender_name or 'the lawyer'}{f', {sender_firm}' if sender_firm else ''}
Recipient: {recipient_name or 'the executive'}{f', {recipient_role}' if recipient_role else ''}
Email type: {email_type.replace('_', ' ').title()}

{company_context}

Additional context from sender: {custom_notes or 'None'}

{instruction}

Rules:
- Professional but not stiff — warm, direct tone
- 3–4 short paragraphs max
- Do NOT use generic filler phrases like "I hope this email finds you well"
- Reference specific, real details from the company profile above
- End with a clear, low-pressure call to action (brief call, coffee, etc.)
- Output ONLY the email body (no subject line, no metadata)"""

    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        email_body = message.content[0].text.strip()

        # Generate subject line separately
        subject_prompt = f"Write a concise email subject line (max 10 words) for a {email_type.replace('_',' ')} email from a mining M&A lawyer to {recipient_name or 'an executive'} at {company['name'] if company else 'a mining company'}. Output only the subject line text, no quotes."
        subject_msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            messages=[{"role": "user", "content": subject_prompt}],
        )
        subject = subject_msg.content[0].text.strip()

        return jsonify({"ok": True, "subject": subject, "body": email_body})
    except Exception as e:
        logger.error("Email compose failed: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
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
