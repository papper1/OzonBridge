from __future__ import annotations

from app.settings import Settings
from db.repositories.shop_channels import ShopChannelsRepository
from db.repositories.shop_credentials import ShopCredentialsRepository
from db.repositories.shops import ShopsRepository
from db.schema import create_schema
from db.session import Database


def main() -> None:
    settings = Settings.from_env()
    if not settings.seed_shop_code or not settings.seed_shop_name:
        raise SystemExit("Missing SEED_SHOP_CODE or SEED_SHOP_NAME")
    database = Database(settings.database_url)
    create_schema(database)

    shops = ShopsRepository(database)
    credentials = ShopCredentialsRepository(database)
    channels = ShopChannelsRepository(database)

    shop_id = shops.upsert_seed_shop(
        code=settings.seed_shop_code,
        name=settings.seed_shop_name,
        timezone=settings.seed_shop_timezone,
        poll_interval_seconds=settings.default_poll_interval_seconds,
    )
    if settings.seed_ozon_client_id and settings.seed_ozon_api_key:
        credentials.upsert_seed_credential(
            shop_id=shop_id,
            client_id=settings.seed_ozon_client_id,
            api_key=settings.seed_ozon_api_key,
        )
    if settings.seed_lark_webhook_url:
        channels.upsert_channel(
            shop_id=shop_id,
            channel_type="lark",
            channel_name="default-lark",
            target=settings.seed_lark_webhook_url,
            secret=None,
        )
    if settings.seed_telegram_chat_id and settings.seed_telegram_bot_token:
        channels.upsert_channel(
            shop_id=shop_id,
            channel_type="telegram",
            channel_name="default-telegram",
            target=settings.seed_telegram_chat_id,
            secret=settings.seed_telegram_bot_token,
        )
    print(f"Seeded shop_id={shop_id} code={settings.seed_shop_code}")


if __name__ == "__main__":
    main()
