import tempfile
import unittest
from pathlib import Path

from tradingagents.graph.trading_graph import TradingAgentsGraph


class ReportGenerationTests(unittest.TestCase):
    def test_generate_report_avoids_duplicate_final_decision_when_same_as_risk_judge(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            graph = TradingAgentsGraph.__new__(TradingAgentsGraph)
            graph.config = {"project_dir": tmpdir}
            graph.ticker = "000001"

            duplicated_decision = "## 裁决：**卖出**\n\n执行建议。"
            final_state = {
                "company_of_interest": "000001",
                "market_report": "市场报告",
                "fundamentals_report": "",
                "news_report": "",
                "sentiment_report": "",
                "china_market_report": "",
                "investment_debate_state": {},
                "trader_investment_plan": "",
                "risk_debate_state": {
                    "aggressive_history": "",
                    "conservative_history": "",
                    "neutral_history": "",
                    "judge_decision": duplicated_decision,
                },
                "final_trade_decision": duplicated_decision,
            }
            decision = {
                "action": "卖出",
                "target_price": "10.64",
                "confidence": 0.9,
                "risk_score": 0.8,
                "reasoning": "测试原因",
            }

            graph._generate_report("2025-03-27", final_state, decision)

            report_path = Path(tmpdir) / "docs" / "reports" / "000001_2025-03-27_report.md"
            content = report_path.read_text(encoding="utf-8")

            self.assertEqual(1, content.count("## 裁决：**卖出**"))
            self.assertEqual(1, content.count("## 最终交易决策"))


if __name__ == "__main__":
    unittest.main()
