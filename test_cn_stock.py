"""Test A-share analysis with MiniMax API for stock 000001 (平安银行).

启用多Agent深度分析：
- 多轮投资辩论（Bull vs Bear 研究员进行3轮辩论）
- 多轮风险讨论（激进/保守/中立风控经理进行3轮讨论）
- 全部4类分析师参与（市场、社交媒体、新闻、基本面）
"""

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create config for MiniMax + A-share with deep multi-agent analysis
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "minimax"
config["deep_think_llm"] = "abab6.5s-chat"
config["quick_think_llm"] = "abab6.5s-chat"
config["backend_url"] = "https://api.minimaxi.com/v1"
config["max_debate_rounds"] = 3          # Bull vs Bear 多轮深度辩论
config["max_risk_discuss_rounds"] = 3    # 风险管理多轮深度讨论
config["max_recur_limit"] = 200          # 提高递归上限以支持多轮分析

# Initialize with all 4 analyst types for comprehensive analysis
print("=" * 60)
print("A 股深度分析: 000001 (平安银行) + MiniMax API")
print("多Agent模式: 3轮投资辩论 + 3轮风险讨论")
print("分析师: 市场 / 社交媒体 / 新闻 / 基本面")
print("=" * 60)

ta = TradingAgentsGraph(
    selected_analysts=["market", "social", "news", "fundamentals"],
    debug=True,
    config=config,
)

# Run A-share deep analysis
_, decision = ta.propagate("000001", "2025-03-14")

print("\n" + "=" * 60)
print(f"最终交易决策: {decision}")
print("=" * 60)
