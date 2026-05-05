import os

import uvicorn

from backend.api.main import app


def main() -> None:
    host = os.getenv("CRAWLDESK_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.getenv("CRAWLDESK_PORT", "8000").strip() or "8000")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
