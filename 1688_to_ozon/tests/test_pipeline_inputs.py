import unittest

from crawler.search import _extract_product_links_from_hrefs, is_product_detail_url
from main import (
    SOURCE_EBAY,
    SOURCE_ETSY,
    SOURCE_1688,
    SOURCE_SHEIN,
    SOURCE_MODE_KEYWORD,
    SOURCE_MODE_PRODUCT_URL,
    SOURCE_MODE_SHOP_URL,
    build_export_stem,
    detect_source,
    detect_input_mode,
    normalize_source_value,
)


class TestPipelineInputs(unittest.TestCase):
    def test_detect_input_mode_supports_keyword_product_and_shop(self) -> None:
        self.assertEqual(detect_input_mode("hoodie"), SOURCE_MODE_KEYWORD)
        self.assertEqual(
            detect_input_mode("https://detail.1688.com/offer/987041511404.html?spm=a"),
            SOURCE_MODE_PRODUCT_URL,
        )
        self.assertEqual(
            detect_input_mode("https://us.shein.com/Manfinity-EMRG-Men-Solid-Tee-p-12345678-cat-1738.html"),
            SOURCE_MODE_PRODUCT_URL,
        )
        self.assertEqual(
            detect_input_mode("https://www.etsy.com/listing/4440676337/custom-embroidery-initial-heart-sleeve"),
            SOURCE_MODE_PRODUCT_URL,
        )
        self.assertEqual(
            detect_input_mode("https://www.ebay.com/itm/358165965187"),
            SOURCE_MODE_PRODUCT_URL,
        )
        self.assertEqual(
            detect_input_mode("https://shop.1688.com/page/offerlist.htm?memberId=b2b-123"),
            SOURCE_MODE_SHOP_URL,
        )

    def test_detect_source_supports_1688_shein_etsy_and_ebay(self) -> None:
        self.assertEqual(detect_source("hoodie", ""), SOURCE_1688)
        self.assertEqual(
            detect_source("https://us.shein.com/Manfinity-EMRG-Men-Solid-Tee-p-12345678-cat-1738.html", ""),
            SOURCE_SHEIN,
        )
        self.assertEqual(
            detect_source("https://www.etsy.com/listing/4440676337/custom-embroidery-initial-heart-sleeve", ""),
            SOURCE_ETSY,
        )
        self.assertEqual(
            detect_source("https://www.ebay.com/itm/358165965187", ""),
            SOURCE_EBAY,
        )
        self.assertEqual(detect_source("https://detail.1688.com/offer/987041511404.html", ""), SOURCE_1688)
        self.assertEqual(detect_source("https://detail.1688.com/offer/987041511404.html", "shein"), SOURCE_SHEIN)

    def test_normalize_source_value_canonicalizes_product_url(self) -> None:
        self.assertEqual(
            normalize_source_value(
                "https://detail.1688.com/offer/987041511404.html?spm=a#detail",
                SOURCE_MODE_PRODUCT_URL,
            ),
            "https://detail.1688.com/offer/987041511404.html",
        )

    def test_build_export_stem_uses_product_id_for_single_product(self) -> None:
        self.assertEqual(
            build_export_stem("https://detail.1688.com/offer/987041511404.html", SOURCE_MODE_PRODUCT_URL),
            "product_987041511404",
        )
        self.assertEqual(
            build_export_stem(
                "https://www.etsy.com/listing/4440676337/custom-embroidery-initial-heart-sleeve",
                SOURCE_MODE_PRODUCT_URL,
            ),
            "etsy_4440676337",
        )
        self.assertEqual(
            build_export_stem("https://www.ebay.com/itm/358165965187", SOURCE_MODE_PRODUCT_URL),
            "ebay_358165965187",
        )

    def test_is_product_detail_url_matches_1688_offer_pages(self) -> None:
        self.assertTrue(is_product_detail_url("https://detail.1688.com/offer/987041511404.html"))
        self.assertFalse(is_product_detail_url("https://shop.1688.com/page/offerlist.htm"))

    def test_extract_product_links_from_hrefs_filters_duplicates_and_noise(self) -> None:
        hrefs = [
            "https://detail.1688.com/offer/987041511404.html?foo=1",
            "https://detail.1688.com/offer/987041511404.html?foo=2",
            "https://shop.1688.com/page/offerlist.htm",
            "https://detail.1688.com/offer/946972572932.html",
        ]

        self.assertEqual(
            _extract_product_links_from_hrefs(hrefs, max_links=10),
            [
                "https://detail.1688.com/offer/987041511404.html",
                "https://detail.1688.com/offer/946972572932.html",
            ],
        )


if __name__ == "__main__":
    unittest.main()
