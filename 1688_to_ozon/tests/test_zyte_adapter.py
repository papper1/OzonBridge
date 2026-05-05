import unittest

from adapters.source_to_ozon_input_adapter import convert_source_product_to_existing_ozon_input


class TestZyteAdapter(unittest.TestCase):
    def test_convert_source_product_to_existing_ozon_input_preserves_pipeline_shape(self) -> None:
        source_product = {
            "source": "etsy",
            "product_url": "https://www.etsy.com/listing/123/demo-product",
            "canonical_url": "https://www.etsy.com/listing/123/demo-product",
            "title": "Demo Product",
            "product_id": "123",
            "sku": "SKU-123",
            "brand": "Demo Brand",
            "price": 19.99,
            "price_text": "$19.99",
            "currency": "USD",
            "availability": "InStock",
            "category_path": ["Clothing", "Hoodies"],
            "category": "Hoodies",
            "images": ["https://example.com/1.jpg"],
            "main_image": "https://example.com/1.jpg",
            "description": "Soft hoodie",
            "attributes": {
                "color": "Black",
                "sizes": ["S", "M"],
                "material": "Cotton",
                "style": "Casual",
            },
            "variants": [
                {
                    "sku_code": "SKU-123-S",
                    "color": "Black",
                    "size": "S",
                    "price_text": "$19.99",
                }
            ],
        }

        payload = convert_source_product_to_existing_ozon_input(source_product, "etsy")

        self.assertEqual(payload["source"], "etsy")
        self.assertEqual(payload["title"], "Demo Product")
        self.assertEqual(payload["price"], "$19.99")
        self.assertEqual(payload["attributes"]["brand"], "Demo Brand")
        self.assertEqual(payload["attributes"]["color"], "Black")
        self.assertEqual(payload["attributes"]["size"], "S")
        self.assertEqual(payload["variants"][0]["sku"], "SKU-123-S")
        self.assertEqual(payload["sku"]["currency"], "USD")

    def test_convert_source_product_to_existing_ozon_input_splits_combined_size_and_color_labels(self) -> None:
        source_product = {
            "source": "shein",
            "product_url": "https://www.shein.com.vn/demo.html",
            "title": "Demo Hoodie",
            "variants": [
                {
                    "sku_code": "SKU-1",
                    "size": "XS WHITE ($44.53)",
                    "price_text": "$44.53",
                },
                {
                    "sku_code": "SKU-2",
                    "size": "3XL BLACK ($44.53)",
                    "price_text": "$44.53",
                },
            ],
            "attributes": {},
        }

        payload = convert_source_product_to_existing_ozon_input(source_product, "shein")

        self.assertEqual(payload["attributes"]["color"], "White")
        self.assertEqual(payload["attributes"]["size"], "XS")
        self.assertEqual(payload["variants"][0]["size"], "XS")
        self.assertEqual(payload["variants"][0]["color"], "White")
        self.assertEqual(payload["variants"][0]["color_name"], "White")
        self.assertEqual(payload["variants"][1]["size"], "3XL")
        self.assertEqual(payload["variants"][1]["color"], "Black")


if __name__ == "__main__":
    unittest.main()
