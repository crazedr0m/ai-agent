import unittest
from project_code import calculate_total_price

class TestCalculateTotalPrice(unittest.TestCase):

    def test_calculate_total_price(self):
        self.assertEqual(calculate_total_price(100, 0.1), 110)
        self.assertEqual(calculate_total_price(200, 0.05), 210)
        self.assertEqual(calculate_total_price(0, 0.1), 0)
        self.assertEqual(calculate_total_price(100, 0), 100)
        self.assertEqual(calculate_total_price(50, 0.2), 60)

if __name__ == '__main__':
    unittest.main()
    print('SUCCESS')