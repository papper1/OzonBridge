import unittest
from unittest.mock import ANY, patch

from translator.ai_hashtag_service import generate_hashtags, _parse_ai_hashtag_response
from translator.ai_translator import _clean_ozon_title, translate_product_fields, translate_text_zh_to_ru
from translator.api_client import (
    TranslationApiClient,
    TranslationRequest,
    translate_text,
)
from translator.field_translator import (
    convert_international_size_to_russian,
    translate_brand,
    translate_color,
    translate_description,
    translate_field,
    translate_material,
    translate_ram,
    translate_storage,
    translate_title,
    translate_weight,
)
from translator.openai_client import MissingOpenAIAPIKeyError


class TestTranslator(unittest.TestCase):
    def test_translate_brand_keeps_known_brand_format(self) -> None:
        self.assertEqual(translate_brand("lenovo"), "Lenovo")
        self.assertEqual(translate_brand("asus"), "ASUS")
        self.assertEqual(translate_brand("hp"), "HP")

    def test_translate_color_and_material_use_dictionary(self) -> None:
        self.assertEqual(translate_color("black"), "Чёрный")
        self.assertEqual(translate_material("cotton"), "Хлопок")
        self.assertEqual(translate_material("denim"), "denim")

    def test_translate_units_use_rule_based_format(self) -> None:
        self.assertEqual(translate_ram("16GB"), "16 ГБ")
        self.assertEqual(translate_storage("512GB SSD"), "512 ГБ SSD")
        self.assertEqual(translate_weight("1.5kg"), "1.5 кг")

    def test_translate_title_and_description_are_placeholders(self) -> None:
        self.assertEqual(translate_title("  Lenovo ThinkBook laptop "), "Lenovo ThinkBook laptop")
        self.assertEqual(translate_description("  Good product   for office "), "Good product for office")

    def test_convert_international_size_to_russian_supports_expected_mapping(self) -> None:
        self.assertEqual(convert_international_size_to_russian("XXS")["russian_size"], "40")
        self.assertEqual(convert_international_size_to_russian("XS")["russian_size"], "42")
        self.assertEqual(convert_international_size_to_russian("S")["russian_size"], "44")
        self.assertEqual(convert_international_size_to_russian("M")["russian_size"], "46")
        self.assertEqual(convert_international_size_to_russian("L")["russian_size"], "48")
        self.assertEqual(convert_international_size_to_russian("XL")["russian_size"], "50")
        self.assertEqual(convert_international_size_to_russian("XXL")["russian_size"], "52")
        self.assertEqual(convert_international_size_to_russian("3XL")["russian_size"], "54")
        self.assertEqual(convert_international_size_to_russian("4XL")["russian_size"], "56")

    def test_convert_international_size_to_russian_normalizes_case_and_handles_invalid(self) -> None:
        self.assertEqual(convert_international_size_to_russian(" xs ")["russian_size"], "42")
        self.assertEqual(convert_international_size_to_russian("xl")["russian_size"], "50")
        self.assertEqual(convert_international_size_to_russian("")["russian_size"], "")
        self.assertFalse(convert_international_size_to_russian("")["valid"])
        self.assertEqual(convert_international_size_to_russian(None)["russian_size"], "")
        self.assertFalse(convert_international_size_to_russian(None)["valid"])
        self.assertEqual(convert_international_size_to_russian("undefined")["russian_size"], "")
        self.assertFalse(convert_international_size_to_russian("undefined")["valid"])

    def test_translate_field_is_safe_and_field_aware(self) -> None:
        self.assertEqual(translate_field("color", "silver"), "Серебристый")
        self.assertEqual(translate_field("ram", "8GB"), "8 ГБ")
        self.assertEqual(translate_field("unknown_field", "  Keep Me  "), "Keep Me")
        self.assertEqual(translate_field("brand", None), "")

    def test_api_client_placeholder_keeps_text_normalized(self) -> None:
        client = TranslationApiClient()
        result = client.translate(
            TranslationRequest(
                text="  Lenovo ThinkBook laptop  ",
                field_name="title",
            )
        )

        self.assertEqual(result.text, "Lenovo ThinkBook laptop")
        self.assertFalse(result.translated)
        self.assertEqual(result.provider, "placeholder")

    def test_translate_text_wrapper_uses_placeholder_client(self) -> None:
        self.assertEqual(
            translate_text("  office laptop  ", field_name="description"),
            "office laptop",
        )

    @patch("translator.ai_translator._translate_text_with_openai")
    def test_translate_text_zh_to_ru_returns_ai_output(self, mock_translate) -> None:
        mock_translate.return_value = "Мужская свободная футболка с круглым вырезом, летняя модель"

        translated = translate_text_zh_to_ru(
            "夏季新款男士宽松短袖T恤潮流百搭圆领上衣",
            content_type="title",
        )

        self.assertEqual(
            translated,
            "Мужская свободная футболка с круглым вырезом, летняя модель",
        )
        mock_translate.assert_called_once_with(
            ANY,
            system_prompt=ANY,
            task_label=ANY,
        )

    @patch("translator.ai_translator._translate_text_with_openai")
    def test_translate_text_zh_to_ru_falls_back_when_key_missing(self, mock_translate) -> None:
        mock_translate.side_effect = MissingOpenAIAPIKeyError("Missing OpenAI API key")

        translated = translate_text_zh_to_ru(
            "夏季新款男士宽松短袖T恤潮流百搭圆领上衣",
            content_type="title",
        )

        self.assertEqual(translated, "夏季新款男士宽松短袖T恤潮流百搭圆领上衣")

    @patch("translator.ai_translator.translate_text_zh_to_ru")
    def test_translate_product_fields_translates_core_fields(self, mock_translate) -> None:
        mock_translate.side_effect = lambda text, content_type="generic": {
            ("夏季新款男士宽松短袖T恤潮流百搭圆领上衣", "title"): "Мужская свободная футболка с круглым вырезом, летняя модель",
            ("纯棉面料，透气舒适", "description"): "Хлопковая ткань, дышащая и комфортная",
            ("颜色", "attribute"): "Цвет",
            ("黑色", "attribute"): "Черный",
            ("尺码", "attribute"): "Размер",
            ("XL", "attribute"): "XL",
        }.get((text, content_type), text)

        translated = translate_product_fields(
            {
                "title": "夏季新款男士宽松短袖T恤潮流百搭圆领上衣",
                "description": "纯棉面料，透气舒适",
                "attributes": {"颜色": "黑色", "尺码": "XL"},
            }
        )

        self.assertEqual(
            translated["translated_title"],
            "Мужская свободная футболка с круглым вырезом, летняя модель",
        )
        self.assertEqual(
            translated["translated_description"],
            "Хлопковая ткань, дышащая и комфортная",
        )
        self.assertEqual(
            translated["translated_attributes"],
            {"Цвет": "Черный", "Размер": "XL"},
        )

    def test_clean_ozon_title_removes_extra_separators(self) -> None:
        self.assertEqual(
            _clean_ozon_title("  Мужская футболка / / , , летняя модель  "),
            "Мужская футболка, летняя модель",
        )


    @patch("translator.ai_hashtag_service._generate_hashtags_with_ai")
    def test_generate_hashtags_uses_ai_output(self, mock_generate) -> None:
        mock_generate.return_value = [
            "#hoodie",
            "#menswear",
            "#casualstyle",
            "#streetwear",
            "#cottonhoodie",
            "#blackhoodie",
            "#summerwear",
            "#oversizedhoodie",
        ]

        product = generate_hashtags(
            {
                "title": "Men's oversized summer hoodie",
                "description": "Lightweight casual hoodie for daily wear",
                "category": "hoodie",
                "color": "black",
                "material": "cotton",
            }
        )

        self.assertEqual(
            product["hashtags"],
            [
                "#hoodie",
                "#menswear",
                "#casualstyle",
                "#streetwear",
                "#cottonhoodie",
                "#blackhoodie",
                "#summerwear",
                "#oversizedhoodie",
            ],
        )

    @patch("translator.ai_hashtag_service._generate_hashtags_with_ai")
    def test_generate_hashtags_falls_back_to_product_terms(self, mock_generate) -> None:
        mock_generate.side_effect = RuntimeError("boom")

        product = generate_hashtags(
            {
                "title": "Men's oversized summer hoodie",
                "category": "hoodie",
                "color": "black",
                "material": "cotton",
                "attributes": {"gender": "men", "style": "streetwear"},
            }
        )

        self.assertIn("#hoodie", product["hashtags"])
        self.assertIn("#blackhoodie", product["hashtags"])
        self.assertIn("#cottonhoodie", product["hashtags"])
        self.assertIn("#menswear", product["hashtags"])
        self.assertTrue(all(len(tag) <= 25 for tag in product["hashtags"]))
        self.assertFalse(any("oversizedsummerhoodie" in tag for tag in product["hashtags"]))

    def test_parse_ai_hashtag_response_supports_markdown_json(self) -> None:
        parsed = _parse_ai_hashtag_response(
            '```json\n["#hoodie", "#menswear", "#streetwear", "#casualstyle", "#blackhoodie", "#cottonhoodie", "#oversizedhoodie", "#summerwear"]\n```'
        )

        self.assertEqual(
            parsed,
            [
                "#hoodie",
                "#menswear",
                "#streetwear",
                "#casualstyle",
                "#blackhoodie",
                "#cottonhoodie",
                "#oversizedhoodie",
                "#summerwear",
            ],
        )

    def test_parse_ai_hashtag_response_supports_object_wrapper(self) -> None:
        parsed = _parse_ai_hashtag_response(
            '{"hashtags": ["#hoodie", "#menswear", "#streetwear", "#casualstyle", "#blackhoodie", "#cottonhoodie", "#oversizedhoodie", "#summerwear"]}'
        )

        self.assertIn("#hoodie", parsed)
        self.assertIn("#menswear", parsed)
        self.assertEqual(len(parsed), 8)


if __name__ == "__main__":
    unittest.main()
