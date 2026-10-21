import unittest

from scripts.hello import hello


class HelloTest(unittest.TestCase):
    def test_hello_returns_expected_string(self):
        self.assertEqual(hello(), "hej från SeaParser")


if __name__ == "__main__":
    unittest.main()
