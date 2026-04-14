import importlib
import unittest
from unittest.mock import patch

import tradingagents.dataflows.config as config_module
import tradingagents.dataflows.interface as interface
import tradingagents.dataflows.market_utils as market_utils


class ETFDataflowRoutingTests(unittest.TestCase):
    def setUp(self):
        importlib.reload(config_module)
        importlib.reload(market_utils)
        importlib.reload(interface)

    def test_market_info_marks_supported_cn_etf(self):
        info = market_utils.get_market_info("510300")

        self.assertEqual("cn", info["market"])
        self.assertTrue(info["is_etf"])
        self.assertEqual("510300.SH", info["symbol_display"])

    def test_explicit_etf_asset_type_routes_to_etf_vendor(self):
        calls = []

        def fake_etf_profile(symbol):
            calls.append(symbol)
            return f"etf:{symbol}"

        config_module.set_config(
            {"etf_data_vendors": {"etf_product_data": "tushare"}}
        )
        config_module.set_asset_context("etf")

        with patch.dict(
            interface.ETF_VENDOR_METHODS,
            {"get_etf_profile": {"tushare": fake_etf_profile}},
            clear=False,
        ):
            result = interface.route_to_vendor("get_etf_profile", "510300")

        self.assertEqual("etf:510300", result)
        self.assertEqual(["510300"], calls)

    def test_stock_mode_keeps_existing_cn_stock_route(self):
        calls = []

        def fake_stock_data(symbol, start_date, end_date):
            calls.append((symbol, start_date, end_date))
            return f"stock:{symbol}"

        config_module.set_config(
            {"cn_data_vendors": {"core_stock_apis": "tushare"}}
        )
        config_module.set_asset_context("stock")

        with patch.dict(
            interface.VENDOR_METHODS,
            {"get_stock_data": {"tushare": fake_stock_data}},
            clear=False,
        ):
            result = interface.route_to_vendor(
                "get_stock_data",
                "510300",
                "2025-01-01",
                "2025-01-02",
            )

        self.assertEqual("stock:510300", result)
        self.assertEqual(
            [("510300", "2025-01-01", "2025-01-02")],
            calls,
        )

    def test_etf_mode_rejects_non_etf_cn_symbol(self):
        config_module.set_asset_context("etf")

        result = interface.route_to_vendor("get_etf_profile", "600519")

        self.assertIn("currently supports only A-share exchange-traded ETFs", result)


if __name__ == "__main__":
    unittest.main()
