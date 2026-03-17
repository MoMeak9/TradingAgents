"""
测试脚本：使用股票 000001（平安银行）测试集成后的 TradingAgents
"""
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from dotenv import load_dotenv

load_dotenv()

# 配置使用 minimax provider（有可用的 API key）
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "minimax"
config["deep_think_llm"] = "MiniMax-M2.5"
config["quick_think_llm"] = "MiniMax-M2.5"
config["backend_url"] = "https://api.minimaxi.com/v1"
config["max_debate_rounds"] = 1
config["max_risk_discuss_rounds"] = 1

# A股数据源配置
config["cn_data_vendors"] = {
    "core_stock_apis": "tushare",
    "technical_indicators": "tushare",
    "fundamental_data": "tushare",
    "news_data": "akshare",
}

print("=" * 60)
print("TradingAgents 集成测试 - 000001 平安银行")
print("=" * 60)
print(f"LLM Provider: {config['llm_provider']}")
print(f"Model: {config['quick_think_llm']}")
print(f"CN Data Vendor: tushare")
print()

# 初始化
print("正在初始化 TradingAgentsGraph...")
ta = TradingAgentsGraph(
    selected_analysts=["market", "fundamentals"],
    debug=True,
    config=config,
)
print("初始化完成！")
print()

# 运行分析
print("开始分析 000001（平安银行）...")
print("-" * 60)

final_state, decision = ta.propagate("000001", "2025-03-17")

print()
print("=" * 60)
print("分析完成！决策结果：")
print("=" * 60)
print(f"  操作: {decision.get('action', 'N/A')}")
print(f"  目标价: {decision.get('target_price', 'N/A')}")
print(f"  置信度: {decision.get('confidence', 'N/A')}")
print(f"  风险评分: {decision.get('risk_score', 'N/A')}")
print(f"  理由: {decision.get('reasoning', 'N/A')[:200]}...")
print()
print("报告摘要：")
print(f"  市场报告长度: {len(final_state.get('market_report', ''))}")
print(f"  基本面报告长度: {len(final_state.get('fundamentals_report', ''))}")
print(f"  最终决策长度: {len(final_state.get('final_trade_decision', ''))}")
