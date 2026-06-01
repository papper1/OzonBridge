# Ozon Multi-Shop Bot

Refactor nay chuyen bot tu `single-shop + SQLite + 1 process` sang `multi-shop MVP + PostgreSQL + scheduler/worker/command_server` de de scale va de deploy len VPS.

## Muc tieu ky thuat

- PostgreSQL thay cho SQLite
- `scheduler` chi tao job, khong goi Ozon API
- `worker` claim job an toan bang `FOR UPDATE SKIP LOCKED`
- command mac dinh doc DB
- notification idempotent qua `notification_log.idempotency_key`
- dependency gon: `requests + psycopg + python-dotenv + stdlib`

## Cau truc

```text
app/
  settings.py
  bootstrap.py
core/
db/
  schema.py
  repositories/
integrations/
services/
formatters/
scripts/
tests/
```

## Cai dat

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Cap nhat `.env`, dac biet:

- `DATABASE_URL`
- `SEED_OZON_CLIENT_ID`
- `SEED_OZON_API_KEY`
- `SEED_LARK_WEBHOOK_URL` hoac `SEED_TELEGRAM_*`

## Khoi tao DB va seed shop dau tien

```powershell
python -m scripts.seed_shop
```

Script nay se:

- tao schema PostgreSQL neu chua co
- tao/cap nhat `shops`
- tao/cap nhat `shop_credentials`
- tao/cap nhat `shop_channels`

## Chay local

Mo PowerShell trong thu muc project va kich hoat virtualenv:

```powershell
.\.venv312\Scripts\Activate.ps1
```

Chay tat ca trong 1 process (`scheduler + worker + command server`):

```powershell
.\.venv312\Scripts\python.exe .\main.py
```

Neu muon chay tach process, mo 3 cua so PowerShell rieng:

```powershell
.\.venv312\Scripts\python.exe -m scripts.run_scheduler
```

```powershell
.\.venv312\Scripts\python.exe -m scripts.run_worker
```

```powershell
.\.venv312\Scripts\python.exe -m scripts.run_command_server
```

## Chay Cloudflare tunnel

Mac dinh command server HTTP lang nghe tai `0.0.0.0:8080` theo `.env.example`:

```env
LARK_COMMAND_HOST=0.0.0.0
LARK_COMMAND_PORT=8080
```

Sau khi command server da chay, mo them 1 cua so PowerShell khac:

```powershell
cloudflared tunnel --url http://127.0.0.1:8080
```

Tunnel nay dung de public endpoint:

- `https://<random-subdomain>.trycloudflare.com/health`
- `https://<random-subdomain>.trycloudflare.com/lark/health`
- `https://<random-subdomain>.trycloudflare.com/lark/command`

Neu ban dang chay `.\.venv312\Scripts\python.exe .\main.py` thi khong can mo them `scripts.run_command_server`, vi HTTP command server da nam trong `main.py`.

## Command

- `/status <shop_code>`
- `/order <shop_code>`
- `/refund <shop_code>`
- `/cancel <shop_code>`
- `/order_now <shop_code>`
- `/help`

Neu he thong chi co 1 shop active, co the bo qua `shop_code`.

## Telegram va Lark

- Telegram command duoc poll truc tiep qua HTTP API, khong dung `python-telegram-bot`.
- Lark command server cung cap:
  - `GET /health`
  - `GET /lark/health`
  - `POST /lark/command`

Lark endpoint hien tai tra response JSON de de test va tich hop gateway. Telegram la kenh command hoan chinh hon cho ban MVP nay.

## Manual API test

File [MANUAL_API_CALLS.md](./MANUAL_API_CALLS.md) chua cac request Ozon API de test thu cong.

## Test thu thong bao cho 1 shop

Neu chi muon ban thu message vao dung channel cua 1 shop ma khong can doi Ozon tra event that:

```powershell
.\.venv312\Scripts\python.exe -m scripts.send_test_notification --shop-code sensia02 --event-type refund
```

Gia lap khach hoi:

```powershell
.\.venv312\Scripts\python.exe -m scripts.send_test_notification --shop-code sensia02 --event-type customer_question
```

Gui noi dung tuy chinh:

```powershell
.\.venv312\Scripts\python.exe -m scripts.send_test_notification --shop-code sensia02 --message "Khach hoi: shop oi con hang khong?"
```

Xem truoc noi dung, khong gui that va khong ghi DB:

```powershell
.\.venv312\Scripts\python.exe -m scripts.send_test_notification --shop-code sensia02 --event-type customer_question --dry-run
```

An toan nhat de khong anh huong VPS: gui thang vao webhook test rieng, khong doc `shop_channels`, khong ghi `notification_log`:

```powershell
.\.venv312\Scripts\python.exe -m scripts.send_test_notification --event-type customer_question --lark-webhook-url "https://open.larksuite.com/open-apis/bot/v2/hook/your-test-webhook"
```

## Ghi chu deploy VPS

- VPS IP: `103.153.254.116`
- SSH:

```powershell
ssh root@103.153.254.116
```

- Script deploy code tu local len VPS:

```powershell
.\scripts\deploy_to_vps.ps1
```

- Neu chi muon copy code ma khong test/restart:

```powershell
.\scripts\deploy_to_vps.ps1 -SkipTests -SkipRestart
```

- khong push thu muc `venv/`, `__pycache__/`, `logs/`
- dung PostgreSQL local hoac managed PostgreSQL
- dung 3 service rieng: scheduler, worker, command_server
