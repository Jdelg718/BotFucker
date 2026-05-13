import unittest

from botfucker.samples import RESERVED_SAMPLE_DOMAINS, build_sample_review_items


class SampleDataTests(unittest.TestCase):
    def test_sample_items_are_deterministic(self):
        first = [item.to_dict() for item in build_sample_review_items()]
        second = [item.to_dict() for item in build_sample_review_items()]

        self.assertEqual(first, second)

    def test_sample_items_use_reserved_fake_domains_only(self):
        items = build_sample_review_items()

        self.assertGreaterEqual(len(items), 4)
        for item in items:
            self.assertIn(item.sender_domain, RESERVED_SAMPLE_DOMAINS)
            self.assertRegex(item.from_email, r"@(?:example\.com|example\.net|example\.org|invalid|test)$")
            self.assertNotIn("gmail.com", item.from_email)
            self.assertNotIn("outlook.com", item.from_email)

    def test_sample_items_make_mock_status_explicit(self):
        for item in build_sample_review_items():
            data = item.to_dict()
            self.assertTrue(data["mock_only"])
            self.assertIn("sample", data["source"])
            self.assertIn("mock", data["safety_note"].lower())


if __name__ == "__main__":
    unittest.main()
