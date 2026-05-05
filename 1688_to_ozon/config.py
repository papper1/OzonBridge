import os
from pathlib import Path


def _resolve_env_path(name: str, fallback: Path) -> Path:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return fallback
    return Path(raw_value).expanduser().resolve()


# Base directory that contains the backend source code.
BASE_DIR = Path(__file__).resolve().parent

# Resource root used for templates and bundled assets.
RESOURCE_ROOT = _resolve_env_path("CRAWLDESK_RESOURCE_ROOT", BASE_DIR)

# Writable root for runtime data.
DATA_ROOT = _resolve_env_path("CRAWLDESK_DATA_DIR", BASE_DIR / "data")

# Writable template directory for CRUD from the desktop app.
TEMPLATES_DIR = _resolve_env_path("CRAWLDESK_TEMPLATES_DIR", RESOURCE_ROOT / "templates")

# Writable workbook/template asset directory.
ASSETS_TEMPLATES_DIR = _resolve_env_path(
    "CRAWLDESK_ASSETS_TEMPLATES_DIR",
    RESOURCE_ROOT / "assets" / "templates",
)

# Run browser in headless mode or not.
HEADLESS = False

# Default timeout for browser and HTTP actions in milliseconds.
DEFAULT_TIMEOUT = 30000

# Timeout for opening a product detail page in milliseconds.
PRODUCT_PAGE_TIMEOUT = 90000

# Extra wait after a product page opens so dynamic content can render.
PRODUCT_PAGE_STABILIZE_MS = 5000

# Maximum number of product links to collect from search results.
SEARCH_MAX_LINKS = 50

# Number of scroll rounds when loading more search results.
SEARCH_SCROLL_ROUNDS = 10

# File path used to persist the 1688 login session.
SESSION_FILE = DATA_ROOT / "session.json"

# Directory used by Chromium persistent context for SHEIN.
SHEIN_PROFILE_DIR = DATA_ROOT / "shein_profile"

# Directory for raw crawled HTML and JSON files.
RAW_DATA_DIR = DATA_ROOT / "raw"

# Directory for cleaned and normalized product data.
CLEAN_DATA_DIR = DATA_ROOT / "clean"

# Directory for exported Ozon files such as Excel output.
EXPORT_DIR = DATA_ROOT / "export"

# Directory for local app-facing JSON snapshots.
APP_DATA_DIR = DATA_ROOT / "app"

# Directory for application log files.
LOG_DIR = DATA_ROOT / "logs"

# Shared desktop browser settings for marketplace crawlers.
BROWSER_HEADLESS = False
BROWSER_LOCALE = "en-US"
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/135.0.0.0 Safari/537.36"
)
BROWSER_DEFAULT_VIEWPORT = {"width": 1366, "height": 768}
BROWSER_VIEWPORT_CHOICES = (
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1920, "height": 1080},
)

# Base URL for the Ozon Seller API.
OZON_API_URL = "https://api-seller.ozon.ru"

# Ozon API client identifier.
OZON_CLIENT_ID = ""

# Ozon API secret key.
OZON_API_KEY = ""


def ensure_directories() -> None:
    """Create required project data directories if they do not exist."""
    for directory in (
        RAW_DATA_DIR,
        CLEAN_DATA_DIR,
        EXPORT_DIR,
        APP_DATA_DIR,
        LOG_DIR,
        TEMPLATES_DIR,
        ASSETS_TEMPLATES_DIR,
        SHEIN_PROFILE_DIR,
        SESSION_FILE.parent,
    ):
        directory.mkdir(parents=True, exist_ok=True)
