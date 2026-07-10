import os

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "mason_law.db")

FETCH_INTERVAL_HOURS = 1
MIN_RELEVANCE_SCORE = 3

PRACTICE_AREAS = {
    "Mining & Resources": [
        "mining", "mineral", "gold", "copper", "silver", "lithium", "uranium",
        "resource", "exploration", "drill", "ore", "reserve", "royalty",
        "energy", "oil sands", "natural gas", "pipeline", "petroleum",
        "ESG", "environment impact", "tailings", "mine site", "staking",
        "NI 43-101", "technical report", "feasibility", "preliminary economic",
        "junior miner", "streaming", "royalty company", "resource estimate",
        "Orion Mine Finance", "Orion Resource Partners", "OR Royalties", "Radisson Mining",
        ("mining", "royalty"), ("mining", "stream"), ("mining", "private placement"),
        ("mining", "prospectus"), ("mining", "plan of arrangement"),
    ],
    "M&A/Corporate": [
        "merger", "acquisition", "takeover", "buyout", "transaction",
        "deal", "definitive agreement", "letter of intent", "LOI",
        "amalgamation", "arrangement", "plan of arrangement",
        "hostile bid", "friendly acquisition", "strategic review",
        "private equity", "venture capital", "divestiture", "spinoff",
        "consolidation", "synergy", "due diligence", "shareholder approval",
        "regulatory approval", "competition bureau", "investment canada",
        "fairness opinion", "special committee", "poison pill",
    ],
    "Securities & Capital Markets": [
        "IPO", "initial public offering", "TSX", "TSX-V", "TSXV", "CSE",
        "NYSE", "NASDAQ", "listing", "delisting", "prospectus",
        "private placement", "bought deal", "short form prospectus",
        "securities commission", "OSC", "BCSC", "AMF", "CSA",
        "insider trading", "material change", "continuous disclosure",
        "SEDAR", "EDGAR", "warrant", "stock option", "flow-through",
        "equity financing", "debt financing", "debenture", "convertible",
        "capital raise", "bought deal", "rights offering", "normal course",
        "issuer bid", "share buyback", "dividend", "going concern",
        "cease trade", "management cease trade", "compliance",
    ],
}

MINING_WATCHLIST = [
    # ── Target companies ─────────────────────────────────────────────────────
    {"label": "Orion Mine Finance",        "pattern": "orion mine finance",       "group": "company"},
    {"label": "Orion Resource Partners",   "pattern": "orion resource partners",  "group": "company"},
    {"label": "OR Royalties",              "pattern": "or royalties",             "group": "company"},
    {"label": "Radisson Mining",           "pattern": "radisson mining",          "group": "company"},
    {"label": "Radisson Gold",             "pattern": "radisson gold",            "group": "company"},
    # Tickers — user-specified; ODV = Osisko Development (TSX-V), RADF unverified
    {"label": "ODV",                       "pattern": "odv",                      "group": "company"},
    {"label": "RADF",                      "pattern": "radf",                     "group": "company"},
    # ── Sector news keywords ──────────────────────────────────────────────────
    {"label": "Mining Royalty",            "pattern": "mining royalty",           "group": "sector"},
    {"label": "Gold Royalty",              "pattern": "gold royalty",             "group": "sector"},
    {"label": "Silver Stream",             "pattern": "silver stream",            "group": "sector"},
    {"label": "Stream Financing",          "pattern": "stream financing",         "group": "sector"},
    {"label": "Metal Streaming",           "pattern": "metal streaming",          "group": "sector"},
    {"label": "Royalty Financing",         "pattern": "royalty financing",        "group": "sector"},
    {"label": "Junior Miner",              "pattern": "junior miner",             "group": "sector"},
    {"label": "Junior Mining",             "pattern": "junior mining",            "group": "sector"},
    {"label": "Mining M&A",               "pattern": "mining m&a",               "group": "sector"},
    {"label": "Mine Acquisition",          "pattern": "mine acquisition",         "group": "sector"},
    {"label": "Mining Private Placement",  "pattern": "mining private placement", "group": "sector"},
    {"label": "Mining + Bought Deal",      "pattern": ("mining", "bought deal"),  "group": "sector"},
    {"label": "Mining Capital Markets",    "pattern": "mining capital markets",   "group": "sector"},
    {"label": "Gold Producer",             "pattern": "gold producer",            "group": "sector"},
    {"label": "Copper Mining",             "pattern": "copper mining",            "group": "sector"},
    {"label": "Critical Minerals",         "pattern": "critical minerals",        "group": "sector"},
]

RSS_FEEDS = [
    {
        "name": "GlobeNewswire - Mining",
        "url": "https://www.globenewswire.com/RssFeed/industry/Mining",
        "source": "GlobeNewswire",
    },
    {
        "name": "GlobeNewswire - Financial Services",
        "url": "https://www.globenewswire.com/RssFeed/industry/Financial+Services",
        "source": "GlobeNewswire",
    },
    {
        "name": "GlobeNewswire - Energy & Natural Resources",
        "url": "https://www.globenewswire.com/RssFeed/industry/Energy",
        "source": "GlobeNewswire",
    },
    {
        "name": "Newsfile Corp",
        "url": "https://www.newsfilecorp.com/rss/newsreleases",
        "source": "Newsfile",
    },
    {
        "name": "Business Wire - Mining",
        "url": "https://feed.businesswire.com/rss/home/?rss=G22&rssid=20&rss=yes",
        "source": "Business Wire",
    },
    {
        "name": "Business Wire - M&A",
        "url": "https://feed.businesswire.com/rss/home/?rss=G18&rssid=15",
        "source": "Business Wire",
    },
    {
        "name": "Google News - Mining Canada",
        "url": "https://news.google.com/rss/search?q=mining+Canada+TSX&hl=en-CA&gl=CA&ceid=CA:en",
        "source": "Google News",
    },
    {
        "name": "Google News - M&A Canada",
        "url": "https://news.google.com/rss/search?q=acquisition+merger+Canada+TSX&hl=en-CA&gl=CA&ceid=CA:en",
        "source": "Google News",
    },
    {
        "name": "Google News - Securities Canada",
        "url": "https://news.google.com/rss/search?q=securities+IPO+TSX+OSC&hl=en-CA&gl=CA&ceid=CA:en",
        "source": "Google News",
    },
    {
        "name": "Canadian Press - Business",
        "url": "https://www.thecanadianpress.com/feed/?cat=3",
        "source": "Canadian Press",
    },
    # Mining & Resources
    {
        "name": "Mining.com",
        "url": "https://www.mining.com/feed/",
        "source": "Mining.com",
    },
    {
        "name": "Mining Weekly",
        "url": "https://www.miningweekly.com/rss",
        "source": "Mining Weekly",
    },
    {
        "name": "Northern Miner",
        "url": "https://www.northernminer.com/feed/",
        "source": "Northern Miner",
    },
    {
        "name": "Investing News - Mining",
        "url": "https://investingnews.com/innspired/mining/feed/",
        "source": "Investing News",
    },
    {
        "name": "Resource World",
        "url": "https://www.resourceworld.com/feed/",
        "source": "Resource World",
    },
    {
        "name": "Stockhouse",
        "url": "https://stockhouse.com/rss/news",
        "source": "Stockhouse",
    },
    {
        "name": "Junior Mining Network",
        "url": "https://www.juniorminingnetwork.com/feed",
        "source": "Junior Mining Network",
    },
    {
        "name": "Proactive Investors",
        "url": "https://www.proactiveinvestors.com/rss/news.rss",
        "source": "Proactive Investors",
    },
    # M&A / Corporate
    {
        "name": "Bloomberg - Markets",
        "url": "https://feeds.bloomberg.com/markets/news.rss",
        "source": "Bloomberg",
    },
    {
        "name": "GlobeNewswire - M&A",
        "url": "https://www.globenewswire.com/RssFeed/subjectcode/14-Mergers%20%26%20Acquisitions",
        "source": "GlobeNewswire",
    },
    {
        "name": "Reuters - M&A",
        "url": "https://www.reuters.com/rssFeed/mergersNews",
        "source": "Reuters",
    },
    {
        "name": "MarketWatch - Top Stories",
        "url": "https://feeds.marketwatch.com/marketwatch/topstories/",
        "source": "MarketWatch",
    },
    # Securities & Capital Markets
    {
        "name": "SEC EDGAR - Current Filings",
        "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&dateb=&owner=include&count=40&search_text=&output=atom",
        "source": "SEC EDGAR",
    },
    {
        "name": "GlobeNewswire - Capital Markets",
        "url": "https://www.globenewswire.com/RssFeed/subjectcode/13-Capital%20Markets",
        "source": "GlobeNewswire",
    },
    {
        "name": "Financial Post",
        "url": "https://financialpost.com/feed/",
        "source": "Financial Post",
    },
]
