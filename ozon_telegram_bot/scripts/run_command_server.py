from __future__ import annotations

import threading

from app.bootstrap import Container
from app.settings import Settings
from logger_config import setup_logging


def main() -> None:
    settings = Settings.from_env()
    logger = setup_logging(settings.log_file_path)
    container = Container(settings, logger)
    threads: list[threading.Thread] = []
    if container.command_server.server is not None:
        threads.append(
            threading.Thread(
                target=container.command_server.serve_lark_forever,
                name="command-http",
                daemon=True,
            )
        )
    if settings.telegram_command_bot_token:
        threads.append(
            threading.Thread(
                target=container.command_server.poll_telegram_forever,
                name="command-telegram",
                daemon=True,
            )
        )
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        logger.info("Command server stopped by user")
    finally:
        container.command_server.shutdown()


if __name__ == "__main__":
    main()
