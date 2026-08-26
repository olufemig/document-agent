"""Streamlit UI tests."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
    def test_renders_primary_controls(self) -> None:
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
        app.run()

        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "Document Agent")
        self.assertEqual(app.text_area[0].label, "Document specification")
        self.assertEqual(
            [button.label for button in app.button],
            ["Ingest Case Studies", "Generate Document"],
        )


if __name__ == "__main__":
    unittest.main()
