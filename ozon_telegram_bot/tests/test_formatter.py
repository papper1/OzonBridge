from __future__ import annotations

import unittest

from formatters.message_formatter import MessageFormatter


class FormatterTests(unittest.TestCase):
    def test_help_contains_order_now(self) -> None:
        formatter = MessageFormatter()
        self.assertIn("/order_now", formatter.format_help())

    def test_format_return_includes_dates(self) -> None:
        formatter = MessageFormatter()
        message = formatter.format_return(
            {
                "shop_name": "Shop A",
                "return_number": "RET-1",
                "return_type": "Refund",
                "posting_number": "POST-1",
                "status": "approved",
                "reason": "Customer changed mind",
                "created_date": "2026-05-18T08:30:00Z",
                "changed_date": "2026-05-18T10:45:00Z",
            }
        )
        self.assertIn("Tao luc: 2026-05-18 08:30:00", message)
        self.assertIn("Cap nhat luc: 2026-05-18 10:45:00", message)


if __name__ == "__main__":
    unittest.main()
