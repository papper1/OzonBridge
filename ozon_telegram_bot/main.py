from __future__ import annotations

from app.bootstrap import Container
from app.settings import ConfigError, Settings
from logger_config import setup_logging


def main() -> None:
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        raise SystemExit(str(exc)) from exc

    logger = setup_logging(settings.log_file_path)
    container = Container(settings, logger)
    try:
        container.run_all()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    finally:
        container.stop_all()


if __name__ == "__main__":
    main()
