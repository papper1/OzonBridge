import unittest
from unittest.mock import Mock

from classifier.template_detector import detect_template
from crawler.product import extract_sku, extract_supplier, extract_title
from normalizer.build_variants import (
    build_product_variants,
    build_variants,
    extract_primary_memory_option,
    parse_memory_options,
    parse_size_options,
    select_primary_variant,
)
from normalizer.clean_text import clean_text, repair_mojibake
from normalizer.normalize_attributes import normalize_attributes
from normalizer.value_cleaner import clean_canonical_value


class TestNormalizer(unittest.TestCase):
    def test_extract_title_prefers_h1_product_title_over_global_supplier_name(self) -> None:
        page = Mock()
        page.evaluate.return_value = (
            "Áo len cardigan có mũ trùm đầu bằng cotton xuất sắc, kiểu dáng rộng rãi"
        )

        title = extract_title(page)

        self.assertEqual(
            title,
            "Áo len cardigan có mũ trùm đầu bằng cotton xuất sắc, kiểu dáng rộng rãi",
        )

    def test_clean_text(self) -> None:
        text = "  Lenovo   Laptop \n 16 gb   512 gb ssd \t 1,8kg  "
        cleaned = clean_text(text)

        self.assertEqual(cleaned, "Lenovo Laptop 16GB 512GB SSD 1.8 kg")

    def test_repair_mojibake_recovers_utf8_text(self) -> None:
        text = "Ão khoÃ¡c ná»‰ nam trÆ¡n mÃ u thá»i trang"

        self.assertEqual(repair_mojibake(text), "Áo khoác nỉ nam trơn màu thời trang")

    def test_clean_canonical_value_converts_size_and_screen_size_to_numbers(self) -> None:
        self.assertEqual(clean_canonical_value("size", "357,6*229,7*19,2mm"), "357.6 229.7 19.2")
        self.assertEqual(clean_canonical_value("screen_size", "15.6inch"), "15.6")

    def test_normalize_attributes_for_laptop(self) -> None:
        raw_product = {
            "title": "Lenovo ThinkBook laptop",
            "supplier": "Lenovo Official Store",
            "attributes": {
                "brand": "Lenovo",
                "model": "ThinkBook 14",
                "processor": "Intel Core i5-1240P",
                "cpu speed": "1.7GHz",
                "memory": "16GB",
                "storage": "512GB SSD",
                "screen size": "14 inch",
                "resolution": "1920 x 1080",
                "graphics card": "Intel Iris Xe",
                "wifi": "yes",
                "operating system": "Windows 11",
                "touchscreen": "no",
                "weight": "1,4kg",
                "warranty": "12 months",
                "promotion": "hot sale",
            },
        }

        normalized = normalize_attributes(raw_product)

        self.assertEqual(normalized["brand"], "Lenovo")
        self.assertEqual(normalized["model"], "ThinkBook 14")
        self.assertEqual(normalized["category"], "laptop")
        self.assertEqual(normalized["product_name"], "Lenovo ThinkBook laptop")
        self.assertEqual(normalized["supplier"], "Lenovo Official Store")
        self.assertEqual(normalized["cpu"], "Intel Core i5-1240P")
        self.assertEqual(normalized["specs"]["cpu"], "Intel Core i5-1240P")
        self.assertEqual(normalized["specs"]["ram"], "16GB")
        self.assertEqual(normalized["specs"]["storage"], "512GB SSD")
        self.assertEqual(normalized["specs"]["weight"], "1.4 kg")
        self.assertEqual(normalized["raw_attributes"]["promotion"], "hot sale")
        self.assertEqual(detect_template(normalized), "laptop")

    def test_build_variants_from_memory_string(self) -> None:
        memory_text = "16G + 128GB,16G + 256GB,8GB+512GB"
        parsed = parse_memory_options(memory_text)

        self.assertEqual(
            parsed,
            [
                {"ram": "16GB", "storage": "128GB"},
                {"ram": "16GB", "storage": "256GB"},
                {"ram": "8GB", "storage": "512GB"},
            ],
        )

        variants = build_variants(
            {
                "model": "ThinkBook 14",
                "raw_attributes": {
                    "memory_options": memory_text,
                    "color": "Grey, Silver",
                },
            },
            price="699",
        )

        self.assertEqual(len(variants), 6)
        self.assertEqual(variants[0]["price"], "699")
        self.assertIn("sku", variants[0])
        self.assertIn(variants[0]["color"], {"Grey", "Silver"})
        self.assertIn(variants[0]["color_name"], {"Grey", "Silver"})
        self.assertIn(variants[0]["ram"], {"16GB", "8GB"})
        self.assertIn(variants[0]["storage"], {"128GB", "256GB", "512GB"})

    def test_parse_memory_options_supports_compact_ram_storage_format(self) -> None:
        parsed = parse_memory_options("6+128GB,6+256GB,16G+0")

        self.assertEqual(
            parsed,
            [
                {"ram": "6GB", "storage": "128GB"},
                {"ram": "6GB", "storage": "256GB"},
                {"ram": "16GB", "storage": ""},
            ],
        )

    def test_build_variants_extracts_basic_color_and_color_name_from_sku_labels(self) -> None:
        variants = build_variants(
            {
                "model": "NX 15",
                "sku": {
                    "option_labels": [
                        "Haoyue Bạc 15.6inch R3-3200U",
                        "Xám không gian 15.6inch R3-3200U",
                    ]
                },
                "raw_attributes": {
                    "Dung lượng bộ nhớ": "8GB+256GB,16GB+512GB",
                    "màu sắc": "Dung lượng bộ nhớ",
                    "Haoyue Bạc 15.6inch R3-3200U": "8GB+256GB",
                    "Xám không gian 15.6inch R3-3200U": "16GB+512GB",
                },
            }
        )

        self.assertEqual({variant["color"] for variant in variants}, {"Silver", "Grey"})
        self.assertIn("Haoyue Silver 15.6 inch R3-3200U", {variant["color_name"] for variant in variants})
        self.assertIn("Space Grey 15.6 inch R3-3200U", {variant["color_name"] for variant in variants})

    def test_extract_primary_memory_option_from_1688_memory_text(self) -> None:
        memory_text = (
            "16G + 128GB,16G + 256GB,16G + 512GB,16G + 1024GB,"
            "Hệ thống Barebone (không có ổ cứng bộ nhớ),"
            "8GB + 128GB,8GB + 256GB,8GB+512GB,8GB+1024GB"
        )

        primary = extract_primary_memory_option(memory_text)
        product = build_product_variants(
            {
                "raw_attributes": {
                    "Dung lượng bộ nhớ": memory_text,
                }
            }
        )

        self.assertEqual(primary, {"ram": "8GB", "storage": "128GB"})
        self.assertEqual(product["ram"], "8GB")
        self.assertEqual(product["storage"], "128GB")
        self.assertEqual(product["color"], "")

    def test_build_product_variants_overrides_combined_memory_string(self) -> None:
        memory_text = "6G+128G,6G+256G,6G+512G,6G+1TB,Ổ cứng 6G 0"

        product = build_product_variants(
            {
                "ram": memory_text,
                "storage": "",
                "raw_attributes": {
                    "Dung lượng bộ nhớ": memory_text,
                },
            }
        )

        self.assertEqual(product["ram"], "6GB")
        self.assertEqual(product["storage"], "128GB")

    def test_select_primary_variant_prefers_lower_storage_then_ram(self) -> None:
        variants = [
            {"sku": "v1", "ram": "16GB", "storage": "256GB"},
            {"sku": "v2", "ram": "16GB", "storage": "128GB"},
            {"sku": "v3", "ram": "8GB", "storage": "128GB"},
        ]

        selected = select_primary_variant(variants)

        self.assertEqual(selected["sku"], "v3")
        self.assertEqual(selected["ram"], "8GB")
        self.assertEqual(selected["storage"], "128GB")

    def test_detect_clothing_template(self) -> None:
        product = {
            "product_name": "Cotton T-Shirt",
            "brand": "OEM",
            "color": "Black",
            "size": "L",
            "material": "Cotton",
        }

        self.assertEqual(detect_template(product), "clothing")

    def test_parse_size_options_for_clothing_sizes(self) -> None:
        parsed = parse_size_options("S/ 45-55kg,M/ 55-65kg,L/ 65-75kg,XL/ 75-85kg")

        self.assertEqual(parsed, ["S", "M", "L", "XL"])

    def test_normalize_attributes_for_hoodie_html_like_fields(self) -> None:
        raw_product = {
            "title": "Women's zip hoodie cardigan",
            "attributes": {
                "Phong cách": "Kiểu Hàn",
                "Kiểu cổ áo": "Cổ lật",
                "Dài tay áo": "Dài tay",
                "Vạt áo": "Khóa kéo",
                "Thích hợp cho mùa": "Mùa xuân thu",
                "Thành phần vải chính": "Bông polyester",
                "Chi tiết kiểu dáng": "Vạt dưới gân",
                "Màu sắc": "Màu trắng,Màu đen",
                "Kích cỡ": "S/ 45-55kg,M/ 55-65kg,L/ 65-75kg",
                "Trọng lượng": "301g (tính cả) - 350g (không tính)",
                "Có mũ liền không": "Liền mũ",
            },
        }

        normalized = normalize_attributes(raw_product)
        normalized = build_product_variants(normalized)

        self.assertEqual(normalized["category"], "hoodie")
        self.assertEqual(normalized["material"], "Bông polyester")
        self.assertEqual(normalized["season"], "Mùa xuân thu")
        self.assertEqual(normalized["collar"], "Cổ lật")
        self.assertEqual(normalized["sleeve_type"], "Dài tay")
        self.assertEqual(normalized["fastener_type"], "Khóa kéo")
        self.assertEqual(normalized["model_features"], "Liền mũ")
        self.assertEqual(normalized["size"], "S")
        self.assertEqual({variant["size"] for variant in normalized["variants"]}, {"S", "M", "L"})
        self.assertEqual({variant["color"] for variant in normalized["variants"]}, {"White", "Black"})

    def test_build_product_variants_does_not_parse_weight_as_ram_storage_for_hoodie(self) -> None:
        product = build_product_variants(
            {
                "title": "Zip hoodie",
                "style": "mũ trùm đầu",
                "color": "đen,xám",
                "size": "M ( 50-60kg ),L ( 60-67.5kg )",
                "raw_attributes": {
                    "Trọng lượng gram": "180g (tính cả) - 250g (không tính)",
                    "màu sắc": "đen,xám",
                    "Kích thước": "M ( 50-60kg ),L ( 60-67.5kg )",
                },
            }
        )

        self.assertEqual(detect_template(product), "hoodie")
        self.assertEqual(product.get("ram", ""), "")
        self.assertEqual(product.get("storage", ""), "")
        self.assertTrue(all(not variant.get("ram") for variant in product["variants"]))
        self.assertTrue(all(not variant.get("storage") for variant in product["variants"]))

    def test_build_product_variants_assigns_color_images_from_sku(self) -> None:
        product = build_product_variants(
            {
                "product_name": "Basic Tee",
                "raw_attributes": {
                    "Color": "Red, Black",
                    "Size": "M",
                },
                "sku": {
                    "skuImageList": [
                        {"value": "Red", "skuImageUrl": "https://img.example.com/red.jpg"},
                        {"value": "Black", "skuImageUrl": "https://img.example.com/black.jpg"},
                    ]
                },
            }
        )

        variant_by_color = {variant["color"]: variant for variant in product["variants"]}
        self.assertEqual(variant_by_color["Red"]["image_url"], "https://img.example.com/red.jpg")
        self.assertEqual(variant_by_color["Black"]["image_url"], "https://img.example.com/black.jpg")

    def test_extract_supplier_prefers_h1_title_attribute(self) -> None:
        page = Mock()
        page.evaluate.return_value = "çŸ³ç‹®å¸‚é©¬å†€éª¥æœè£…åŽ‚"

        supplier = extract_supplier(page)

        self.assertEqual(supplier, "çŸ³ç‹®å¸‚é©¬å†€éª¥æœè£…åŽ‚")


    def test_extract_sku_preserves_nested_sku_image_sources(self) -> None:
        page = Mock()
        page.evaluate.side_effect = [
            ["Red", "Black"],
            "Red Black",
        ]

        sku = extract_sku(
            page,
            init_data={
                "state": {
                    "detail": {
                        "skuModel": {
                            "skuImageList": [
                                {"value": "Red", "skuImageUrl": "https://img.example.com/red.jpg"},
                                {"value": "Black", "skuImageUrl": "https://img.example.com/black.jpg"},
                            ]
                        },
                        "skuCore": {
                            "sku2info": {
                                "sku-red": {"skuImageUrl": "https://img.example.com/red.jpg"},
                                "sku-black": {"skuImageUrl": "https://img.example.com/black.jpg"},
                            }
                        },
                    }
                }
            },
        )

        self.assertIn("skuModel", sku)
        self.assertIn("skuCore", sku)
        self.assertEqual(sku["skuModel"]["skuImageList"][0]["value"], "Red")
        self.assertEqual(sku["skuCore"]["sku2info"]["sku-black"]["skuImageUrl"], "https://img.example.com/black.jpg")
        self.assertEqual(sku["option_labels"], ["Red", "Black"])

    def test_extract_sku_falls_back_to_dom_image_list(self) -> None:
        page = Mock()
        page.evaluate.side_effect = [
            ["Wine Red", "Black"],
            "Wine Red Black",
            [
                {"value": "Wine Red", "skuImageUrl": "https://img.example.com/red.jpg"},
                {"value": "Black", "skuImageUrl": "https://img.example.com/black.jpg"},
            ],
        ]

        sku = extract_sku(page, init_data={})

        self.assertEqual(sku["option_labels"], ["Wine Red", "Black"])
        self.assertEqual(sku["skuImageList"][0]["value"], "Wine Red")
        self.assertEqual(sku["skuImageList"][1]["skuImageUrl"], "https://img.example.com/black.jpg")


if __name__ == "__main__":
    unittest.main()
