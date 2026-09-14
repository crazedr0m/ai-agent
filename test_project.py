import unittest
from project_code import calculate_total_price

class TestCalculateTotalPrice(unittest.TestCase):

    def test_calculate_total_price_with_no_tax(self):
        self.assertEqual(calculate_total_price(100, 0), 100)

    def test_calculate_total_price_with_positive_tax(self):
        self.assertEqual(calculate_total_price(100, 0.1), 110)

    def test_calculate_total_price_with_negative_tax(self):
        self.assertEqual(calculate_total_price(100, -0.1), 90)

    def test_calculate_total_price_with_zero_price(self):
        self.assertEqual(calculate_total_price(0, 0.1), 0)

    def test_calculate_total_price_with_large_tax_rate(self):
        self.assertEqual(calculate_total_price(100, 0.5), 150)

if __name__ == '__main__':
    unittest.main()