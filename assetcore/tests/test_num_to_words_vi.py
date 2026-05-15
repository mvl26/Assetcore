"""Unit tests cho tiện ích đọc số tiền tiếng Việt.

Run: bench --site miyano run-tests --module assetcore.tests.test_num_to_words_vi
"""
import unittest

from assetcore.services.shared.num_to_words_vi import num_to_words_vi


class TestNumToWordsVi(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(num_to_words_vi(0), "Không đồng")

    def test_thousand(self):
        self.assertEqual(num_to_words_vi(1000), "Một nghìn đồng")

    def test_million(self):
        self.assertEqual(num_to_words_vi(1000000), "Một triệu đồng")

    def test_1234567(self):
        self.assertEqual(
            num_to_words_vi(1234567),
            "Một triệu hai trăm ba mươi bốn nghìn năm trăm sáu mươi bảy đồng",
        )

    def test_rounds_decimal(self):
        self.assertEqual(num_to_words_vi(999.6), "Một nghìn đồng")

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            num_to_words_vi(-1)
