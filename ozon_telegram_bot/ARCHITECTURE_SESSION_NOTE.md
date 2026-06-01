# Ozon Telegram Bot - Architecture Session Note

## Muc tieu cua buoi lam viec

Tai cau truc bot hien tai tu mo hinh `single-shop` sang `multi-shop MVP`, uu tien:

- chay on dinh cho `1-3 shop` truoc
- khong gui trung thong bao
- khong claim trung job khi co nhieu worker
- command server uu tien doc DB thay vi goi Ozon truc tiep
- chuan bi san de scale len `20+ shop`

## Danh gia code hien tai

Code hien tai phu hop cho `1 shop / 1 process`:

- mot bo config trong `.env`
- mot `OzonClient`
- mot `StateStore` SQLite
- mot `Scheduler`
- Telegram bot chay polling
- command server Lark la optional

Han che khi scale:

- single-shop, khong co mo hinh tenant ro rang
- SQLite khong hop de mo rong nhieu worker
- scheduler dang poll tuan tu, de cham khi tang shop
- chua co co che claim job an toan
- chua co rate limit/backoff du de scale Ozon API
- command de bi phu thuoc vao API realtime neu khong dua qua DB

## Dinh huong duoc chot

Khong nhat tat ca vao bang `shops`.

Thong tin can tach rieng:

- `shops`: thong tin co ban cua shop
- `shop_credentials`: credential/API key
- `shop_channels`: kenh gui tin

Bo MVP duoc chot:

- `shops`
- `shop_credentials`
- `shop_channels`
- `poll_jobs`
- `order_state`
- `return_state`
- `notification_log`
- `command_log`
- `scheduler`
- `worker`
- `command_server`

Chua uu tien trong MVP:

- `chat_state`
- `message_state`
- dashboard
- finance/reporting nang cao
- nhieu worker song song

## Nguyen tac thiet ke

### 1. Tach du lieu shop / credential / channel

Khong luu API key, webhook, chat target truc tiep trong `shops`.

Ly do:

- de xoay key
- de ho tro nhieu kenh cho 1 shop
- de audit
- de tranh schema phong to

### 2. Worker phai claim job an toan

Claim job bang co che:

- `FOR UPDATE SKIP LOCKED`

Muc dich:

- tranh hai worker xu ly cung mot job
- mo duong cho scale worker sau nay

### 3. Scheduler khong duoc spam job

Rule:

- moi `shop_id` chi duoc co toi da `1 job queued/running` cho cung `job_type`

Muc dich:

- tranh day hang doi neu chu ky poll nhanh hon thoi gian xu ly

### 4. Notification phai idempotent

Bang `notification_log` bat buoc co:

- `idempotency_key`

Vi du:

- `shop_id:order:posting_number:status:lark`
- `shop_id:return:return_number:state:lark`

Muc dich:

- tranh gui trung thong bao khi retry/job lap lai

### 5. State phai luu payload va status

`order_state`, `return_state` va ve sau co the la `chat_state` can co:

- `raw_payload JSONB`
- `last_status`
- `last_notified_status`
- `updated_at`

Muc dich:

- biet du lieu co doi that hay khong
- biet trang thai nao da duoc notify
- de command doc du lieu nhanh tu DB

### 6. Ozon API can rate limit va backoff

Can them:

- request throttling
- retry co gioi han
- exponential backoff
- log loi API

Ly do:

- khi scale nhieu shop, Ozon API se la diem nghen dau tien

### 7. Command Server uu tien doc DB

Nguyen tac:

- lenh thong thuong nhu `/status`, `/refund`, `/cancel` uu tien doc DB
- chi lenh realtime nhu `/order_now` moi goi Ozon truc tiep

Muc dich:

- nhanh hon
- it ton request Ozon
- it nguy co dinh rate limit

### 8. Return/cancellation phai model dung nghiep vu

Khong coi `/v2/returns/rfbs/list` la refund thuan tuy.

Can dua ve logic:

- `returns_and_cancellations`

Sau do phan loai theo:

- `return_number`
- `state`
- `group_state`
- `money_return_state_name`
- hoac detail API

## Folder structure duoc de xuat

```text
ozon_telegram_bot/
  app/
    settings.py
    bootstrap.py

  core/
    models.py
    enums.py
    ids.py
    utils.py

  db/
    session.py
    schema.py
    migrations/
      versions/
    repositories/
      shops.py
      shop_credentials.py
      shop_channels.py
      poll_jobs.py
      order_state.py
      return_state.py
      notification_log.py
      command_log.py

  integrations/
    ozon_client.py
    lark_client.py
    telegram_client.py

  services/
    scheduler.py
    worker.py
    command_server.py
    command_router.py
    polling.py
    notifications.py
    rate_limit.py

  formatters/
    message_formatter.py

  scripts/
    run_scheduler.py
    run_worker.py
    run_command_server.py
    seed_shop.py

  systemd/
    ozon-scheduler.service
    ozon-worker.service
    ozon-command-server.service

  tests/
    test_scheduler.py
    test_worker.py
    test_command_server.py
    test_ozon_client.py
    test_notifications.py

  requirements.txt
  README.md
```

Luu y:

- bo trung lap `formatters.py` va `message_formatter.py`
- giu `domain` don gian, chua can tach qua nhieu service

## Database structure MVP

### `shops`

- `id`
- `code`
- `name`
- `timezone`
- `is_active`
- `created_at`
- `updated_at`

### `shop_credentials`

- `id`
- `shop_id`
- `provider`
- `client_id`
- `api_key`
- `extra_jsonb`
- `is_active`
- `created_at`
- `updated_at`

### `shop_channels`

- `id`
- `shop_id`
- `channel_type`
- `channel_name`
- `target`
- `secret`
- `is_active`
- `created_at`
- `updated_at`

### `poll_jobs`

- `id`
- `shop_id`
- `job_type`
- `status`
- `retry_count`
- `max_retry`
- `next_run_at`
- `locked_at`
- `locked_by`
- `last_error`
- `created_at`
- `updated_at`

### `order_state`

- `id`
- `shop_id`
- `posting_number`
- `raw_payload JSONB`
- `last_status`
- `last_notified_status`
- `updated_at`

Rang buoc:

- `UNIQUE(shop_id, posting_number)`

### `return_state`

- `id`
- `shop_id`
- `return_number`
- `raw_payload JSONB`
- `last_status`
- `last_notified_status`
- `updated_at`

Rang buoc:

- `UNIQUE(shop_id, return_number)`

### `notification_log`

- `id`
- `shop_id`
- `channel_type`
- `event_type`
- `entity_key`
- `idempotency_key`
- `payload JSONB`
- `sent_at`

Rang buoc:

- `UNIQUE(idempotency_key)`

### `command_log`

- `id`
- `shop_id` nullable
- `source`
- `command_text`
- `command_type`
- `status`
- `response_summary`
- `created_at`

## Workflow phia nguoi dung

Co 2 kieu su dung chinh.

### A. He thong tu gui thong bao

Nguoi dung thay:

1. shop co thay doi tren Ozon
2. bot tu gui tin vao Lark hoac Telegram
3. nguoi dung nhan thong bao da duoc loc trung lap

Nguoi dung khong can thao tac gi.

### B. Nguoi dung chu dong goi lenh

Vi du:

- `/status`
- `/refund`
- `/cancel`
- `/order_now`

Luot chay:

1. user gui lenh
2. command server nhan lenh
3. command router phan loai
4. neu la lenh thuong thi doc DB
5. neu la lenh realtime thi goi Ozon API truc tiep
6. tra ket qua cho user
7. ghi `command_log`

## Workflow phia he thong

### Vai tro cac thanh phan

#### `Scheduler`

Chi co nhiem vu:

- xem shop nao den lich
- tao `poll_job`

Khong truc tiep goi Ozon API.

#### `Worker`

Chi co nhiem vu:

- claim job
- load shop + credential + channel
- goi Ozon API
- so sanh state
- gui thong bao neu can
- cap nhat DB

#### `Command Server`

Chi co nhiem vu:

- nhan lenh tu Lark/Telegram
- doc DB de tra loi
- hoac goi Ozon realtime neu lenh can

### 1 vong poll cua 1 shop

1. scheduler thay shop den gio chay
2. scheduler kiem tra chua co job cung `job_type` dang `queued/running`
3. scheduler tao `poll_job`
4. worker claim job bang `FOR UPDATE SKIP LOCKED`
5. worker set job thanh `running`, gan `locked_at`, `locked_by`
6. worker load `shop`, `shop_credentials`, `shop_channels`
7. worker goi Ozon API voi rate limit + retry + backoff
8. worker xu ly orders
9. worker xu ly returns/cancellations
10. worker so sanh state cu va moi
11. worker tao `idempotency_key`
12. neu chua gui thi gui thong bao
13. neu gui thanh cong thi ghi `notification_log` va cap nhat state
14. ket thuc:
- `done` neu thanh cong
- `retry` neu loi tam thoi
- `failed` neu vuot `max_retry`

## Dau vao / dau ra

### `Scheduler`

Dau vao:

- `shops`
- `poll_jobs`
- current time

Dau ra:

- tao them record trong `poll_jobs`

### `Worker`

Dau vao:

- `poll_jobs`
- `shops`
- `shop_credentials`
- `shop_channels`
- Ozon API
- `order_state`
- `return_state`
- `notification_log`

Dau ra:

- state moi cua order/return
- thong bao gui ra channel
- log thong bao
- cap nhat trang thai job

### `Command Server`

Dau vao:

- user command
- du lieu DB
- Ozon API cho lenh realtime

Dau ra:

- message tra ve user
- `command_log`

## Quy tac MVP

- uu tien chay on `1-3 shop`
- command uu tien doc DB
- moi shop/job_type chi co 1 job `queued/running`
- worker claim job an toan
- notification phai idempotent
- orders va returns deu can state rieng
- chua mo rong dashboard hay chat realtime som

## Buoc tiep theo de implement

1. tao schema PostgreSQL MVP
2. viet repository cho `shops`, `poll_jobs`, `order_state`, `return_state`, `notification_log`, `command_log`
3. viet scheduler tao job co chong trung
4. viet worker claim job an toan
5. refactor `ozon_client` them rate limit + backoff
6. chuyen command server sang doc DB la mac dinh
7. chay thu voi `1 shop`
8. mo rong `2-3 shop`

