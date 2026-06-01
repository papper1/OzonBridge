# Manual Ozon API Calls

File nay dung de test thu cong tung Ozon API call truoc khi doi chieu voi du lieu trong bot.

## Bien moi truong mau

```bash
export OZON_CLIENT_ID="your_client_id"
export OZON_API_KEY="your_api_key"
export OZON_BASE_URL="https://api-seller.ozon.ru"
export POSTING_NUMBER="1234567890-0001"
export RETURN_ID="123456"
```

Windows PowerShell:

```powershell
$env:OZON_CLIENT_ID="your_client_id"
$env:OZON_API_KEY="your_api_key"
$env:OZON_BASE_URL="https://api-seller.ozon.ru"
$env:POSTING_NUMBER="1234567890-0001"
$env:RETURN_ID="123456"
```

## Header chung

```text
Client-Id: $OZON_CLIENT_ID
Api-Key: $OZON_API_KEY
Content-Type: application/json
```

## 1. FBS postings list (order - danh sach don hang FBS)

```bash
curl -X POST "$OZON_BASE_URL/v3/posting/fbs/list" \
  -H "Client-Id: $OZON_CLIENT_ID" \
  -H "Api-Key: $OZON_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "dir":"ASC",
    "filter":{
      "since":"2026-05-01T00:00:00Z",
      "to":"2026-05-17T23:59:59Z"
    },
    "limit":100,
    "offset":0,
    "with":{"financial_data":true}
  }'
```

## 2. Unfulfilled postings (order - don chua hoan tat, thuong dung de xem cho dong goi)

```bash
curl -X POST "$OZON_BASE_URL/v3/posting/fbs/unfulfilled/list" \
  -H "Client-Id: $OZON_CLIENT_ID" \
  -H "Api-Key: $OZON_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "dir":"ASC",
    "filter":{
      "cutoff_from":"2026-05-01T00:00:00Z",
      "cutoff_to":"2026-05-17T23:59:59Z"
    },
    "limit":100,
    "offset":0,
    "with":{"financial_data":true}
  }'
```

## 3. Order detail (order - chi tiet 1 don cu the)

```bash
curl -X POST "$OZON_BASE_URL/v3/posting/fbs/get" \
  -H "Client-Id: $OZON_CLIENT_ID" \
  -H "Api-Key: $OZON_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"posting_number\":\"$POSTING_NUMBER\"}"
```

## 4. Cancel reason (order cancellation - ly do huy don)

```bash
curl -X POST "$OZON_BASE_URL/v2/posting/fbs/cancel-reason/list" \
  -H "Client-Id: $OZON_CLIENT_ID" \
  -H "Api-Key: $OZON_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"posting_number\":\"$POSTING_NUMBER\"}"
```

```bash
curl -X POST "$OZON_BASE_URL/v1/posting/fbs/cancel-reason" \
  -H "Client-Id: $OZON_CLIENT_ID" \
  -H "Api-Key: $OZON_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"related_posting_numbers\":[\"$POSTING_NUMBER\"]}"
```

## 5. FBS returns (return/refund - danh sach yeu cau tra hang hoan tien FBS)

```bash
curl -X POST "$OZON_BASE_URL/v1/returns/list" \
  -H "Client-Id: $OZON_CLIENT_ID" \
  -H "Api-Key: $OZON_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "filter":{"return_schema":"FBS"},
    "limit":100
  }'
```

## 6. RFBS returns list (return/cancellation - danh sach return hoac cancellation RFBS)

```bash
curl -X POST "$OZON_BASE_URL/v2/returns/rfbs/list" \
  -H "Client-Id: $OZON_CLIENT_ID" \
  -H "Api-Key: $OZON_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "filter":{},
    "limit":100,
    "last_id":0
  }'
```

## 7. RFBS return detail (return/cancellation - chi tiet 1 yeu cau RFBS)

```bash
curl -X POST "$OZON_BASE_URL/v2/returns/rfbs/get" \
  -H "Client-Id: $OZON_CLIENT_ID" \
  -H "Api-Key: $OZON_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"return_id\":$RETURN_ID}"
```

## Cach doi chieu ket qua theo hanh dong thuc te

- `order`: doi chieu voi `v3/posting/fbs/list`
- `order awaiting_packaging`: doi chieu voi `v3/posting/fbs/unfulfilled/list`
- `order detail`: doi chieu voi `v3/posting/fbs/get`
- `order cancellation`: doi chieu them voi `v2/posting/fbs/cancel-reason/list` hoac `v1/posting/fbs/cancel-reason`
- `return/refund FBS`: doi chieu voi `v1/returns/list`
- `return/cancellation RFBS`: doi chieu voi `v2/returns/rfbs/list`
- `return/cancellation RFBS detail`: doi chieu voi `v2/returns/rfbs/get`

## Bang map nhanh ten API va nghiep vu

- `FBS postings list (order)`: lay danh sach don hang FBS trong khoang thoi gian
- `FBS unfulfilled list (order awaiting_packaging / awaiting_delivery)`: lay don chua hoan tat de theo doi don can xu ly
- `FBS get (order detail)`: lay chi tiet day du cua 1 don
- `FBS cancel reason (order cancellation)`: lay ly do huy don khi trang thai da chuyen sang huy
- `FBS returns list (return/refund)`: lay danh sach yeu cau tra hang, hoan tien thuoc FBS
- `RFBS returns list (return/cancellation)`: lay danh sach return va cancellation thuoc RFBS
- `RFBS return detail (return/cancellation detail)`: lay chi tiet 1 yeu cau RFBS de phan loai dung nghiep vu

## Ghi chu

- test thu cong nen luu response JSON goc de so sanh voi `order_state.raw_payload` va `return_state.raw_payload`
- khi Ozon rate limit, giam tan suat test thu cong va doi lai sau
