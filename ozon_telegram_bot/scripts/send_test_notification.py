from __future__ import annotations

import argparse
from datetime import datetime, timezone

from app.settings import Settings
from core.models import ShopChannel
from db.repositories.notification_log import NotificationLogRepository
from db.repositories.shop_channels import ShopChannelsRepository
from db.repositories.shops import ShopsRepository
from db.schema import create_schema
from db.session import Database
from formatters.message_formatter import MessageFormatter
from integrations.lark_client import LarkWebhookClient
from integrations.telegram_client import TelegramBotClient
from logger_config import setup_logging
from services.notifications import NotificationService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send a test notification to the configured channels of one shop.",
    )
    parser.add_argument("--shop-code", help="Target shop code from the shops table.")
    parser.add_argument(
        "--event-type",
        default="customer_question",
        choices=("order", "refund", "cancellation_request", "customer_question"),
        help="Notification scenario to simulate.",
    )
    parser.add_argument(
        "--message",
        help="Optional raw message text. When set, this overrides the built-in template.",
    )
    parser.add_argument(
        "--channel-type",
        choices=("lark", "telegram"),
        help="Optional channel filter. Default sends to all active channels of the shop.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the generated message only. No send and no database write.",
    )
    parser.add_argument(
        "--lark-webhook-url",
        help="Send directly to this Lark webhook instead of loading channels from DB.",
    )
    parser.add_argument(
        "--telegram-chat-id",
        help="Send directly to this Telegram chat id instead of loading channels from DB.",
    )
    parser.add_argument(
        "--telegram-bot-token",
        help="Bot token used together with --telegram-chat-id.",
    )
    return parser


def build_message(
    formatter: MessageFormatter,
    event_type: str,
    shop_name: str,
    marker: str,
) -> tuple[str, dict]:
    if event_type == "order":
        payload = {
            "shop_name": shop_name,
            "posting_number": f"TEST-{marker}",
            "status": "awaiting_packaging",
            "product_name": "San pham test",
            "quantity": 1,
            "price": 199000,
            "currency": "RUB",
            "created_or_in_process_at": marker,
            "shipment_date": marker,
        }
        return formatter.format_order(payload), payload

    if event_type == "refund":
        payload = {
            "shop_name": shop_name,
            "return_number": f"TEST-RETURN-{marker}",
            "return_type": "refund",
            "posting_number": f"TEST-{marker}",
            "status": f"preview-{marker}",
            "reason": "Khach muon hoan hang",
            "created_date": marker,
            "changed_date": marker,
        }
        return formatter.format_return(payload), payload

    if event_type == "cancellation_request":
        payload = {
            "shop_name": shop_name,
            "return_number": f"TEST-CANCEL-{marker}",
            "return_type": "cancellation",
            "posting_number": f"TEST-{marker}",
            "status": f"preview-{marker}",
            "reason": "Khach yeu cau huy don",
            "created_date": marker,
            "changed_date": marker,
        }
        return formatter.format_return(payload), payload

    payload = {
        "shop_name": shop_name,
        "status": f"preview-{marker}",
        "customer_message": "Khach hoi ve tinh trang don hoac yeu cau ho tro.",
    }
    message = (
        "Tin nhan khach hang\n\n"
        f"Shop: {shop_name}\n"
        f"Loai: customer_question\n"
        f"Noi dung: {payload['customer_message']}\n"
        f"Ma test: {marker}"
    )
    return message, payload


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings.from_env()
    logger = setup_logging(settings.log_file_path)
    formatter = MessageFormatter()
    marker = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    direct_channels: list[ShopChannel] = []
    if args.lark_webhook_url:
        direct_channels.append(
            ShopChannel(
                id=0,
                shop_id=0,
                channel_type="lark",
                channel_name="manual-lark",
                target=args.lark_webhook_url,
                secret=None,
                is_active=True,
            )
        )
    if args.telegram_chat_id or args.telegram_bot_token:
        if not (args.telegram_chat_id and args.telegram_bot_token):
            raise SystemExit("--telegram-chat-id va --telegram-bot-token phai di cung nhau")
        direct_channels.append(
            ShopChannel(
                id=0,
                shop_id=0,
                channel_type="telegram",
                channel_name="manual-telegram",
                target=args.telegram_chat_id,
                secret=args.telegram_bot_token,
                is_active=True,
            )
        )

    database = None
    shop = None
    channels: list[ShopChannel] = []
    shop_name = args.shop_code or "TEST_SHOP"

    if direct_channels:
        channels = direct_channels
    else:
        if not args.shop_code:
            raise SystemExit("Can --shop-code neu ban khong truyen webhook/chat test rieng")
        database = Database(settings.database_url)
        create_schema(database)
        shops = ShopsRepository(database)
        channels_repo = ShopChannelsRepository(database)
        shop = shops.get_by_code(args.shop_code)
        if shop is None:
            raise SystemExit(f"Shop code not found: {args.shop_code}")
        shop_name = shop.name
        channels = channels_repo.list_active(shop.id)
        if args.channel_type:
            channels = [channel for channel in channels if channel.channel_type == args.channel_type]
        if not channels:
            raise SystemExit(f"No active channels found for shop: {args.shop_code}")

    default_message, payload = build_message(formatter, args.event_type, shop_name, marker)
    message = args.message.strip() if args.message else default_message

    if args.dry_run:
        print("DRY RUN - no send, no database write")
        print(f"event_type={args.event_type}")
        print(f"marker={marker}")
        print(f"channels={[channel.channel_type for channel in channels]}")
        print()
        print(message)
        return

    lark_client = LarkWebhookClient(settings.request_timeout_seconds, logger)
    telegram_client = TelegramBotClient(settings.request_timeout_seconds, logger)

    if database is None:
        for channel in channels:
            if channel.channel_type == "lark":
                lark_client.send_message(channel.target, message)
            elif channel.channel_type == "telegram":
                if not channel.secret:
                    raise SystemExit("Telegram test channel is missing bot token")
                telegram_client.send_message(channel.secret, channel.target, message)
        print(
            f"Sent direct test notification event_type={args.event_type} "
            f"channels={len(channels)} marker={marker}"
        )
        return

    notifications = NotificationService(
        NotificationLogRepository(database),
        lark_client,
        telegram_client,
        logger,
    )
    notifications.send_once(
        shop_id=shop.id if shop is not None else 0,
        channels=channels,
        event_type=args.event_type,
        entity_key=f"manual-test-{marker}",
        payload=payload,
        message=message,
    )
    print(
        f"Sent test notification for shop={shop.code} event_type={args.event_type} "
        f"channels={len(channels)} marker={marker}"
    )


if __name__ == "__main__":
    main()
