import unittest
from unittest.mock import patch

from mapper.field_mapper import map_fields
from mapper.template_option_mapper import map_field_value, normalize_text


class TestTemplateOptionMapper(unittest.TestCase):
    def test_normalize_text_lowercases_and_removes_noise(self) -> None:
        normalized = normalize_text("  MÃ¹a xuÃ¢n & MÃ¹a thu!! ")
        self.assertTrue(normalized)
        self.assertNotIn("!", normalized)
        self.assertEqual(normalized, normalized.lower())

    def test_map_style_uses_rule_based_alias(self) -> None:
        self.assertEqual(map_field_value("Style", "phong cÃ¡ch thá»ƒ thao"), "Sports")
        self.assertEqual(map_field_value("Style", "ä¼‘é—²"), "Casual")

    def test_map_season_uses_allowed_value_not_raw_text(self) -> None:
        self.assertEqual(map_field_value("Season", "mÃ¹a xuÃ¢n vÃ  mÃ¹a thu"), "Demi-season")
        self.assertEqual(map_field_value("Season", "dong"), "Winter")

    def test_map_material_supports_multi_values(self) -> None:
        self.assertEqual(map_field_value("Material", "æ£‰, èšé…¯çº¤ç»´, æŠ“ç»’"), "Cotton;Polyester;Fleece")

    def test_map_sleeve_type_supports_aliases(self) -> None:
        self.assertEqual(map_field_value("Sleeve Type", "é•¿è¢–"), "Long")
        self.assertEqual(map_field_value("Sleeve Type", "tay ngáº¯n"), "Short")

    def test_map_hoodie_option_fields_use_only_allowed_values(self) -> None:
        self.assertEqual(map_field_value("Fastener type", "zipper, drawstring, velcro, clip"), "Zipper;Drawstring;Velcro")
        self.assertEqual(map_field_value("Drawing", "solid / logo / stars"), "Plain;Logo;Stars")
        self.assertEqual(
            map_field_value("Model Features", "hood, breathable, hidden pocket, ventilation, wrinkle resistant, heated, extra"),
            "hood;Breathable material;Hidden pocket;ventilation;wrinkle-resistant material;Heated",
        )
        self.assertEqual(
            map_field_value("Decorative Elements", "label, rhinestones, ribbon, spikes, chain"),
            "Label;Rhinestones;Ribbon;Spikes",
        )
        self.assertEqual(map_field_value("Collar", "round neck"), "round")

    @patch("mapper.template_option_mapper._ai_select_allowed_values")
    def test_map_field_value_uses_ai_fallback_but_keeps_allowed_values_only(self, mock_ai_select) -> None:
        mock_ai_select.return_value = ["Demi-season"]
        self.assertEqual(map_field_value("Season", "giao mÃ¹a"), "Demi-season")

    def test_map_text_field_material_composition_reuses_material_mapping(self) -> None:
        self.assertEqual(
            map_field_value("Material composition", "æ£‰, èšé…¯çº¤ç»´", product={"material": "æ£‰, èšé…¯çº¤ç»´"}),
            "Cotton;Polyester",
        )

    def test_map_text_field_strict_returns_unknown_for_untrusted_height(self) -> None:
        self.assertEqual(map_field_value("Height", "cao vá»«a"), "")
        self.assertEqual(map_field_value("HS codes of the EAEU", ""), "UNKNOWN")

    def test_map_fields_applies_option_mapping_before_generic_translation(self) -> None:
        row = map_fields(
            {
                "style": "phong cÃ¡ch thá»ƒ thao",
                "season": "mÃ¹a xuÃ¢n vÃ  mÃ¹a thu",
                "material": "æ£‰, èšé…¯çº¤ç»´",
                "sleeve_type": "é•¿è¢–",
            },
            {
                "Style": "style",
                "Season": "season",
                "Material": "material",
                "Sleeve Type": "sleeve_type",
            },
        )

        self.assertEqual(
            row,
            {
                "Style": "Sports",
                "Season": "Demi-season",
                "Material": "Cotton;Polyester",
                "Sleeve Type": "Long",
            },
        )


if __name__ == "__main__":
    unittest.main()
