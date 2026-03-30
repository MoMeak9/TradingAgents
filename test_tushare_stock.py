import unittest
from unittest.mock import patch

import pandas as pd

from tradingagents.dataflows import tushare_stock


class TushareFundamentalsTests(unittest.TestCase):
    @patch("tradingagents.dataflows.tushare_stock._request_delay", lambda: None)
    @patch("tradingagents.dataflows.tushare_stock._get_tushare_api")
    @patch("tradingagents.dataflows.tushare_stock._call_with_retry")
    def test_get_fundamentals_includes_analysis_date_close_price(
        self,
        mock_call_with_retry,
        mock_get_tushare_api,
    ):
        pro = type(
            "FakeTusharePro",
            (),
            {
                "daily_basic": object(),
                "daily": object(),
                "fina_indicator": object(),
            },
        )()
        mock_get_tushare_api.return_value = pro

        df_basic = pd.DataFrame(
            [
                {
                    "trade_date": "20250327",
                    "turnover_rate": 1.23,
                    "pe": 5.6,
                    "pe_ttm": 5.4,
                    "pb": 0.7,
                    "ps": 1.1,
                    "ps_ttm": 1.0,
                    "dv_ratio": 4.2,
                    "dv_ttm": 4.0,
                    "total_mv": 21385300,
                    "circ_mv": 21385000,
                }
            ]
        )
        df_fina = pd.DataFrame(
            [
                {
                    "ann_date": "20250315",
                    "end_date": "20241231",
                    "eps": 1.23,
                    "bps": 10.0,
                }
            ]
        )
        df_daily = pd.DataFrame(
            [
                {
                    "trade_date": "20250327",
                    "close": 10.79,
                }
            ]
        )
        mock_call_with_retry.side_effect = [df_basic, df_daily, df_fina]

        result = tushare_stock.get_fundamentals("000001", curr_date="2025-03-27")

        self.assertIn("Trade Date: 20250327", result)
        self.assertIn("Close Price: 10.79", result)


if __name__ == "__main__":
    unittest.main()
