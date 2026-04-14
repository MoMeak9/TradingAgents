import importlib
import unittest

import tradingagents.default_config as default_config
import tradingagents.dataflows.config as config_module


class ETFConfigTests(unittest.TestCase):
    def setUp(self):
        importlib.reload(default_config)
        importlib.reload(config_module)

    def test_default_config_keeps_stock_asset_type(self):
        self.assertEqual("stock", default_config.DEFAULT_CONFIG["asset_type"])
        self.assertEqual("hybrid", default_config.DEFAULT_CONFIG["etf_analysis_mode"])
        self.assertIn("selected_etf_analysts", default_config.DEFAULT_CONFIG)
        self.assertIn("etf_data_vendors", default_config.DEFAULT_CONFIG)
        self.assertIn("etf_tool_vendors", default_config.DEFAULT_CONFIG)

    def test_config_accepts_etf_asset_type(self):
        config_module.set_config({"asset_type": "etf"})
        config = config_module.get_config()

        self.assertEqual("etf", config["asset_type"])

    def test_asset_context_does_not_overwrite_market_context(self):
        config_module.set_market_context("cn")
        config_module.set_asset_context("etf")

        self.assertEqual("cn", config_module.get_market_context())
        self.assertEqual("etf", config_module.get_asset_context())


if __name__ == "__main__":
    unittest.main()
