from __future__ import annotations

import argparse

from app.settings import Settings
from db.repositories.shop_channels import ShopChannelsRepository
from db.repositories.shop_credentials import ShopCredentialsRepository
from db.repositories.shops import ShopsRepository
from db.schema import create_schema
from db.session import Database


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Add or update one shop in PostgreSQL.",
    )
    parser.add_argument("--code", required=True, help="Unique shop code used in commands.")
    parser.add_argument("--name", required=True, help="Display name of the shop.")
    parser.add_argument(
        "--timezone",
        default="Asia/Bangkok",
        help="IANA timezone, default: Asia/Bangkok",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=None,
        help="Polling interval in seconds. Default uses env setting.",
    )
    parser.add_argument("--client-id", required=True, help="Ozon client id / seller id.")
    parser.add_argument("--api-key", required=True, help="Ozon API key.")
    parser.add_argument(
        "--lark-webhook",
        default="",
        help="Optional Lark webhook URL for notifications.",
    )
    parser.add_argument(
        "--telegram-chat-id",
        default="",
        help="Optional Telegram chat id for notifications.",
    )
    parser.add_argument(
        "--telegram-bot-token",
        default="",
        help="Optional Telegram bot token used with telegram chat id.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = Settings.from_env()
    database = Database(settings.database_url)
    create_schema(database)

    shops = ShopsRepository(database)
    credentials = ShopCredentialsRepository(database)
    channels = ShopChannelsRepository(database)

    poll_interval_seconds = args.poll_interval_seconds or settings.default_poll_interval_seconds
    shop_id = shops.upsert_seed_shop(
        code=args.code.strip(),
        name=args.name.strip(),
        timezone=args.timezone.strip(),
        poll_interval_seconds=poll_interval_seconds,
    )

    credentials.upsert_seed_credential(
        shop_id=shop_id,
        client_id=args.client_id.strip(),
        api_key=args.api_key.strip(),
    )

    if args.lark_webhook.strip():
        channels.upsert_channel(
            shop_id=shop_id,
            channel_type="lark",
            channel_name="default-lark",
            target=args.lark_webhook.strip(),
            secret=None,
        )

    if args.telegram_chat_id.strip() and args.telegram_bot_token.strip():
        channels.upsert_channel(
            shop_id=shop_id,
            channel_type="telegram",
            channel_name="default-telegram",
            target=args.telegram_chat_id.strip(),
            secret=args.telegram_bot_token.strip(),
        )

    print(f"Shop upserted successfully: shop_id={shop_id} code={args.code.strip()}")


if __name__ == "__main__":
    main()
