import requests
from bs4 import BeautifulSoup
import re
import json

url = "https://seller.ozon.ru/app/returns/rfbs?status=90"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Cookie": "DÁN_COOKIE_CỦA_BẠN_VÀO_ĐÂY"
}

html = requests.get(url, headers=headers).text

# tìm dữ liệu returns trong html
match = re.search(r'"returns"\s*:\s*(\[.*?\])\s*,\s*"total"', html, re.S)

if match:
    returns = json.loads(match.group(1))
    for item in returns:
        print(item["returnNumber"], item["postingNumber"], item["status"]["name"])
else:
    print("Không tìm thấy returns")