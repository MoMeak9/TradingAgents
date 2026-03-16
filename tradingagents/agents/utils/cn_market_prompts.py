"""Chinese A-share market prompt suffixes for agent localization."""

CN_MARKET_RULES = """
## A 股市场规则 (你必须在分析中考虑这些规则)

### 交易制度
- **T+1 交易**: 当日买入的股票，次日方可卖出。这意味着短线操作受限，需考虑隔夜风险。
- **涨跌停限制**:
  - 主板 (沪市/深市主板): ±10%
  - 创业板 (300xxx): ±20%
  - 科创板 (688xxx): ±20%
  - ST 股票: ±5%
- **交易时间**: 9:30-11:30, 13:00-15:00 (UTC+8)，含 1.5 小时午休
- **集合竞价**: 9:15-9:25 (开盘), 14:57-15:00 (收盘)
- **最小交易单位**: 100 股 (1手)

### 市场特征
- **散户主导**: A 股散户投资者占比高，市场情绪波动较大
- **政策敏感**: 政府政策（如降准降息、行业监管）对市场影响显著
- **板块轮动**: A 股存在明显的板块轮动现象
- **无做空机制**: 普通投资者无法直接做空（融券除外）

### 货币
- **计价货币**: 人民币 (CNY)
- 所有价格和财务数据均以人民币计价
"""

CN_ANALYST_SUFFIX = """
## 重要指令
- 请使用**中文**进行分析和输出报告
- 你正在分析的是**中国 A 股**上市公司
- 分析中必须考虑 A 股特有的交易规则 (涨跌停、T+1 等)
- 所有金额单位为**人民币 (CNY)**
- 新闻和舆情数据来源为中国财经媒体

""" + CN_MARKET_RULES

CN_RESEARCHER_SUFFIX = """
## 重要指令
- 请使用**中文**进行辩论和分析
- 你正在辩论的是**中国 A 股**上市公司的投资价值
- 请考虑 A 股特有的市场特征 (散户主导、政策敏感、板块轮动等)
- 请考虑 T+1 交易制度对短期策略的影响
- 涨跌停板制度意味着极端行情下可能无法及时止损

""" + CN_MARKET_RULES

CN_TRADER_SUFFIX = """
## 重要指令
- 请使用**中文**提供交易建议
- 你正在为**中国 A 股**股票提供交易方案
- **必须考虑**:
  - T+1 制度: 建议买入后至少持有至次日
  - 涨跌停: 追涨停板风险极高，跌停板可能无法卖出
  - 最小交易单位: 100 股 (1手)
  - 所有金额和收益以人民币 (CNY) 计
- 最终交易建议格式: "最终交易建议: **买入/持有/卖出**"

""" + CN_MARKET_RULES

CN_RISK_SUFFIX = """
## 重要指令
- 请使用**中文**进行风险分析
- 你正在评估**中国 A 股**股票的风险
- 特别关注:
  - 涨跌停风险: 连续跌停可能导致无法及时出场
  - 政策风险: 行业监管政策变化
  - 流动性风险: 小盘股流动性不足
  - 汇率风险 (如果涉及外资持仓)
  - T+1 制度下的隔夜风险

""" + CN_MARKET_RULES

# Role to suffix mapping
_ROLE_SUFFIX_MAP = {
    "analyst": CN_ANALYST_SUFFIX,
    "researcher": CN_RESEARCHER_SUFFIX,
    "trader": CN_TRADER_SUFFIX,
    "risk": CN_RISK_SUFFIX,
}


def get_prompt_suffix(market: str, role: str) -> str:
    """
    Get the prompt suffix for a given market and role.

    Args:
        market: "cn" or "us"
        role: "analyst", "researcher", "trader", or "risk"

    Returns:
        Prompt suffix string. Empty string for non-CN markets.
    """
    if market != "cn":
        return ""
    return _ROLE_SUFFIX_MAP.get(role, "")
