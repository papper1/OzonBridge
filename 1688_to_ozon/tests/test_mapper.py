import unittest
from unittest.mock import patch

from mapper.attribute_mapper import map_attributes_to_ozon
from mapper.field_mapper import map_fields
from mapper.product_mapper import map_product_to_ozon
from mapper.template_loader import load_template
from validators.required_field_validator import find_missing_required_fields


class TestMapper(unittest.TestCase):
    def test_map_attributes_to_ozon(self) -> None:
        specs = {
            "Product name": "Lenovo ThinkBook 14",
            "Brand*": "Lenovo",
            "Random access memory": "16GB",
            "Total SSD capacity, GB": "512",
        }

        mapped = map_attributes_to_ozon(specs)

        self.assertIsInstance(mapped, list)
        self.assertIn({"name": "Brand*", "value": "Lenovo"}, mapped)
        self.assertIn({"name": "Random access memory", "value": "16GB"}, mapped)
        self.assertIn({"name": "Total SSD capacity, GB", "value": "512"}, mapped)

    def test_map_fields_supports_old_and_new_template_formats(self) -> None:
        product = {
            "product_name": "Lenovo ThinkBook laptop",
            "brand": "lenovo",
            "ram": "16GB",
            "color": "black",
        }

        mapped = map_fields(
            product,
            {
                "Product name": {"field": "product_name", "translate": "title"},
                "Brand*": {"field": "brand", "translate": "brand"},
                "Random access memory": {"field": "ram", "translate": "ram"},
                "Color name": {"field": "color", "translate": "color"},
                "Raw Brand": "brand",
            },
        )

        self.assertEqual(mapped["Product name"], "Lenovo ThinkBook laptop")
        self.assertEqual(mapped["Brand*"], "Lenovo")
        self.assertEqual(mapped["Random access memory"], "16 ГБ")
        self.assertEqual(mapped["Color name"], "Чёрный")
        self.assertEqual(mapped["Raw Brand"], "lenovo")

    def test_map_product_to_ozon_for_laptop(self) -> None:
        product = {
            "product_name": "Lenovo ThinkBook laptop",
            "brand": "Lenovo",
            "model": "ThinkBook 14",
            "cpu": "Intel Core i5-1240P",
            "ram": "16GB",
            "storage": "512GB SSD",
            "screen_size": "15.6",
            "weight": "1.4kg",
            "color": "black",
            "price": "699",
            "supplier": "Lenovo Store",
            "source_url": "https://detail.1688.com/offer/123.html",
            "raw_attributes": {
                "Product size": "300*80*400mm",
            },
            "images": [
                "https://img.example.com/1.jpg",
                "https://img.example.com/2.jpg",
            ],
            "variants": [
                {
                    "sku": "thinkbook14-grey-16gb-512gb",
                    "color": "Grey",
                    "color_name": "Space Grey",
                    "image_url": "https://img.example.com/grey.jpg",
                    "ram": "16GB",
                    "storage": "512GB",
                    "price": "699",
                },
                {
                    "sku": "thinkbook14-silver-16gb-512gb",
                    "color": "Silver",
                    "color_name": "Moonlight Silver",
                    "image_url": "https://img.example.com/silver.jpg",
                    "ram": "16GB",
                    "storage": "512GB",
                    "price": "719",
                },
            ],
        }

        mapped = map_product_to_ozon(product)

        self.assertIsInstance(mapped, dict)
        self.assertIn("name", mapped)
        self.assertIn("category", mapped)
        self.assertIn("attributes", mapped)
        self.assertIn("variants", mapped)

        self.assertEqual(mapped["category"], "laptop")
        self.assertEqual(mapped["template_name"], "laptop")
        self.assertIsNone(mapped["category_id"])
        self.assertTrue(mapped["name"].startswith("Lenovo ThinkBook 14"))
        self.assertEqual(mapped["supplier"], "Lenovo Store")
        self.assertEqual(mapped["source_url"], "https://detail.1688.com/offer/123.html")
        self.assertEqual(mapped["row_data"]["Brand*"], "Lenovo")
        self.assertEqual(mapped["row_data"]["Type*"], "Laptop")
        self.assertEqual(mapped["row_data"]["Random access memory"], "16 GB")
        self.assertEqual(mapped["row_data"]["Total SSD capacity, GB"], "512")
        self.assertEqual(mapped["row_data"]["Product color"], "grey")
        self.assertEqual(mapped["row_data"]["Color name"], "Space Grey")
        self.assertEqual(mapped["row_data"]["Link to the main image*"], "https://img.example.com/grey.jpg")
        self.assertEqual(
            mapped["row_data"]["Links to additional photos"],
            "https://img.example.com/1.jpg\nhttps://img.example.com/2.jpg",
        )
        self.assertEqual(mapped["row_data"]["Package width, mm*"], "300")
        self.assertEqual(mapped["row_data"]["Package height, mm*"], "80")
        self.assertEqual(mapped["row_data"]["Package length, mm*"], "400")
        self.assertEqual(len(mapped["attributes"]), 19)
        self.assertEqual(len(mapped["variants"]), 2)
        self.assertEqual(mapped["variants"][0]["sku"], "thinkbook14-grey-16gb-512gb")
        self.assertEqual(mapped["variants"][0]["color"], "Grey")
        self.assertEqual(mapped["missing_required_fields"], [])

    def test_map_product_to_ozon_sets_gaming_laptop_type(self) -> None:
        mapped = map_product_to_ozon(
            {
                "product_name": "Gaming notebook",
                "brand": "OEM",
                "model": "G15",
                "cpu": "Intel Core i7",
                "ram": "16GB",
                "storage": "512GB",
                "raw_attributes": {"Graphics": "NVIDIA GeForce RTX 4060"},
            }
        )

        self.assertEqual(mapped["row_data"]["Type*"], "Gaming laptop")

    def test_map_product_to_ozon_detects_hoodie_template(self) -> None:
        mapped = map_product_to_ozon(
            {
                "product_name": "Oversized fleece hoodie",
                "brand": "OEM",
                "model": "HD-01",
                "color": "black",
                "size": "M",
                "material": "cotton",
                "weight": "0.8kg",
                "price": "89",
                "images": ["https://img.example.com/hoodie.jpg"],
                "raw_attributes": {
                    "Product size": "350*80*450mm",
                    "Sleeve Type": "Long sleeve",
                },
            }
        )

        self.assertEqual(mapped["category"], "hoodie")
        self.assertEqual(mapped["template_name"], "hoodie")
        self.assertEqual(mapped["row_data"]["Type*"], "Hoodie")
        self.assertEqual(mapped["row_data"]["Price, CNY*"], "249")
        self.assertEqual(mapped["row_data"]["Brand in Clothing and Footwear*"], "Oem")
        self.assertEqual(mapped["row_data"]["Russian size*"], "46")
        self.assertEqual(mapped["row_data"]["Height"], "")
        self.assertTrue(mapped["row_data"]["#Hashtags"].startswith("#"))
        self.assertEqual(mapped["row_data"]["Manufacturer size"], "M")
        self.assertEqual(mapped["row_data"]["Link to the main image*"], "https://img.example.com/hoodie.jpg")

    def test_map_product_to_ozon_exports_hashtags_for_template_column(self) -> None:
        mapped = map_product_to_ozon(
            {
                "product_name": "Oversized fleece hoodie",
                "brand": "OEM",
                "model": "HD-04",
                "color": "black",
                "size": "M",
                "hashtags": ["#hoodie", "#menswear", "#streetwear"],
                "images": ["https://img.example.com/hoodie.jpg"],
            }
        )

        self.assertEqual(mapped["row_data"]["#Hashtags"], "#hoodie #menswear #streetwear")

    @patch("mapper.product_mapper.generate_hashtags")
    def test_map_product_to_ozon_generates_hashtags_when_missing(self, mock_generate_hashtags) -> None:
        mock_generate_hashtags.return_value = {
            "product_name": "Oversized fleece hoodie",
            "brand": "OEM",
            "model": "HD-05",
            "color": "black",
            "size": "M",
            "hashtags": ["#hoodie", "#menswear"],
            "images": ["https://img.example.com/hoodie.jpg"],
        }

        mapped = map_product_to_ozon(
            {
                "product_name": "Oversized fleece hoodie",
                "brand": "OEM",
                "model": "HD-05",
                "color": "black",
                "size": "M",
                "images": ["https://img.example.com/hoodie.jpg"],
            }
        )

        mock_generate_hashtags.assert_called_once()
        self.assertEqual(mapped["row_data"]["#Hashtags"], "#hoodie #menswear")

    def test_map_product_to_ozon_uses_default_package_and_gender_when_missing(self) -> None:
        mapped = map_product_to_ozon(
            {
                "product_name": "Basic hoodie",
                "brand": "OEM",
                "model": "HD-02",
                "color": "black",
                "size": "L",
                "images": ["https://img.example.com/basic-hoodie.jpg"],
            }
        )

        self.assertEqual(mapped["row_data"]["Weight in package, g*"], "600")
        self.assertEqual(mapped["row_data"]["Package width, mm*"], "350")
        self.assertEqual(mapped["row_data"]["Package height, mm*"], "80")
        self.assertEqual(mapped["row_data"]["Package length, mm*"], "400")
        self.assertEqual(mapped["row_data"]["Gender*"], "Male")
        self.assertEqual(mapped["row_data"]["Height"], "")
        self.assertEqual(mapped["row_data"]["Russian size*"], "48")

    def test_map_product_to_ozon_keeps_height_blank_and_russian_size_fallback_when_size_is_missing(self) -> None:
        mapped = map_product_to_ozon(
            {
                "product_name": "Basic hoodie",
                "brand": "OEM",
                "model": "HD-03",
                "color": "black",
                "images": ["https://img.example.com/basic-hoodie.jpg"],
            }
        )

        self.assertEqual(mapped["row_data"]["Height"], "")
        self.assertEqual(mapped["row_data"]["Russian size*"], "46")

    def test_map_product_to_ozon_converts_xxxl_and_xxxxl_sizes(self) -> None:
        mapped_xxxl = map_product_to_ozon(
            {
                "product_name": "Basic hoodie",
                "brand": "OEM",
                "model": "HD-06",
                "color": "black",
                "size": "XXXL",
                "images": ["https://img.example.com/basic-hoodie.jpg"],
            }
        )
        mapped_xxxxl = map_product_to_ozon(
            {
                "product_name": "Basic hoodie",
                "brand": "OEM",
                "model": "HD-07",
                "color": "black",
                "size": "XXXXL",
                "images": ["https://img.example.com/basic-hoodie.jpg"],
            }
        )

        self.assertEqual(mapped_xxxl["row_data"]["Russian size*"], "54")
        self.assertEqual(mapped_xxxxl["row_data"]["Russian size*"], "56")

    def test_map_product_to_ozon_uses_upper_bound_for_weight_range(self) -> None:
        mapped = map_product_to_ozon(
            {
                "product_name": "Office laptop",
                "brand": "OEM",
                "model": "M1",
                "cpu": "Intel Core i5",
                "ram": "8GB",
                "storage": "256GB",
                "weight": "1.2-1.3kg（kg）",
            }
        )

        self.assertEqual(mapped["row_data"]["Weight in package, g*"], "1300")

    def test_load_template_and_validate_required_fields(self) -> None:
        template = load_template("clothing")
        missing_fields = find_missing_required_fields(
            {"product_name": "T-Shirt", "brand": "OEM", "color": "Black"},
            template["required_fields"],
        )

        self.assertEqual(template["template_name"], "clothing")
        self.assertIn("size", missing_fields)
        self.assertIn("article_code", missing_fields)
        self.assertIn("main_image_url", missing_fields)


if __name__ == "__main__":
    unittest.main()
