import json
import logging
import time
import feedparser
import anthropic
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, PRACTICE_AREAS, RSS_FEEDS, MIN_RELEVANCE_SCORE
from database import insert_article, url_exists

logger = logging.getLogger(__name__)

_client = None

# Flat set of all keywords for fast pre-filtering before calling Claude.
# Any article that doesn't contain at least one of these is skipped entirely,
# saving the API call cost.
_ALL_KEYWORDS = []
for _kws in PRACTICE_AREAS.values():
    _ALL_KEYWORDS.extend(_kws)


def _passes_prefilter(title: str, description: str) -> bool:
    """Return True if the article contains at least one practice-area keyword.
    This is a cheap check that avoids unnecessary Claude API calls."""
    text = f"{title} {description or ''}".lower()
    for kw in _ALL_KEYWORDS:
        if isinstance(kw, tuple):
            if all(part.lower() in text for part in kw):
                return True
        else:
            if kw.lower() in text:
                return True
    return False


def get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def score_article(title, description, practice_area):
    keywords = PRACTICE_AREAS.get(practice_area, [])
    keyword_list = ", ".join(
        " AND ".join(kw) if isinstance(kw, tuple) else kw
        for kw in keywords[:20]
    )

    prompt = f"""You are a legal news analyst for Mason Law, a Canadian law firm specializing in Mining & Resources, M&A/Corporate, and Securities & Capital Markets.

Evaluate this article for the practice area: {practice_area}

Article title: {title}
Article description: {description[:500] if description else "N/A"}

Relevant keywords for this area: {keyword_list}

Rate the relevance on a scale of 0-10:
- 8-10: Highly relevant (directly involves Canadian companies/deals in this practice area)
- 5-7: Moderately relevant (tangentially related or involves non-Canadian deals)
- 3-4: Low relevance (general industry news with minor connection)
- 0-2: Not relevant

Respond with JSON only, no explanation:
{{"score": <number 0-10>, "summary": "<one sentence explaining why this is relevant to {practice_area} lawyers>"}}"""

    try:
        message = get_client().messages.create(
            model=CLAUDE_MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
        score = float(result.get("score", 0))
        summary = result.get("summary", "")
        return round(min(max(score, 0), 10), 1), summary
    except Exception as e:
        logger.error("Claude scoring failed for '%s': %s", title, e)
        return 0.0, ""


def parse_date(entry):
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                pass
    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return parsedate_to_datetime(val).isoformat()
            except Exception:
                pass
    return datetime.now(timezone.utc).isoformat()


def classify_practice_area(title, description):
    text = f"{title} {description or ''}".lower()
    scores = {}
    for area, keywords in PRACTICE_AREAS.items():
        count = 0
        for kw in keywords:
            if isinstance(kw, tuple):
                if all(part.lower() in text for part in kw):
                    count += 2  # tuple matches are more specific — weight them higher
            else:
                if kw.lower() in text:
                    count += 1
        scores[area] = count
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "M&A/Corporate"


def fetch_feed(feed_config):
    url = feed_config["url"]
    source = feed_config["source"]
    logger.info("Fetching feed: %s", feed_config["name"])

    try:
        parsed = feedparser.parse(url, agent="MasonLawMonitor/1.0")
    except Exception as e:
        logger.error("Failed to parse feed %s: %s", url, e)
        return 0

    if parsed.bozo and not parsed.entries:
        logger.warning("Feed returned no entries (possibly dead): %s", feed_config["name"])
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    saved = 0

    # Increased from 30 → 50 so slow-moving feeds don't get truncated
    for entry in parsed.entries[:50]:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        if not title or not link:
            continue
        if url_exists(link):
            continue

        description = getattr(entry, "summary", "") or getattr(entry, "description", "")
        published_at = parse_date(entry)

        try:
            pub_dt = datetime.fromisoformat(published_at)
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            if pub_dt < cutoff:
                logger.debug("Skipping old article (%s): %s", published_at[:10], title[:60])
                continue
        except Exception:
            pass

        # ── Pre-filter: skip articles with zero keyword matches entirely ──────
        if not _passes_prefilter(title, description):
            logger.debug("Pre-filter skip: %s", title[:80])
            continue

        practice_area = classify_practice_area(title, description)

        # ── Claude scoring (only reached if pre-filter passes) ────────────────
        score, summary = score_article(title, description, practice_area)
        if score < MIN_RELEVANCE_SCORE:
            logger.debug("Low score (%.1f), skipping: %s", score, title[:60])
            continue

        if insert_article(title, link, source, published_at, practice_area, score, summary):
            saved += 1
            logger.info("Saved [%.1f] %s", score, title[:80])

        time.sleep(0.3)

    return saved


def run_scraper():
    logger.info("Starting scrape run across %d feeds", len(RSS_FEEDS))
    total = 0
    for feed in RSS_FEEDS:
        try:
            count = fetch_feed(feed)
            total += count
        except Exception as e:
            logger.error("Error in feed %s: %s", feed.get("name"), e)
    logger.info("Scrape complete. Saved %d new articles.", total)
    return total
