"""
Shared Hummingbot API client helper.

Auth priority:
  1. ~/mcp/.env  (HUMMINGBOT_API_URL, HUMMINGBOT_USERNAME, HUMMINGBOT_PASSWORD)
  2. ~/.hummingbot/.env
  3. Environment variables
  4. Defaults: http://localhost:8000 / admin / admin
"""

import os
from contextlib import asynccontextmanager
from hummingbot_api_client import HummingbotAPIClient


ENV_PATHS = [
    os.path.expanduser("~/mcp/.env"),
    os.path.expanduser("~/.hummingbot/.env"),
    ".env",
]


def load_env():
    """Load .env file — first match wins."""
    for path in ENV_PATHS:
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        os.environ.setdefault(
                            key.strip(),
                            value.strip().strip('"').strip("'"),
                        )
            return path
    return None


def get_config():
    """Return (url, username, password) from env."""
    load_env()
    return (
        os.environ.get("HUMMINGBOT_API_URL", "http://localhost:8000"),
        os.environ.get("HUMMINGBOT_USERNAME", "admin"),
        os.environ.get("HUMMINGBOT_PASSWORD", "admin"),
    )


@asynccontextmanager
async def client():
    """Async context manager yielding a configured HummingbotAPIClient."""
    url, username, password = get_config()
    async with HummingbotAPIClient(url, username, password) as c:
        yield c


def print_table(rows: list[dict], columns: list[str] | None = None):
    """Print a list of dicts as a plain text table."""
    if not rows:
        print("(no data)")
        return
    cols = columns or list(rows[0].keys())
    widths = {c: len(c) for c in cols}
    for row in rows:
        for c in cols:
            widths[c] = max(widths[c], len(str(row.get(c, ""))))
    header = "  ".join(c.upper().ljust(widths[c]) for c in cols)
    separator = "  ".join("-" * widths[c] for c in cols)
    print(header)
    print(separator)
    for row in rows:
        print("  ".join(str(row.get(c, "")).ljust(widths[c]) for c in cols))
