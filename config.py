import os

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "mason_law.db")

FETCH_INTERVAL_HOURS = 1
MIN_RELEVANCE_SCORE = 2

PRACTICE_AREAS = {
    "Mining & Resources": [
        # ── Base metals & commodities ─────────────────────────────────────────
        "mining", "mineral", "gold", "copper", "silver", "lithium", "uranium",
        "cobalt", "nickel", "zinc", "iron ore", "potash", "rare earth",
        "resource", "exploration", "drill", "ore", "reserve", "royalty",
        "energy", "oil sands", "natural gas", "pipeline", "petroleum",
        "ESG", "environment impact", "tailings", "mine site", "staking",
        "NI 43-101", "technical report", "feasibility", "preliminary economic",
        "junior miner", "streaming", "royalty company", "resource estimate",
        "offtake agreement", "mine development", "open pit", "underground mine",
        # ── Critical minerals (expanded) ─────────────────────────────────────
        "critical minerals", "critical mineral", "battery metals", "battery mineral",
        "energy transition metals", "green metals", "EV metals", "strategic minerals",
        "graphite", "manganese", "vanadium", "titanium", "antimony",
        "gallium", "germanium", "indium", "tellurium", "tungsten",
        "chromium", "molybdenum", "scandium", "niobium", "tantalum",
        "rare earth elements", "REE", "neodymium", "dysprosium",
        "praseodymium", "terbium", "lanthanum", "cerium",
        "phosphate", "fluorspar", "barite", "silicon",
        # ── Government & agency investment ───────────────────────────────────
        "IFC", "International Finance Corporation",
        "DFC", "Development Finance Corporation",
        "Export Development Canada", "EDC financing",
        "World Bank mining", "IDA mining",
        "sovereign wealth fund", "sovereign fund mining",
        "state-owned enterprise", "SOE mining",
        "government offtake", "government investment mining",
        "Minerals Security Partnership", "MSP",
        "Critical Raw Materials Act", "EU critical minerals",
        "national security mining", "strategic reserve",
        "government-backed mining", "federal mining investment",
        "ministry of mines", "department of mines",
        "Export-Import Bank", "EXIM mining",
        "African Development Bank", "AfDB mining",
        "Asian Development Bank", "ADB mining",
        "Inter-American Development Bank", "IDB mining",
        "EBRD mining", "European Bank mining",
        # ── Named companies (watchlist seeds) ────────────────────────────────
        "Orion Mine Finance", "Orion Resource Partners", "OR Royalties",
        "Radisson Mining", "Osisko", "Wheaton Precious Metals",
        "Franco-Nevada", "Royal Gold", "Sandstorm Gold", "Triple Flag",
        # ── Tuple combos ─────────────────────────────────────────────────────
        ("mining", "royalty"), ("mining", "stream"), ("mining", "private placement"),
        ("mining", "prospectus"), ("mining", "plan of arrangement"),
        ("mining", "acquisition"), ("mining", "merger"), ("gold", "acquisition"),
        ("copper", "acquisition"), ("lithium", "acquisition"),
        ("cobalt", "acquisition"), ("nickel", "acquisition"),
        ("graphite", "deal"), ("vanadium", "deal"), ("manganese", "deal"),
        ("critical minerals", "deal"), ("critical minerals", "investment"),
        ("critical minerals", "acquisition"), ("battery metals", "deal"),
        ("rare earth", "acquisition"), ("REE", "deal"),
        ("government", "mining investment"), ("sovereign", "mining"),
        ("IFC", "mining"), ("DFC", "mining"), ("World Bank", "mining"),
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
        "share purchase agreement", "SPA", "closing conditions",
        "earn-out", "indemnification", "representations and warranties",
        # ── International regulatory bodies ──────────────────────────────────
        "Hart-Scott-Rodino", "HSR", "CFIUS", "foreign investment review",
        "FIRB", "Foreign Investment Review Board",       # Australia
        "European Commission merger", "EC merger control",
        "CMA", "Competition and Markets Authority",      # UK
        "SAMR", "State Administration for Market Regulation",  # China
        "Competition Tribunal", "antitrust clearance",
        "national security review", "Investment Canada Act",
        "state-owned enterprise acquisition", "SOE bid",
        "cross-border mining deal", "international mining merger",
        ("mining", "cross-border"), ("mining", "international deal"),
    ],
    "Securities & Capital Markets": [
        "IPO", "initial public offering", "TSX", "TSX-V", "TSXV", "CSE",
        "NYSE", "NASDAQ", "ASX", "LSE", "AIM", "JSE", "HKEx",   # added intl exchanges
        "listing", "delisting", "prospectus",
        "private placement", "bought deal", "short form prospectus",
        "securities commission", "OSC", "BCSC", "AMF", "CSA",
        "FCA", "ASIC", "SEC filing",                             # intl regulators
        "insider trading", "material change", "continuous disclosure",
        "SEDAR", "EDGAR", "warrant", "stock option", "flow-through",
        "equity financing", "debt financing", "debenture", "convertible",
        "capital raise", "rights offering", "normal course",
        "issuer bid", "share buyback", "dividend", "going concern",
        "cease trade", "management cease trade", "compliance",
        "national instrument", "NI 51-101", "NI 45-106", "NI 62-104",
        "government bond mining", "green bond mining", "sustainability-linked",
    ],
}

MINING_WATCHLIST = [
    # ── Target companies ──────────────────────────────────────────────────────
    {"label": "Orion Mine Finance",       "pattern": "orion mine finance",       "group": "company"},
    {"label": "Orion Resource Partners",  "pattern": "orion resource partners",  "group": "company"},
    {"label": "OR Royalties",             "pattern": "or royalties",             "group": "company"},
    {"label": "Radisson Mining",          "pattern": "radisson mining",          "group": "company"},
    {"label": "Radisson Gold",            "pattern": "radisson gold",            "group": "company"},
    {"label": "ODV",                      "pattern": "odv",                      "group": "company"},
    {"label": "RADF",                     "pattern": "radf",                     "group": "company"},
    {"label": "Osisko Development",       "pattern": "osisko development",       "group": "company"},
    {"label": "Wheaton Precious Metals",  "pattern": "wheaton precious metals",  "group": "company"},
    {"label": "Franco-Nevada",            "pattern": "franco-nevada",            "group": "company"},
    # ── Sector / deal-type keywords ───────────────────────────────────────────
    {"label": "Mining Royalty",           "pattern": "mining royalty",           "group": "sector"},
    {"label": "Gold Royalty",             "pattern": "gold royalty",             "group": "sector"},
    {"label": "Silver Stream",            "pattern": "silver stream",            "group": "sector"},
    {"label": "Stream Financing",         "pattern": "stream financing",         "group": "sector"},
    {"label": "Metal Streaming",          "pattern": "metal streaming",          "group": "sector"},
    {"label": "Royalty Financing",        "pattern": "royalty financing",        "group": "sector"},
    {"label": "Offtake Agreement",        "pattern": "offtake agreement",        "group": "sector"},
    {"label": "Junior Miner",             "pattern": "junior miner",             "group": "sector"},
    {"label": "Mining M&A",              "pattern": "mining m&a",               "group": "sector"},
    {"label": "Mine Acquisition",         "pattern": "mine acquisition",         "group": "sector"},
    {"label": "Plan of Arrangement",      "pattern": "plan of arrangement",      "group": "sector"},
    {"label": "Strategic Alternatives",   "pattern": "strategic alternatives",   "group": "sector"},
    {"label": "Going Private",            "pattern": "going private",            "group": "sector"},
    {"label": "Insider Bid",              "pattern": "insider bid",              "group": "sector"},
    {"label": "Hostile Bid",              "pattern": "hostile bid",              "group": "sector"},
    {"label": "Compulsory Acquisition",   "pattern": "compulsory acquisition",   "group": "sector"},
    {"label": "Mining Private Placement", "pattern": "mining private placement", "group": "sector"},
    {"label": "Mining Bought Deal",       "pattern": ("mining", "bought deal"),  "group": "sector"},
    {"label": "Gold Producer",            "pattern": "gold producer",            "group": "sector"},
    {"label": "Copper Mining",            "pattern": "copper mining",            "group": "sector"},
    # ── Critical minerals ─────────────────────────────────────────────────────
    {"label": "Critical Minerals",        "pattern": "critical minerals",        "group": "sector"},
    {"label": "Battery Metals",           "pattern": "battery metals",           "group": "sector"},
    {"label": "Rare Earth Deal",          "pattern": ("rare earth", "acquisition"), "group": "sector"},
    {"label": "Lithium Acquisition",      "pattern": ("lithium", "acquisition"), "group": "sector"},
    {"label": "Cobalt Acquisition",       "pattern": ("cobalt", "acquisition"),  "group": "sector"},
    {"label": "Nickel Deal",              "pattern": ("nickel", "deal"),         "group": "sector"},
    {"label": "Graphite Deal",            "pattern": ("graphite", "deal"),       "group": "sector"},
    {"label": "Vanadium Deal",            "pattern": ("vanadium", "deal"),       "group": "sector"},
    # ── Government / agency investment ───────────────────────────────────────
    {"label": "IFC Mining",               "pattern": ("IFC", "mining"),          "group": "government"},
    {"label": "DFC Mining",               "pattern": ("DFC", "mining"),          "group": "government"},
    {"label": "World Bank Mining",        "pattern": ("world bank", "mining"),   "group": "government"},
    {"label": "Sovereign Fund Mining",    "pattern": ("sovereign", "mining"),    "group": "government"},
    {"label": "Minerals Security Partnership", "pattern": "minerals security partnership", "group": "government"},
    {"label": "Critical Raw Materials Act",    "pattern": "critical raw materials act",    "group": "government"},
    {"label": "Government Mining Investment",  "pattern": ("government", "mining investment"), "group": "government"},
    {"label": "State-Owned Enterprise Mining", "pattern": ("state-owned", "mining"),          "group": "government"},
    {"label": "AfDB Mining",              "pattern": ("african development bank", "mining"),  "group": "government"},
    {"label": "ADB Mining",              "pattern": ("asian development bank", "mining"),     "group": "government"},
    {"label": "EBRD Mining",             "pattern": ("EBRD", "mining"),          "group": "government"},
    # ── Australia ─────────────────────────────────────────────────────────────
    {"label": "Mining Australia",        "pattern": ("mining", "australia"),     "group": "australia"},
    {"label": "ASX Mining Deal",         "pattern": ("ASX", "mining"),           "group": "australia"},
    {"label": "FIRB Mining",             "pattern": "FIRB",                      "group": "australia"},
    {"label": "Pilbara",                 "pattern": "pilbara",                   "group": "australia"},
    {"label": "Western Australia Mining","pattern": ("western australia", "mining"), "group": "australia"},
    {"label": "Queensland Mining",       "pattern": ("queensland", "mining"),    "group": "australia"},
    {"label": "Lithium Australia",       "pattern": ("lithium", "australia"),    "group": "australia"},
    {"label": "Iron Ore Australia",      "pattern": ("iron ore", "australia"),   "group": "australia"},
    # ── Africa ────────────────────────────────────────────────────────────────
    {"label": "Mining DRC",              "pattern": ("mining", "congo"),         "group": "africa"},
    {"label": "Mining DRC (abbrev)",     "pattern": ("mining", "DRC"),           "group": "africa"},
    {"label": "Mining Ghana",            "pattern": ("mining", "ghana"),         "group": "africa"},
    {"label": "Mining Tanzania",         "pattern": ("mining", "tanzania"),      "group": "africa"},
    {"label": "Mining Zambia",           "pattern": ("mining", "zambia"),        "group": "africa"},
    {"label": "Mining South Africa",     "pattern": ("mining", "south africa"),  "group": "africa"},
    {"label": "Mining Mali",             "pattern": ("mining", "mali"),          "group": "africa"},
    {"label": "Mining Senegal",          "pattern": ("mining", "senegal"),       "group": "africa"},
    {"label": "Mining Zimbabwe",         "pattern": ("mining", "zimbabwe"),      "group": "africa"},
    {"label": "Mining Kenya",            "pattern": ("mining", "kenya"),         "group": "africa"},
    {"label": "Mining Mozambique",       "pattern": ("mining", "mozambique"),    "group": "africa"},
    {"label": "Mining Ethiopia",         "pattern": ("mining", "ethiopia"),      "group": "africa"},
    {"label": "Mining Namibia",          "pattern": ("mining", "namibia"),       "group": "africa"},
    {"label": "JSE Mining",              "pattern": ("JSE", "mining"),           "group": "africa"},
    # ── Europe ────────────────────────────────────────────────────────────────
    {"label": "Mining Europe",           "pattern": ("mining", "europe"),        "group": "europe"},
    {"label": "Mining Scandinavia",      "pattern": ("mining", "scandinavia"),   "group": "europe"},
    {"label": "Mining Finland",          "pattern": ("mining", "finland"),       "group": "europe"},
    {"label": "Mining Sweden",           "pattern": ("mining", "sweden"),        "group": "europe"},
    {"label": "Mining Norway",           "pattern": ("mining", "norway"),        "group": "europe"},
    {"label": "Mining Portugal",         "pattern": ("mining", "portugal"),      "group": "europe"},
    {"label": "Mining UK",               "pattern": ("mining", "united kingdom"), "group": "europe"},
    {"label": "Mining Poland",           "pattern": ("mining", "poland"),        "group": "europe"},
    {"label": "Mining Serbia",           "pattern": ("mining", "serbia"),        "group": "europe"},
    {"label": "LSE Mining",              "pattern": ("LSE", "mining"),           "group": "europe"},
    {"label": "AIM Mining",              "pattern": ("AIM", "mining"),           "group": "europe"},
    {"label": "EU Critical Minerals",    "pattern": ("EU", "critical minerals"), "group": "europe"},
    # ── South America ─────────────────────────────────────────────────────────
    {"label": "Mining Chile",            "pattern": ("mining", "chile"),         "group": "south_america"},
    {"label": "Mining Peru",             "pattern": ("mining", "peru"),          "group": "south_america"},
    {"label": "Mining Brazil",           "pattern": ("mining", "brazil"),        "group": "south_america"},
    {"label": "Mining Argentina",        "pattern": ("mining", "argentina"),     "group": "south_america"},
    {"label": "Mining Colombia",         "pattern": ("mining", "colombia"),      "group": "south_america"},
    {"label": "Mining Bolivia",          "pattern": ("mining", "bolivia"),       "group": "south_america"},
    {"label": "Mining Ecuador",          "pattern": ("mining", "ecuador"),       "group": "south_america"},
    {"label": "Lithium Triangle",        "pattern": "lithium triangle",          "group": "south_america"},
    {"label": "Copper Chile",            "pattern": ("copper", "chile"),         "group": "south_america"},
    # ── Asia Pacific ──────────────────────────────────────────────────────────
    {"label": "Mining Indonesia",        "pattern": ("mining", "indonesia"),     "group": "asia_pacific"},
    {"label": "Mining Philippines",      "pattern": ("mining", "philippines"),   "group": "asia_pacific"},
    {"label": "Mining Mongolia",         "pattern": ("mining", "mongolia"),      "group": "asia_pacific"},
    {"label": "Mining Kazakhstan",       "pattern": ("mining", "kazakhstan"),    "group": "asia_pacific"},
    {"label": "Mining Papua New Guinea", "pattern": ("mining", "papua new guinea"), "group": "asia_pacific"},
    {"label": "Mining Vietnam",          "pattern": ("mining", "vietnam"),       "group": "asia_pacific"},
    {"label": "Mining China",            "pattern": ("mining", "china"),         "group": "asia_pacific"},
    {"label": "Mining Japan",            "pattern": ("mining", "japan"),         "group": "asia_pacific"},
    {"label": "Mining India",            "pattern": ("mining", "india"),         "group": "asia_pacific"},
    {"label": "Rare Earth China",        "pattern": ("rare earth", "china"),     "group": "asia_pacific"},
    {"label": "HKEx Mining",             "pattern": ("HKEx", "mining"),          "group": "asia_pacific"},
]

RSS_FEEDS = [
    # ── Press release wires ───────────────────────────────────────────────────
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
        "name": "GlobeNewswire - M&A",
        "url": "https://www.globenewswire.com/RssFeed/subjectcode/14-Mergers%20%26%20Acquisitions",
        "source": "GlobeNewswire",
    },
    {
        "name": "GlobeNewswire - Capital Markets",
        "url": "https://www.globenewswire.com/RssFeed/subjectcode/13-Capital%20Markets",
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
    # ── Google News — North America ───────────────────────────────────────────
    {
        "name": "Google News - Mining Canada TSX",
        "url": "https://news.google.com/rss/search?q=mining+Canada+TSX&hl=en-CA&gl=CA&ceid=CA:en",
        "source": "Google News",
    },
    {
        "name": "Google News - Mining M&A",
        "url": 'https://news.google.com/rss/search?q=mining+acquisition+OR+"plan+of+arrangement"+OR+"mining+merger"&hl=en-CA&gl=CA&ceid=CA:en',
        "source": "Google News",
    },
    {
        "name": "Google News - Junior Mining Finance",
        "url": 'https://news.google.com/rss/search?q="bought+deal"+OR+"private+placement"+mining&hl=en-CA&gl=CA&ceid=CA:en',
        "source": "Google News",
    },
    {
        "name": "Google News - M&A Canada",
        "url": "https://news.google.com/rss/search?q=acquisition+merger+Canada+TSX&hl=en-CA&gl=CA&ceid=CA:en",
        "source": "Google News",
    },
    {
        "name": "Google News - PE Resources",
        "url": 'https://news.google.com/rss/search?q="private+equity"+mining+OR+"resource+fund"&hl=en-CA&gl=CA&ceid=CA:en',
        "source": "Google News",
    },
    {
        "name": "Google News - Securities Canada",
        "url": "https://news.google.com/rss/search?q=securities+IPO+TSX+OSC&hl=en-CA&gl=CA&ceid=CA:en",
        "source": "Google News",
    },
    # ── Google News — International regions ──────────────────────────────────
    {
        "name": "Google News - Mining Australia",
        "url": 'https://news.google.com/rss/search?q=mining+acquisition+OR+merger+Australia+ASX&hl=en-AU&gl=AU&ceid=AU:en',
        "source": "Google News",
    },
    {
        "name": "Google News - Mining Africa",
        "url": 'https://news.google.com/rss/search?q=mining+acquisition+OR+merger+Africa+OR+DRC+OR+"South Africa"+OR+Ghana+OR+Tanzania+OR+Zambia&hl=en&gl=US&ceid=US:en',
        "source": "Google News",
    },
    {
        "name": "Google News - Mining Europe",
        "url": 'https://news.google.com/rss/search?q=mining+acquisition+OR+merger+Europe+OR+Scandinavia+OR+"United Kingdom"+OR+Finland+OR+Portugal&hl=en&gl=GB&ceid=GB:en',
        "source": "Google News",
    },
    {
        "name": "Google News - Mining South America",
        "url": 'https://news.google.com/rss/search?q=mining+acquisition+OR+merger+OR+deal+Chile+OR+Peru+OR+Brazil+OR+Argentina+OR+Colombia&hl=en&gl=US&ceid=US:en',
        "source": "Google News",
    },
    {
        "name": "Google News - Mining Asia Pacific",
        "url": 'https://news.google.com/rss/search?q=mining+acquisition+OR+merger+OR+deal+"Asia Pacific"+OR+Indonesia+OR+Philippines+OR+Mongolia+OR+Kazakhstan&hl=en&gl=US&ceid=US:en',
        "source": "Google News",
    },
    # ── Google News — Critical minerals (global) ──────────────────────────────
    {
        "name": "Google News - Critical Minerals Deals",
        "url": 'https://news.google.com/rss/search?q="critical+minerals"+acquisition+OR+deal+OR+investment&hl=en&gl=US&ceid=US:en',
        "source": "Google News",
    },
    {
        "name": "Google News - Battery Metals",
        "url": 'https://news.google.com/rss/search?q="battery+metals"+OR+"battery+minerals"+acquisition+OR+deal+OR+offtake&hl=en&gl=US&ceid=US:en',
        "source": "Google News",
    },
    {
        "name": "Google News - Lithium Deals",
        "url": 'https://news.google.com/rss/search?q=lithium+acquisition+OR+merger+OR+"offtake+agreement"+OR+"lithium+deal"&hl=en&gl=US&ceid=US:en',
        "source": "Google News",
    },
    {
        "name": "Google News - Rare Earth Deals",
        "url": 'https://news.google.com/rss/search?q="rare+earth"+OR+REE+acquisition+OR+deal+OR+investment&hl=en&gl=US&ceid=US:en',
        "source": "Google News",
    },
    {
        "name": "Google News - Cobalt Nickel Deals",
        "url": 'https://news.google.com/rss/search?q=cobalt+OR+nickel+acquisition+OR+merger+OR+"offtake+agreement"&hl=en&gl=US&ceid=US:en',
        "source": "Google News",
    },
    # ── Google News — Government & agency investment ──────────────────────────
    {
        "name": "Google News - Government Mining Investment",
        "url": 'https://news.google.com/rss/search?q=government+mining+investment+OR+"critical+minerals+strategy"+OR+"minerals+security"&hl=en&gl=US&ceid=US:en',
        "source": "Google News",
    },
    {
        "name": "Google News - DFC IFC Mining",
        "url": 'https://news.google.com/rss/search?q=DFC+OR+IFC+OR+"World+Bank"+mining+OR+"critical+minerals"+investment&hl=en&gl=US&ceid=US:en',
        "source": "Google News",
    },
    {
        "name": "Google News - Sovereign Fund Mining",
        "url": 'https://news.google.com/rss/search?q="sovereign+wealth+fund"+mining+OR+"state-owned"+mining+OR+SOE+mining&hl=en&gl=US&ceid=US:en',
        "source": "Google News",
    },
    {
        "name": "Google News - EU Critical Raw Materials",
        "url": 'https://news.google.com/rss/search?q="Critical+Raw+Materials+Act"+OR+"Minerals+Security+Partnership"+OR+"strategic+minerals"&hl=en&gl=US&ceid=US:en',
        "source": "Google News",
    },
    # ── Watchlist company feeds ───────────────────────────────────────────────
    {
        "name": "Google News - Orion Mine Finance",
        "url": 'https://news.google.com/rss/search?q="Orion+Mine+Finance"+OR+"Orion+Resource+Partners"+OR+"OR+Royalties"&hl=en-CA&gl=CA&ceid=CA:en',
        "source": "Google News",
    },
    {
        "name": "Google News - Radisson Mining",
        "url": 'https://news.google.com/rss/search?q="Radisson+Mining"+OR+"Radisson+Gold"+OR+ODV&hl=en-CA&gl=CA&ceid=CA:en',
        "source": "Google News",
    },
    # ── Mining specialist publications ────────────────────────────────────────
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
        "name": "Australian Mining",
        "url": "https://www.australianmining.com.au/feed/",
        "source": "Australian Mining",
    },
    {
        "name": "Kitco News",
        "url": "https://www.kitco.com/rss/kitconews.rss",
        "source": "Kitco",
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
    # ── Financial news ────────────────────────────────────────────────────────
    {
        "name": "Financial Post",
        "url": "https://financialpost.com/feed/",
        "source": "Financial Post",
    },
    {
        "name": "MarketWatch - Top Stories",
        "url": "https://feeds.marketwatch.com/marketwatch/topstories/",
        "source": "MarketWatch",
    },
    {
        "name": "SEC EDGAR - Current Filings",
        "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&dateb=&owner=include&count=40&search_text=&output=atom",
        "source": "SEC EDGAR",
    },
]
