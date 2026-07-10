"""
digest.py — Daily email digest for Mason Law Monitor

Sends a Gmail digest with:
  - Top 5 highlights (highest scored articles from past 24h)
  - Full breakdown by practice area

Required environment variables:
  DIGEST_EMAIL_FROM   — Gmail address to send FROM (e.g. you@gmail.com)
  DIGEST_EMAIL_TO     — Address to send TO (can be same as FROM)
  DIGEST_EMAIL_PASS   — Gmail App Password (NOT your regular Gmail password)
                        Generate one at: https://myaccount.google.com/apppasswords
"""

import logging
import os
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from database import get_articles

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_FROM = os.environ.get("DIGEST_EMAIL_FROM", "")
EMAIL_TO   = os.environ.get("DIGEST_EMAIL_TO", "")
EMAIL_PASS = os.environ.get("DIGEST_EMAIL_PASS", "")

PRACTICE_AREAS = ["Mining & Resources", "M&A/Corporate", "Securities & Capital Markets"]


def _get_recent_articles(hours=24):
    """Pull all articles from the last N hours across all practice areas."""
    all_articles = []
    for area in PRACTICE_AREAS:
        articles = get_articles(practice_area=area, min_score=0, include_dismissed=False)
        all_articles.extend(articles)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent = []
    seen = set()
    for a in all_articles:
        if a["url"] in seen:
            continue
        seen.add(a["url"])
        try:
            pub = datetime.fromisoformat(a["published_at"])
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if pub >= cutoff:
                recent.append(a)
        except Exception:
            pass

    return sorted(recent, key=lambda x: x.get("score", 0), reverse=True)


def _build_html(articles):
    today = datetime.now().strftime("%B %d, %Y")

    # Split into top highlights and by-area buckets
    top = articles[:5]
    by_area = {area: [] for area in PRACTICE_AREAS}
    for a in articles:
        area = a.get("practice_area", "M&A/Corporate")
        if area in by_area:
            by_area[area].append(a)

    def article_row(a, show_area=False):
        score = a.get("score", 0)
        score_color = "#16a34a" if score >= 7 else "#ca8a04" if score >= 4 else "#6b7280"
        area_tag = f'<span style="font-size:11px;color:#6b7280;"> [{a.get("practice_area","")}]</span>' if show_area else ""
        summary = a.get("summary", "") or a.get("description", "")
        summary_html = f'<p style="margin:4px 0 0 0;font-size:13px;color:#4b5563;">{summary[:200]}{"…" if len(summary)>200 else ""}</p>' if summary else ""
        return f"""
        <tr>
          <td style="padding:12px 0;border-bottom:1px solid #f3f4f6;vertical-align:top;">
            <span style="display:inline-block;background:{score_color};color:white;font-size:11px;
                         font-weight:600;padding:2px 6px;border-radius:4px;margin-right:8px;">{score:.1f}</span>
            <a href="{a['url']}" style="color:#1d4ed8;font-weight:600;font-size:14px;text-decoration:none;">
              {a['title']}{area_tag}
            </a>
            {summary_html}
            <p style="margin:4px 0 0 0;font-size:11px;color:#9ca3af;">
              {a.get('source','')} &nbsp;·&nbsp; {a.get('published_at','')[:10]}
            </p>
          </td>
        </tr>"""

    highlights_rows = "".join(article_row(a, show_area=True) for a in top) if top else \
        "<tr><td style='padding:12px 0;color:#6b7280;font-size:13px;'>No new articles in the last 24 hours.</td></tr>"

    area_sections = ""
    area_colors = {
        "Mining & Resources": "#92400e",
        "M&A/Corporate": "#1e40af",
        "Securities & Capital Markets": "#065f46",
    }
    for area in PRACTICE_AREAS:
        items = by_area[area]
        color = area_colors.get(area, "#374151")
        rows = "".join(article_row(a) for a in items) if items else \
            "<tr><td style='padding:12px 0;color:#6b7280;font-size:13px;'>No new articles.</td></tr>"
        area_sections += f"""
        <h2 style="color:{color};font-size:16px;margin:28px 0 8px 0;padding-bottom:6px;
                    border-bottom:2px solid {color};">{area}</h2>
        <table width="100%" cellpadding="0" cellspacing="0">{rows}</table>"""

    total = len(articles)
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
             max-width:680px;margin:0 auto;padding:24px;color:#111827;background:#ffffff;">

  <div style="background:#1e3a5f;color:white;padding:20px 24px;border-radius:8px;margin-bottom:24px;">
    <h1 style="margin:0;font-size:20px;">Mason Law — Daily News Digest</h1>
    <p style="margin:6px 0 0 0;font-size:13px;opacity:0.8;">{today} &nbsp;·&nbsp; {total} new article{"s" if total!=1 else ""} in the last 24 hours</p>
  </div>

  <h2 style="color:#111827;font-size:16px;margin:0 0 8px 0;">⭐ Top Highlights</h2>
  <table width="100%" cellpadding="0" cellspacing="0">{highlights_rows}</table>

  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <h2 style="color:#111827;font-size:16px;margin:0 0 4px 0;">Full Breakdown</h2>
  {area_sections}

  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <p style="font-size:11px;color:#9ca3af;text-align:center;">
    Mason Law Monitor &nbsp;·&nbsp; Automated digest &nbsp;·&nbsp; Open the app at http://localhost:5001
  </p>
</body>
</html>"""


def send_digest():
    """Build and send the daily digest email. Called by the scheduler."""
    if not all([EMAIL_FROM, EMAIL_TO, EMAIL_PASS]):
        logger.warning("Digest email not configured — set DIGEST_EMAIL_FROM, DIGEST_EMAIL_TO, DIGEST_EMAIL_PASS")
        return

    logger.info("Building daily digest...")
    articles = _get_recent_articles(hours=24)
    html = _build_html(articles)

    today = datetime.now().strftime("%B %d, %Y")
    subject = f"Mason Law News Digest — {today} ({len(articles)} new articles)"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASS)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        logger.info("Digest sent to %s (%d articles)", EMAIL_TO, len(articles))
    except Exception as e:
        logger.error("Failed to send digest: %s", e)


if __name__ == "__main__":
    # Run manually to test: python3 digest.py
    logging.basicConfig(level=logging.INFO)
    send_digest()
