from __future__ import annotations

from app.bootstrap import Container
from app.settings import Settings
from logger_config import setup_logging


def main() -> None:
    settings = Settings.from_env()
    logger = setup_logging(settings.log_file_path)
    container = Container(settings, logger, enable_command_server=False)
    try:
        container.scheduler.run()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    finally:
        container.scheduler.stop()


if __name__ == "__main__":
    main()
