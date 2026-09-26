import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import category_for, read_csv, reconcile, summarize

ROOT = Path(__file__).resolve().parents[1]


class SpendMatchTest(unittest.TestCase):
    def setUp(self):
        self.campaigns = read_csv((ROOT / "sample_data/campaigns.csv").read_bytes(),
                                  ["campaign_id", "campaign_name", "agency", "region"])
        self.pos = read_csv((ROOT / "sample_data/purchase_orders.csv").read_bytes(),
                            ["po_id", "campaign_id", "campaign_name", "agency", "region",
                             "raw_category", "gl_code", "amount"])

    def test_taxonomy(self):
        self.assertEqual(category_for("consumer insights"), "Research")

    def test_review_not_in_report(self):
        rows = reconcile(self.campaigns, self.pos)
        self.assertEqual(rows[1]["status"], "review")
        self.assertEqual(sum(x["Spend"] for x in summarize(rows)), 37000)

    def test_approval_and_code_mismatch(self):
        rows = reconcile(self.campaigns, self.pos, {"PO-102": "CMP-001"})
        self.assertEqual(rows[1]["status"], "approved")
        self.assertEqual(rows[4]["code_warning"], "Category/code mismatch")
        self.assertEqual(sum(x["Spend"] for x in summarize(rows)), 45500)


if __name__ == "__main__":
    unittest.main()
