import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.zyte_source_service import crawl_source_product


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python test_shein.py <shein_product_url>")
        raise SystemExit(1)

    product = crawl_source_product(sys.argv[1].strip(), "shein")
    print(f"title: {product.get('title', '')}")
    print(f"price: {product.get('price', '')}")
    print(f"images: {len(product.get('images', []) or [])}")


if __name__ == "__main__":
    main()
