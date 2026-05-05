import html as html_lib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse
from uuid import uuid4

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

ZYTE_API_KEY = os.getenv("ZYTE_API_KEY")
ZYTE_USE_PROXY_MODE = os.getenv("ZYTE_USE_PROXY_MODE", "").strip().lower() in {"1", "true", "yes"}
ZYTE_PROXY_VERIFY = os.getenv("ZYTE_PROXY_VERIFY", "").strip().lower() in {"1", "true", "yes"}

PRODUCT_URL = (
    "https://www.shein.com.vn/Protect-Marine-Life-Shark-Print-Autumn-Clothes-Women-"
    "Back-To-School-Loose-Fit-Drop-Shoulder-Casual-Hoodie-Sweatshirt-p-115201665.html"
    "?src_identifier=st%3D5%60sc%3Dhoodie%60sr%3D0%60ps%3D1"
    "&src_module=search&src_tab_page_id=page_home1777520322097"
    "&mallCode=1&pageListType=4&imgRatio=3-4"
    "&detailBusinessFrom=0-1_115201665%7C0-2&pageListType=4"
)

VALID_SIZES = {
    "XXS", "XS", "S", "M", "L", "XL", "XXL",
    "0XL", "1XL", "2XL", "3XL", "4XL", "5XL",
    "ONE SIZE", "ONESIZE",
}


def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    text = html_lib.unescape(str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def to_float(value: Any) -> float | None:
    if value is None:
        return None

    text = str(value).strip()
    text = text.replace("₫", "").replace("VND", "").replace("Giá", "").strip()

    # 216.500 => 216500 nếu là format VNĐ
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", text):
        text = text.replace(".", "")

    text = text.replace(",", "")

    try:
        return float(text)
    except ValueError:
        return None


def normalize_url(url: str | None) -> str | None:
    if not url:
        return None

    url = url.strip()

    if url.startswith("//"):
        url = "https:" + url

    return url.split("?")[0]


def unique_keep_order(items: list[Any]) -> list[Any]:
    result = []
    seen = set()

    for item in items:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, dict) else str(item)

        if key not in seen:
            seen.add(key)
            result.append(item)

    return result


def extract_requested_url(url: str | None) -> str | None:
    if not url:
        return None

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    redirected = query.get("redirection")
    if redirected:
        return clean_text(unquote(redirected[0]))

    return clean_text(url)


def is_shein_challenge_response(zyte_data: dict) -> bool:
    url = (zyte_data.get("url") or "").lower()
    html = zyte_data.get("browserHtml") or ""

    return (
        "risk/challenge" in url
        or "page_risk_crawler_block" in html
        or "captcha_type=" in url
        or "GB_RISK_CHALLEGE_LANG" in html
    )


def fetch_zyte_product(url: str) -> dict:
    if not ZYTE_API_KEY:
        raise RuntimeError(
            "Không tìm thấy ZYTE_API_KEY. Hãy kiểm tra file .env có nằm cùng thư mục với file Python không."
        )

    response = requests.post(
        "https://api.zyte.com/v1/extract",
        auth=(ZYTE_API_KEY, ""),
        json={
            "url": url,
            "browserHtml": True,
            "product": True,
        },
        timeout=120,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"Zyte API lỗi {response.status_code}: {response.text[:1000]}"
        )

    return response.json()


def extract_price_from_html(soup: BeautifulSoup) -> dict:
    price_el = soup.select_one("#productMainPriceId, .productPrice__main, [class*=productPrice__main]")

    if not price_el:
        return {
            "price": None,
            "price_text": None,
            "currency": None,
            "currency_raw": None,
        }

    raw = price_el.get("aria-label") or price_el.get_text(" ", strip=True)
    raw = clean_text(raw)

    if not raw:
        return {
            "price": None,
            "price_text": None,
            "currency": None,
            "currency_raw": None,
        }

    raw = raw.replace("Giá", "").strip()

    return {
        "price": to_float(raw),
        "price_text": raw,
        "currency": "VND" if "₫" in raw else None,
        "currency_raw": "₫" if "₫" in raw else None,
    }


def extract_sizes_from_html(soup: BeautifulSoup) -> list[str]:
    """
    Chỉ lấy size thật, tránh quét toàn trang quá rộng.
    """
    size_blocks = soup.select(
        "[class*=product-intro] [class*=size], "
        "[class*=product-intro] [aria-label*=Size], "
        "[class*=product-intro] [aria-label*=Kích]"
    )

    sizes = []

    for block in size_blocks:
        for el in block.select("button, span, li, div"):
            text = clean_text(el.get("aria-label") or el.get_text(" ", strip=True))
            if not text:
                continue

            if len(text) > 12:
                continue

            lower = text.lower()
            bad_words = [
                "size guide",
                "kích thước",
                "hướng dẫn",
                "cm",
                "inch",
                "ngực",
                "vai",
                "dài",
            ]

            if any(word in lower for word in bad_words):
                continue

            normalized = text.upper().replace(" ", "")

            for size in VALID_SIZES:
                if normalized == size.upper().replace(" ", ""):
                    sizes.append(size)

    return unique_keep_order(sizes)


def extract_meta_content(html: str, property_name: str) -> str | None:
    pattern = rf'<meta[^>]+property="{re.escape(property_name)}"[^>]+content="([^"]+)"'
    match = re.search(pattern, html, flags=re.I)
    if match:
        return clean_text(match.group(1))

    return None


def extract_name_from_html(html: str) -> str | None:
    title = extract_meta_content(html, "og:title")
    if not title:
        match = re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S)
        title = clean_text(match.group(1)) if match else None

    if not title:
        return None

    return clean_text(title.replace("| SHEIN", ""))


def extract_images_from_html(html: str) -> list[str]:
    images = []

    og_image = extract_meta_content(html, "og:image")
    if og_image:
        images.append(normalize_url(og_image))

    pattern = re.compile(
        r'https?:\\?/\\?/img\.ltwebstatic\.com[^"\']+?\.(?:jpg|jpeg|png|webp)',
        flags=re.I,
    )
    for match in pattern.findall(html):
        images.append(normalize_url(match.replace("\\/", "/")))

    return [x for x in unique_keep_order(images) if x]


def extract_sizes_from_embedded_data(html: str) -> list[str]:
    sizes = []

    base_sort = re.search(r'"base_size_sort"\s*:\s*\{([^{}]{1,500})\}', html, flags=re.S)
    if base_sort:
        for size in re.findall(r'"([A-Z0-9 ]{1,10})"\s*:\s*\d+', base_sort.group(1)):
            normalized = size.upper().replace(" ", "")
            if any(normalized == valid.upper().replace(" ", "") for valid in VALID_SIZES):
                sizes.append(size.strip())

    for size in re.findall(r'-\s*(?:K[^"]{0,20}?)\s+([A-Z0-9 ]{1,10})"', html, flags=re.I):
        normalized = size.upper().replace(" ", "")
        if any(normalized == valid.upper().replace(" ", "") for valid in VALID_SIZES):
            sizes.append(size.strip())

    return unique_keep_order(sizes)


def extract_color_from_embedded_data(html: str) -> str | None:
    match = re.search(
        r'"attr_name_en":"Color".{0,250}?"attr_value":"([^"]+)"',
        html,
        flags=re.I | re.S,
    )
    if match:
        return clean_text(match.group(1))

    return None


def extract_material_from_embedded_data(html: str) -> dict:
    material = None
    composition = None

    block_match = re.search(
        r'"materialExposed"\s*:\s*\{.*?"materialInfoList"\s*:\s*\[(.*?)\]\s*\}',
        html,
        flags=re.I | re.S,
    )
    if not block_match:
        return {"material": None, "composition": None}

    pairs = re.findall(
        r'"attrName":"([^"]+)","attrValue":"([^"]*)"',
        block_match.group(1),
        flags=re.S,
    )
    for key, value in pairs:
        key_clean = (clean_text(key) or "").lower()
        value_clean = clean_text(value)
        if not value_clean:
            continue

        if "%" in value_clean and not composition:
            composition = value_clean
            continue

        if ("composition" in key_clean or "thành phần" in key_clean) and not composition:
            composition = value_clean
            continue

        if not material:
            material = value_clean

    return {
        "material": material,
        "composition": composition,
    }


def extract_sku_options_from_html(html: str) -> list[dict[str, Any]]:
    size_names = extract_sizes_from_embedded_data(html)
    sku_matches = list(
        re.finditer(
            r'"sku_code":"([^"]+)","stock":"([^"]*)".{0,1200}?"salePrice":\{"amount":"[^"]*","amountWithSymbol":"([^"]+)"',
            html,
            flags=re.I | re.S,
        )
    )
    if not sku_matches:
        return []

    options = []
    for index, match in enumerate(sku_matches):
        size_name = size_names[index] if index < len(size_names) else None
        options.append(
            {
                "sku_code": clean_text(match.group(1)),
                "size": size_name,
                "stock": clean_text(match.group(2)),
                "price_text": clean_text(match.group(3)),
                "price": to_float(match.group(3)),
            }
        )

    return options


def extract_color_from_html(soup: BeautifulSoup) -> str | None:
    color_blocks = soup.select(
        "[class*=product-intro] [class*=color], "
        "[class*=product-intro] [aria-label*=Color], "
        "[class*=product-intro] [aria-label*=Màu]"
    )

    for block in color_blocks:
        text = clean_text(block.get("aria-label") or block.get_text(" ", strip=True))
        if not text:
            continue

        patterns = [
            r"Màu sắc\s*[:：]\s*([A-Za-zÀ-ỹ0-9\s-]+)",
            r"Màu\s*[:：]\s*([A-Za-zÀ-ỹ0-9\s-]+)",
            r"Color\s*[:：]\s*([A-Za-zÀ-ỹ0-9\s-]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.I)
            if match:
                color = clean_text(match.group(1))
                if color and len(color) <= 40:
                    return color

    return None


def extract_material_from_html(soup: BeautifulSoup) -> dict:
    product_area = soup.select_one("[class*=product-intro]") or soup

    text = clean_text(product_area.get_text(" ", strip=True)) or ""

    material = None
    composition = None
    care = None

    material_match = re.search(
        r"Chất liệu\s*[:：]?\s*([^:：]{2,80}?)(?:Thành phần|Hướng dẫn|Bảo quản|Chi tiết|$)",
        text,
        flags=re.I,
    )

    if material_match:
        material = clean_text(material_match.group(1))

    composition_match = re.search(
        r"Thành phần\s*[:：]?\s*([^:：]{2,100}?)(?:Chất liệu|Hướng dẫn|Bảo quản|Chi tiết|$)",
        text,
        flags=re.I,
    )

    if composition_match:
        composition = clean_text(composition_match.group(1))

    if not composition:
        comp_match = re.search(
            r"\b\d{1,3}%\s*(?:Polyester|Cotton|Elastane|Spandex|Nylon|Viscose|Acrylic)\b",
            text,
            flags=re.I,
        )

        if comp_match:
            composition = clean_text(comp_match.group(0))

    care_match = re.search(
        r"(?:Hướng dẫn chăm sóc|Bảo quản|Care Instructions)\s*[:：]?\s*([^:：]{4,120}?)(?:Chất liệu|Thành phần|Chi tiết|$)",
        text,
        flags=re.I,
    )

    if care_match:
        care = clean_text(care_match.group(1))

    return {
        "material": material,
        "composition": composition,
        "care": care,
    }


def collect_images(product: dict) -> list[str]:
    images = []

    main_image = product.get("mainImage")
    if isinstance(main_image, dict):
        url = normalize_url(main_image.get("url"))
        if url:
            images.append(url)

    for img in product.get("images") or []:
        if isinstance(img, dict):
            url = normalize_url(img.get("url"))
        else:
            url = normalize_url(str(img))

        if url:
            # đổi thumbnail nhỏ thành ảnh lớn hơn nếu có thể
            url = url.replace("_thumbnail_220x293", "_thumbnail_900x")
            images.append(url)

    return unique_keep_order(images)


def parse_variants(product: dict) -> dict:
    raw_variants = product.get("variants") or []

    colors = []
    sizes = []

    for item in raw_variants:
        if not isinstance(item, dict):
            continue

        color = clean_text(item.get("color"))
        size = clean_text(item.get("size"))

        if color:
            colors.append(color)

        if size:
            sizes.append(size)

    return {
        "colors": unique_keep_order(colors),
        "sizes": unique_keep_order(sizes),
        "variants_raw": raw_variants,
    }


def extract_embedded_product_data(html: str) -> dict:
    material_data = extract_material_from_embedded_data(html)

    return {
        "name": extract_name_from_html(html),
        "images": extract_images_from_html(html),
        "sizes": extract_sizes_from_embedded_data(html),
        "color": extract_color_from_embedded_data(html),
        "material": material_data["material"],
        "composition": material_data["composition"],
        "sku_options": extract_sku_options_from_html(html),
    }


def get_breadcrumbs(product: dict) -> list[str]:
    breadcrumbs = []

    for item in product.get("breadcrumbs") or []:
        if isinstance(item, dict) and item.get("name"):
            breadcrumbs.append(clean_text(item["name"]))

    return [x for x in breadcrumbs if x]


def get_brand_name(product: dict) -> str | None:
    brand = product.get("brand")

    if isinstance(brand, dict):
        return clean_text(brand.get("name"))

    return clean_text(brand)


def build_clean_description(clean_product: dict) -> str:
    parts = []

    if clean_product.get("name"):
        parts.append(clean_product["name"])

    if clean_product.get("brand"):
        parts.append(f"Thương hiệu: {clean_product['brand']}")

    if clean_product.get("color"):
        parts.append(f"Màu sắc: {clean_product['color']}")

    if clean_product.get("sizes"):
        parts.append(f"Kích thước: {', '.join(clean_product['sizes'])}")

    if clean_product.get("material"):
        parts.append(f"Chất liệu: {clean_product['material']}")

    if clean_product.get("composition"):
        parts.append(f"Thành phần: {clean_product['composition']}")

    if clean_product.get("care"):
        parts.append(f"Hướng dẫn chăm sóc: {clean_product['care']}")

    return "\n".join(parts)


def normalize_product(zyte_data: dict, url: str) -> dict:
    if is_shein_challenge_response(zyte_data):
        blocked_url = zyte_data.get("url") or url
        requested_url = extract_requested_url(blocked_url) or url
        return {
            "source": "shein",
            "status": "blocked",
            "blocked_reason": "shein_risk_challenge",
            "requested_url": requested_url,
            "blocked_url": blocked_url,
            "sku": clean_text((zyte_data.get("product") or {}).get("sku")),
            "message": "Zyte bị SHEIN chuyển sang trang challenge/captcha, nên không có HTML sản phẩm thật để parse.",
        }

    product = zyte_data.get("product") or {}
    html = zyte_data.get("browserHtml") or ""
    soup = BeautifulSoup(html, "html.parser") if html else BeautifulSoup("", "html.parser")

    html_price = extract_price_from_html(soup)
    html_material = extract_material_from_html(soup)
    html_sizes = extract_sizes_from_html(soup)
    html_color = extract_color_from_html(soup)
    html_embedded = extract_embedded_product_data(html) if html else {}

    variants = parse_variants(product)

    rating = product.get("aggregateRating") or {}
    breadcrumbs = get_breadcrumbs(product)

    price = to_float(product.get("price")) or html_price["price"]

    clean_product = {
        "source": "shein",
        "name": clean_text(product.get("name")) or html_embedded.get("name"),
        "sku": clean_text(product.get("sku")) or clean_text((html_embedded.get("sku_options") or [{}])[0].get("sku_code")),
        "brand": get_brand_name(product),

        "price": price,
        "price_text": html_price["price_text"],
        "currency": product.get("currency") or html_price["currency"],
        "currency_raw": product.get("currencyRaw") or html_price["currency_raw"],
        "availability": product.get("availability"),

        "category_path": breadcrumbs,
        "category": breadcrumbs[-2] if len(breadcrumbs) >= 2 else None,

        "color": clean_text(product.get("color")) or html_color or html_embedded.get("color"),
        "colors": variants["colors"],
        "sizes": variants["sizes"] or html_sizes or html_embedded.get("sizes", []),

        "material": clean_text(product.get("material")) or html_material["material"] or html_embedded.get("material"),
        "composition": get_additional_property(product, "composition") or html_material["composition"] or html_embedded.get("composition"),
        "care": html_material["care"],

        "rating": rating.get("ratingValue"),
        "review_count": rating.get("reviewCount"),

        "main_image": (
            normalize_url(product.get("mainImage", {}).get("url"))
            if isinstance(product.get("mainImage"), dict)
            else (html_embedded.get("images") or [None])[0]
        ),
        "images": collect_images(product) or html_embedded.get("images", []),

        "url": product.get("url") or url,
        "canonical_url": product.get("canonicalUrl"),

        "variants_raw": variants["variants_raw"],
        "sku_options": html_embedded.get("sku_options", []),
    }

    clean_product["description_clean"] = build_clean_description(clean_product)

    return clean_product


def get_additional_property(product: dict, property_name: str) -> str | None:
    for item in product.get("additionalProperties") or []:
        if not isinstance(item, dict):
            continue

        name = clean_text(item.get("name"))
        value = clean_text(item.get("value"))

        if name and value and name.lower() == property_name.lower():
            return value

    return None


def save_json(filename: str, data: Any) -> None:
    path = BASE_DIR / filename

    with open(path, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)

    print(f"Saved: {path}")


def save_html(filename: str, html: str) -> None:
    path = BASE_DIR / filename

    with open(path, "w", encoding="utf-8") as fp:
        fp.write(html)

    print(f"Saved: {path}")


def build_session_id() -> str:
    return str(uuid4())


def build_referer(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return "https://www.shein.com.vn/"
    return f"{parsed.scheme}://{parsed.netloc}/"


def post_zyte_extract(payload: dict) -> dict:
    if not ZYTE_API_KEY:
        raise RuntimeError(
            "KhÃ´ng tÃ¬m tháº¥y ZYTE_API_KEY. HÃ£y kiá»ƒm tra file .env cÃ³ náº±m cÃ¹ng thÆ° má»¥c vá»›i file Python khÃ´ng."
        )

    response = requests.post(
        "https://api.zyte.com/v1/extract",
        auth=(ZYTE_API_KEY, ""),
        json=payload,
        timeout=120,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"Zyte API lá»—i {response.status_code}: {response.text[:1000]}"
        )

    return response.json()


def summarize_zyte_response(zyte_data: dict) -> dict:
    return {
        "url": zyte_data.get("url"),
        "statusCode": zyte_data.get("statusCode"),
        "challenge_detected": is_shein_challenge_response(zyte_data),
        "responseCookies_count": len(zyte_data.get("responseCookies") or []),
        "product_probability": ((zyte_data.get("product") or {}).get("metadata") or {}).get("probability"),
    }


def warm_up_shein_session(url: str, session_id: str) -> dict:
    return post_zyte_extract(
        {
            "url": url,
            "browserHtml": True,
            "responseCookies": True,
            "session": {"id": session_id},
            "requestHeaders": {
                "referer": build_referer(url),
            },
        }
    )


def fetch_zyte_product_via_proxy(url: str) -> dict:
    if not ZYTE_API_KEY:
        raise RuntimeError(
            "KhÃ´ng tÃ¬m tháº¥y ZYTE_API_KEY. HÃ£y kiá»ƒm tra file .env cÃ³ náº±m cÃ¹ng thÆ° má»¥c vá»›i file Python khÃ´ng."
        )

    session_id = build_session_id()
    proxy_url = f"http://{ZYTE_API_KEY}:@api.zyte.com:8011/"
    headers = {
        "Zyte-Browser-Html": "true",
        "Zyte-Session-ID": session_id,
    }

    response = requests.get(
        url,
        headers=headers,
        proxies={
            "http": proxy_url,
            "https": proxy_url,
        },
        verify=ZYTE_PROXY_VERIFY,
        timeout=120,
    )

    return {
        "url": response.url,
        "statusCode": response.status_code,
        "browserHtml": response.text,
        "_debug": {
            "mode": "proxy",
            "session_id": session_id,
            "verify_tls": ZYTE_PROXY_VERIFY,
            "content_type": response.headers.get("Content-Type"),
            "challenge_detected": is_shein_challenge_response(
                {
                    "url": response.url,
                    "browserHtml": response.text,
                }
            ),
        },
    }


def fetch_zyte_product(url: str) -> dict:
    session_id = build_session_id()
    warmup = warm_up_shein_session(url, session_id)
    warmup_cookies = warmup.get("responseCookies") or []

    product_payload = {
        "url": url,
        "browserHtml": True,
        "product": True,
        "responseCookies": True,
        "session": {"id": session_id},
        "requestHeaders": {
            "referer": build_referer(url),
        },
    }
    if warmup_cookies:
        product_payload["requestCookies"] = warmup_cookies

    product_response = post_zyte_extract(product_payload)
    product_response["_debug"] = {
        "mode": "extract",
        "session_id": session_id,
        "warmup": summarize_zyte_response(warmup),
        "product_request": summarize_zyte_response(product_response),
        "used_warmup_cookies": bool(warmup_cookies),
    }
    return product_response


def fetch_product_with_configured_mode(url: str) -> dict:
    if ZYTE_USE_PROXY_MODE:
        return fetch_zyte_product_via_proxy(url)
    return fetch_zyte_product(url)


def resolve_target_urls() -> list[str]:
    cli_urls = [arg.strip() for arg in sys.argv[1:] if arg.strip()]
    if cli_urls:
        return cli_urls

    env_value = os.getenv("TEST_PRODUCT_URLS", "").strip()
    if env_value:
        raw_urls = re.split(r"[\r\n,]+", env_value)
        env_urls = [item.strip() for item in raw_urls if item.strip()]
        if env_urls:
            return env_urls

    prompt = (
        "Nhập 1 hoặc nhiều URL SHEIN"
        " (ngăn cách bằng dấu phẩy hoặc xuống dòng), rồi nhấn Enter: "
    )
    user_value = input(prompt).strip()
    if user_value:
        raw_urls = re.split(r"[\r\n,]+", user_value)
        user_urls = [item.strip() for item in raw_urls if item.strip()]
        if user_urls:
            return user_urls

    return [PRODUCT_URL]


def filename_suffix(index: int, total: int) -> str:
    if total <= 1:
        return ""
    return f"_{index}"


def legacy_main() -> None:
    target_urls = resolve_target_urls()
    for index, target_url in enumerate(target_urls, start=1):
        suffix = filename_suffix(index, len(target_urls))
        zyte_data = fetch_product_with_configured_mode(target_url)

        save_json(f"zyte_raw_response{suffix}.json", zyte_data)

        html = zyte_data.get("browserHtml")
        if html:
            save_html(f"browser_html{suffix}.html", html)

        product_clean = normalize_product(zyte_data, target_url)

        save_json(f"product_clean{suffix}.json", product_clean)

    if product_clean.get("status") == "blocked":
        print("\n=== BLOCKED ===")
        print(json.dumps(product_clean, ensure_ascii=False, indent=2))
        raise RuntimeError(
            "Zyte chỉ lấy được trang risk/challenge của SHEIN, không phải trang sản phẩm thật."
        )

    print("\n=== PRODUCT CLEAN ===")
    print(json.dumps(product_clean, ensure_ascii=False, indent=2))


def main() -> None:
    target_urls = resolve_target_urls()

    for index, target_url in enumerate(target_urls, start=1):
        suffix = filename_suffix(index, len(target_urls))
        zyte_data = fetch_product_with_configured_mode(target_url)

        save_json(f"zyte_raw_response{suffix}.json", zyte_data)

        html = zyte_data.get("browserHtml")
        if html:
            save_html(f"browser_html{suffix}.html", html)

        product_clean = normalize_product(zyte_data, target_url)
        save_json(f"product_clean{suffix}.json", product_clean)

        if product_clean.get("status") == "blocked":
            print("\n=== BLOCKED ===")
            print(json.dumps(product_clean, ensure_ascii=False, indent=2))
            raise RuntimeError(
                "Zyte chá»‰ láº¥y Ä‘Æ°á»£c trang risk/challenge cá»§a SHEIN, khÃ´ng pháº£i trang sáº£n pháº©m tháº­t."
            )

        print("\n=== PRODUCT CLEAN ===")
        print(json.dumps(product_clean, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
