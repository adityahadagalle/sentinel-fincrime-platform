import unittest
from app.engines.scoring_engine import score_transaction

class TestAnalyticsRealtime(unittest.TestCase):
    def test_01_risk_score_categorization(self):
        # Low risk (<40)
        low_tx = {"amount": 1000.0}
        acc_low = {"avg_monthly_tx_amount": 50000.0, "is_new_receiver": False}
        res_low = score_transaction(low_tx, acc_low)
        score_low = res_low.get("risk_score", 0)
        self.assertLess(score_low, 40)

        # High risk (70-84)
        high_tx = {"amount": 250000.0}
        acc_high = {"avg_monthly_tx_amount": 10000.0, "is_new_receiver": True}
        res_high = score_transaction(high_tx, acc_high)
        score_high = res_high.get("risk_score", 0)
        self.assertGreaterEqual(score_high, 40)

if __name__ == "__main__":
    unittest.main()
