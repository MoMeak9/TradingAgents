import io
import unittest
from argparse import Namespace
from unittest.mock import patch

from rich.console import Console

import analyze


class ResolveAnalysisDateTests(unittest.TestCase):
    def test_explicit_date_is_not_adjusted(self):
        original_date, effective_date = analyze.resolve_analysis_date(
            tickers=["000001"],
            requested_date="2026-03-29",
            date_was_explicit=True,
        )

        self.assertEqual("2026-03-29", original_date)
        self.assertEqual("2026-03-29", effective_date)

    @patch("tradingagents.dataflows.market_utils.get_cn_trade_dates")
    def test_default_cn_holiday_rolls_back_to_previous_trade_date(self, mock_get_cn_trade_dates):
        mock_get_cn_trade_dates.return_value = [
            "2026-03-25",
            "2026-03-26",
            "2026-03-27",
        ]

        original_date, effective_date = analyze.resolve_analysis_date(
            tickers=["000001"],
            requested_date="2026-03-29",
            date_was_explicit=False,
        )

        self.assertEqual("2026-03-29", original_date)
        self.assertEqual("2026-03-27", effective_date)

    def test_default_us_weekend_rolls_back_to_previous_weekday(self):
        original_date, effective_date = analyze.resolve_analysis_date(
            tickers=["AAPL"],
            requested_date="2026-03-29",
            date_was_explicit=False,
        )

        self.assertEqual("2026-03-29", original_date)
        self.assertEqual("2026-03-27", effective_date)


class PrintHeaderTests(unittest.TestCase):
    def test_header_shows_original_and_effective_date(self):
        output = io.StringIO()
        original_console = analyze.console
        analyze.console = Console(file=output, force_terminal=False, color_system=None)

        try:
            args = Namespace(
                tickers=["000001"],
                level=2,
                date="2026-03-27",
                original_date="2026-03-29",
                workers=1,
                provider="custom",
                quick_model="gpt-5.4",
            )
            intensity = analyze.INTENSITY_PROFILES[2]

            analyze.print_header(args, intensity)
        finally:
            analyze.console = original_console

        rendered = output.getvalue()
        self.assertIn("2026-03-29 -> 2026-03-27", rendered)


if __name__ == "__main__":
    unittest.main()
