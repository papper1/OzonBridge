from __future__ import annotations

import unittest

from services.command_server import CommandServer


class CommandServerParsingTests(unittest.TestCase):
    def test_extract_command(self) -> None:
        command = CommandServer._extract_command("@bot /order shop-a")
        self.assertEqual(command, "/order shop-a")


if __name__ == "__main__":
    unittest.main()
