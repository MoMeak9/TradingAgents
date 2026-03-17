# 设计方案：TradingAgents-CN 工作流集成

## 1. 集成总览

**方向**：上游合并（Upstream Merge）
**来源**：TradingAgents-CN (`tradingagents/`)
**目标**：TradingAgents (`tradingagents/`)
**原则**：保持原有模块化架构风格，最小化破坏性变更

### 变更范围

| 类别 | 涉及文件 | 变更类型 |
|------|---------|---------|
| Agent 提示词增强 | 10 个 Agent 文件 | 重写（用 CN 版本替换） |
| 新增 Agent | china_market_analyst.py | 新建 |
| 新增数据源 | baostock.py, hk_stock.py, improved_hk.py | 新建 |
| 市场路由层 | market_router.py | 新建 |
| 工具文件增强 | 4 个现有工具文件 | 编辑（接入路由层） |
| 信号处理 | signal_processing.py | 重写（用 CN 版本替换） |
| 反思模块 | reflection.py | 重写（用 CN 版本替换） |
| 图构建 | setup.py, conditional_logic.py | 编辑 |
| 配置 | default_config.py | 编辑 |
| Google 处理器 | google_tool_handler.py | 新建 |
| Agent 工具 | agent_utils.py | 编辑（扩展 Toolkit） |
| 入口导出 | agents/__init__.py | 编辑 |

---

## 2. 文件级变更清单

### 2.1 Agent 提示词增强（分布式嵌入，中文）

以下文件用 CN 版本**整体替换**，但需做适配修改：

#### 2.1.1 `agents/analysts/market_analyst.py`
- **来源**：CN 版 507 行
- **变更**：
  - 替换为 CN 版本的 `create_market_analyst()` 实现
  - 嵌入中文系统提示词（含详细指标分类：SMA/MACD/RSI/ATR/VWMA/布林带）
  - 引入多市场公司名解析 `_get_company_name()`（A股/港股/美股 fallback 链）
  - 保留工具调用计数器（max 3 calls）防死循环
  - 引入 `GoogleToolCallHandler` 集成
- **适配**：
  - 删除 CN 版中的 `@log_analyst_module` 装饰器和日志/metrics 相关代码
  - 工具函数改为从现有工具文件导入（而非 CN 的 `Toolkit` 类方法）
  - 签名保持 `create_market_analyst(llm, toolkit)` 其中 toolkit 为新建的轻量路由对象

#### 2.1.2 `agents/analysts/fundamentals_analyst.py`
- **来源**：CN 版 689 行
- **变更**：
  - 双层提示词体系（`system_prompt` + `system_message`）
  - `🔴强制要求` / `🚫绝对禁止` 执行标记
  - 10 天数据窗口处理周末/节假日
  - DashScope/DeepSeek/Zhipu 模型预抓取 fallback
  - Force mode：当工具已执行但 LLM 未生成报告时强制生成
- **适配**：同 2.1.1，删除日志装饰器，工具从独立文件导入

#### 2.1.3 `agents/analysts/news_analyst.py`
- **来源**：CN 版 410 行
- **变更**：
  - 多阶段提示词（主提示 + 分析提示 + 回退提示）
  - 情绪量化表格输出
  - DashScope/DeepSeek/Zhipu 预抓取模式（绕过 tool calling 问题）
  - 清洁 AIMessage 返回（无 tool_calls 属性，防死循环）
- **适配**：同上

#### 2.1.4 `agents/analysts/social_media_analyst.py`
- **来源**：CN 版 232 行
- **变更**：
  - 中国平台特化（雪球、东方财富股吧、新浪微博）
  - 情绪量化评分（1-10 分）
  - KOL 分析、散户 vs 机构情绪分化
- **适配**：同上

#### 2.1.5 `agents/researchers/bull_researcher.py`
- **来源**：CN 版 146 行
- **变更**：
  - f-string 动态构建提示词，注入 4 份分析报告 + 辩论历史 + 过往记忆
  - 多市场货币感知（¥/$）
  - 公司名优先于股票代码的表述要求
- **适配**：删除日志代码

#### 2.1.6 `agents/researchers/bear_researcher.py`
- **来源**：CN 版 137 行
- **变更**：与看涨研究员对称的看跌增强
- **适配**：同上

#### 2.1.7 `agents/risk_mgmt/aggressive_debator.py`
- **来源**：CN 版 `aggresive_debator.py` 84 行
- **变更**：
  - 中文激进风控提示词
  - 输入数据长度统计（字符数 → 预估 token）
  - 保持原文件名 `aggressive_debator.py`（不改拼写）
- **适配**：CN 版拼写为 `aggresive`，合并时映射回原版 `aggressive` 文件名

#### 2.1.8 `agents/risk_mgmt/conservative_debator.py`
- **来源**：CN 版 86 行
- **变更**：中文保守风控提示词

#### 2.1.9 `agents/risk_mgmt/neutral_debator.py`
- **来源**：CN 版 88 行
- **变更**：中文中性风控提示词

#### 2.1.10 `agents/trader/trader.py`
- **来源**：CN 版 117 行
- **变更**：
  - 强制目标价（不允许 null/空）
  - 货币单位要求（¥/$ 自适应）
  - 置信度和风险评分
  - 止损价位要求

#### 2.1.11 `agents/managers/research_manager.py`
- **来源**：CN 版 108 行
- **变更**：
  - 三情景目标价分析（保守/基准/乐观）
  - 多时间跨度（1/3/6 个月）
  - 中文投资计划格式

#### 2.1.12 `agents/managers/risk_manager.py`
- **来源**：CN 版 163 行
- **变更**：
  - 重试机制（3 次，2 秒间隔）
  - 默认建议 fallback
  - 中文风险评估格式

---

### 2.2 新增文件

#### 2.2.1 `agents/analysts/china_market_analyst.py` (新建)
- **来源**：CN 版 292 行
- **内容**：
  - `create_china_market_analyst(llm, toolkit)` 工厂函数
  - A 股专属分析师，含 T+1、涨跌停、板块轮动等中国特色分析
  - `create_china_stock_screener()` 选股功能
  - 工具：`get_china_stock_data`, `get_china_market_overview`
- **适配**：
  - 删除日志装饰器
  - 工具从现有工具文件 + market_router 导入

#### 2.2.2 `agents/utils/google_tool_handler.py` (新建)
- **来源**：CN 版 751 行
- **内容**：
  - `GoogleToolCallHandler` 类
  - `is_google_model()` 模型检测
  - `handle_google_tool_calls()` 工具调用处理
  - `_validate_tool_call()` / `_fix_tool_call()` 格式修复
  - `create_analysis_prompt()` 标准提示词模板生成
  - `generate_final_analysis_report()` 多重试报告生成
- **适配**：删除日志相关导入

#### 2.2.3 `agents/utils/market_router.py` (新建 — 原创设计)

这是**本次集成的核心新建文件**，作为轻量级路由/协调层：

```python
"""
市场路由器 - 轻量级市场检测和数据源选择协调层

职责：
1. 市场类型检测（A股/港股/美股）
2. 公司名解析（多数据源 fallback）
3. 货币信息获取
4. 数据源路由建议
"""

class MarketRouter:
    """轻量级市场路由器，不持有数据源实例"""

    def detect_market(self, ticker: str) -> dict:
        """
        检测股票所属市场
        Returns: {
            'market': 'china' | 'hk' | 'us',
            'market_name': '中国A股' | '香港市场' | '美国市场',
            'currency': 'CNY' | 'HKD' | 'USD',
            'currency_symbol': '¥' | 'HK$' | '$',
            'is_china': bool,
            'is_hk': bool,
            'is_us': bool
        }
        """

    def get_company_name(self, ticker: str, market: str = None) -> str:
        """
        多源 fallback 公司名解析
        A股: tushare → akshare → ticker
        港股: improved_hk mapping → akshare → yfinance → ticker
        美股: yfinance → ticker
        """

    def get_data_source_for_market(self, ticker: str, category: str) -> str:
        """
        根据市场和类别返回推荐数据源名称
        category: 'core_stock_apis' | 'technical_indicators' | 'fundamental_data' | 'news_data'
        """
```

**设计要点**：
- 不引入 CN 版的 1379 行 `Toolkit` 单体
- 仅提供路由/检测功能，不持有数据源实例
- 各工具文件（`core_stock_tools.py` 等）调用 `MarketRouter` 做市场感知
- 从 CN 版 `agent_utils.py` 中提取市场检测和公司名解析逻辑

#### 2.2.4 `dataflows/baostock_stock.py` (新建)
- **来源**：CN 版 `providers/china/baostock.py` 902 行
- **适配**：
  - **不继承 `BaseStockDataProvider`**（原版无此基类）
  - 转为**同步函数式接口**，匹配原版风格：
    ```python
    def get_stock_data(symbol: str, start_date: str, end_date: str) -> str:
        """返回 CSV 格式字符串，与原版 tushare_stock.py 接口一致"""

    def get_financial_data(symbol: str, year: int = None, quarter: int = None) -> str:
        """返回格式化财务数据字符串"""

    def get_valuation_data(symbol: str, trade_date: str = None) -> str:
        """返回 PE/PB/PS 估值数据"""
    ```
  - 内部使用 `baostock` SDK，但包装为同步调用
  - 保留 BaoStock 的 login/logout 管理
  - 保留 code 格式转换（`600519` → `sh.600519`）
  - 删除 async/await、日志装饰器、BaseStockDataProvider 继承

#### 2.2.5 `dataflows/hk_stock.py` (新建)
- **来源**：CN 版 `providers/hk/hk_stock.py` 517 行 + `providers/hk/improved_hk.py` 800 行
- **适配**：
  - 合并两个文件为单一模块
  - 同步函数式接口：
    ```python
    def get_hk_stock_data(symbol: str, start_date: str, end_date: str) -> str:
        """返回港股行情数据 CSV 字符串"""

    def get_hk_stock_info(symbol: str) -> str:
        """返回港股基本信息格式化字符串"""

    def get_hk_company_name(symbol: str) -> str:
        """多策略港股公司名解析（静态映射 → AKShare → YFinance）"""

    def get_hk_financial_indicators(symbol: str) -> str:
        """返回 EPS/ROE/ROA 等财务指标"""
    ```
  - 保留技术指标计算（MA5/10/20/60, RSI, MACD, 布林带）
  - 保留速率限制和重试逻辑
  - 保留公司名静态映射（100+ 港股）
  - 删除 async、BaseStockDataProvider、JSON 缓存系统

---

### 2.3 现有文件编辑

#### 2.3.1 `agents/utils/agent_utils.py`（编辑，37 行 → ~120 行）
- **当前**：仅 `create_msg_delete()` 函数（37 行）
- **变更**：
  - 新增 `MarketRouter` 实例化和导出
  - 新增 `create_unified_news_tool(toolkit)` 函数（从 CN 版提取）
  - 新增统一工具创建辅助函数，供各分析师使用
  - **不引入** CN 版的 1379 行 Toolkit 类
- **从 CN 版提取的功能**：
  - `get_stock_market_data_unified()` — 统一市场数据获取（自动路由 A股/港股/美股）
  - `get_stock_fundamentals_unified()` — 统一基本面数据获取
  - `get_stock_sentiment_unified()` — 统一情绪数据获取
  - 这些函数内部调用 `MarketRouter.detect_market()` 后委托给对应的工具文件

#### 2.3.2 `agents/utils/core_stock_tools.py`（编辑）
- **变更**：
  - 导入 `MarketRouter`
  - 在 `get_stock_data` 类工具中增加市场检测逻辑
  - A 股路由到 tushare/akshare/baostock
  - 港股路由到新建的 `hk_stock.py`
  - 美股保持原有 yfinance 逻辑
- **不变**：保持函数式接口，保持独立文件

#### 2.3.3 `agents/utils/technical_indicators_tools.py`（编辑）
- **变更**：增加市场检测，A 股/港股使用对应数据源的技术指标

#### 2.3.4 `agents/utils/fundamental_data_tools.py`（编辑）
- **变更**：增加市场检测，A 股路由到 tushare/baostock 基本面数据

#### 2.3.5 `agents/utils/news_data_tools.py`（编辑）
- **变更**：增加中国财经新闻源支持

#### 2.3.6 `agents/utils/cn_market_prompts.py`（删除）
- **原因**：提示词改为分布式嵌入各 Agent 文件，此文件不再需要
- **处理**：删除文件，移除所有引用

#### 2.3.7 `agents/__init__.py`（编辑）
- **变更**：
  - 新增导出：`create_china_market_analyst`, `MarketRouter`
  - 保持原有导出名称不变（`create_aggressive_debator` 不改名）

#### 2.3.8 `graph/setup.py`（编辑）
- **变更**：
  - 在 `GraphSetup.__init__` 中新增 `toolkit` 参数（`MarketRouter` 实例）
  - 在 `selected_analysts` 中支持 `"china_market"` 选项
  - 新增 `china_market_analyst` 节点注册
  - 新增 `tools_china_market` 工具节点
  - 新增条件边 `should_continue_china_market`
  - 传递 `toolkit` 给所有分析师工厂函数
  - DashScope/DeepSeek 模型检测逻辑（从 CN 版提取，用于决定是否预抓取）
- **不变**：风控节点名称保持 `Aggressive/Conservative/Neutral`（不改为 Risky/Safe）

#### 2.3.9 `graph/conditional_logic.py`（编辑，68 行 → ~180 行）
- **变更**：
  - 新增 `should_continue_china_market()` 方法
  - 为每个分析师增加**死循环防护**：
    - 工具调用计数器（market: 3, social: 3, news: 3, fundamentals: 1, china_market: 3）
    - 报告完成检测（report length > 100 chars → 跳过工具调用）
  - 保持原有方法签名不变
- **不引入**：CN 版的 emoji 日志

#### 2.3.10 `graph/signal_processing.py`（重写，32 行 → ~337 行）
- **来源**：CN 版完整移植
- **变更**：
  - 返回值从 `str` 改为 `dict`：
    ```python
    {
        'action': '买入|持有|卖出',
        'target_price': float,
        'confidence': float,  # 0-1
        'risk_score': float,  # 0-1
        'reasoning': str
    }
    ```
  - 15+ regex 模式提取目标价（中文金融术语）
  - `_smart_price_estimation()` 智能价格估算
  - `_extract_simple_decision()` JSON 解析失败时的文本回退
  - `_get_default_decision()` 安全默认值
  - 多货币支持（¥/$）
- **适配**：删除 `@log_graph_module` 装饰器
- **兼容性处理**：在 `trading_graph.py` 中更新 `propagate()` 的返回值处理

#### 2.3.11 `graph/reflection.py`（重写，~100 行 → ~126 行）
- **来源**：CN 版
- **变更**：
  - 8 维因素权重分析（技术/情绪/新闻/基本面等）
  - 结构化改进建议
  - 压缩洞察（≤1000 tokens）
- **适配**：删除日志装饰器

#### 2.3.12 `graph/trading_graph.py`（编辑）
- **变更**：
  - `__init__` 中创建 `MarketRouter` 实例并传递给 `GraphSetup`
  - `propagate()` 返回值适配新的 signal_processing dict 格式
  - 新增 DashScope/DeepSeek 模型检测辅助函数（从 CN 版提取，精简版）
  - 在 `_get_provider_kwargs()` 中增加 DashScope/DeepSeek 特殊参数处理
- **不变**：保持 `create_llm_client()` 工厂模式（不引入 CN 版的 150 行 `create_llm_by_provider`）

#### 2.3.13 `graph/propagation.py`（编辑）
- **变更**：
  - 初始状态中新增 `china_market_report: str` 字段（如果 china_market 在 selected_analysts 中）
  - 新增 `china_market_tool_call_count: int` 字段

#### 2.3.14 `agents/utils/agent_states.py`（编辑）
- **变更**：
  - `AgentState` 新增 `china_market_report: str` 字段
  - `AgentState` 新增 `china_market_tool_call_count: int` 字段

#### 2.3.15 `default_config.py`（编辑）
- **变更**：
  - `cn_data_vendors` 新增 `baostock` 选项：
    ```python
    "cn_data_vendors": {
        "core_stock_apis": "tushare",      # tushare | akshare | baostock
        "technical_indicators": "tushare",  # tushare | akshare | baostock
        "fundamental_data": "tushare",      # tushare | akshare | baostock
        "news_data": "akshare",
    },
    ```
  - 新增港股数据源配置：
    ```python
    "hk_data_vendors": {
        "core_stock_apis": "yfinance",     # yfinance
        "fundamental_data": "yfinance",    # yfinance | akshare
    },
    ```

#### 2.3.16 `dataflows/interface.py`（编辑）
- **变更**：
  - 在 vendor 路由中新增 `baostock` 分支
  - 在市场检测中新增港股路由到 `hk_stock.py`
  - `VENDOR_METHODS` 新增 baostock 和 hk 条目
- **不变**：保持硬编码路由模式（不引入 CN 版的数据库驱动配置）

#### 2.3.17 `dataflows/config.py`（编辑）
- **变更**：新增 baostock 和 hk 相关配置项

---

## 3. 架构设计图

### 3.1 变更后的文件结构

```
tradingagents/
├── agents/
│   ├── analysts/
│   │   ├── market_analyst.py          [重写] 163→507行 中文提示词
│   │   ├── news_analyst.py            [重写] 93→410行 多阶段提示词
│   │   ├── social_media_analyst.py    [重写] 97→232行 中国平台特化
│   │   ├── fundamentals_analyst.py    [重写] 123→689行 双层提示词
│   │   └── china_market_analyst.py    [新建] 292行 A股专属分析师
│   ├── managers/
│   │   ├── research_manager.py        [重写] 三情景目标价
│   │   └── risk_manager.py            [重写] 重试+fallback
│   ├── researchers/
│   │   ├── bull_researcher.py         [重写] 多市场货币感知
│   │   └── bear_researcher.py         [重写] 对称增强
│   ├── risk_mgmt/
│   │   ├── aggressive_debator.py      [重写] 中文提示词
│   │   ├── conservative_debator.py    [重写] 中文提示词
│   │   └── neutral_debator.py         [重写] 中文提示词
│   ├── trader/
│   │   └── trader.py                  [重写] 强制目标价+货币
│   └── utils/
│       ├── agent_states.py            [编辑] +china_market 字段
│       ├── agent_utils.py             [编辑] +统一工具函数
│       ├── market_router.py           [新建] 轻量级市场路由
│       ├── google_tool_handler.py     [新建] Google 模型处理
│       ├── core_stock_tools.py        [编辑] +市场检测路由
│       ├── technical_indicators_tools.py [编辑] +市场检测
│       ├── fundamental_data_tools.py  [编辑] +市场检测
│       ├── news_data_tools.py         [编辑] +中国新闻源
│       ├── cn_market_prompts.py       [删除]
│       └── memory.py                  (不变)
├── dataflows/
│   ├── interface.py                   [编辑] +baostock/hk 路由
│   ├── config.py                      [编辑] +新配置项
│   ├── market_utils.py                (不变)
│   ├── tushare_stock.py               (不变)
│   ├── akshare_stock.py               (不变)
│   ├── akshare_news.py                (不变)
│   ├── y_finance.py                   (不变)
│   ├── baostock_stock.py              [新建] BaoStock 数据源
│   ├── hk_stock.py                    [新建] 港股数据源
│   └── ...其余文件不变
├── graph/
│   ├── trading_graph.py               [编辑] +MarketRouter+信号处理适配
│   ├── setup.py                       [编辑] +china_market 节点+toolkit
│   ├── conditional_logic.py           [编辑] +死循环防护+新方法
│   ├── propagation.py                 [编辑] +china_market 状态
│   ├── signal_processing.py           [重写] 结构化决策输出
│   └── reflection.py                  [重写] 8维因素分析
├── llm_clients/                       (不变)
│   └── ...
└── default_config.py                  [编辑] +baostock/hk 配置
```

### 3.2 数据流设计

```
用户调用: ta.propagate("000001.SZ", "2024-01-15")
    │
    ▼
TradingAgentsGraph.__init__
    ├── create_llm_client() [不变]
    ├── MarketRouter() [新建]
    └── GraphSetup(llm, toolkit=market_router, ...) [编辑]
            │
            ▼
    LangGraph 节点注册:
    ┌─────────────────────────────────────────────────┐
    │ Phase 1: 数据采集                                │
    │                                                  │
    │  Market Analyst ──┐                              │
    │  Fundamentals  ───┤  (根据 selected_analysts)    │
    │  News Analyst  ───┤                              │
    │  Social Media  ───┤                              │
    │  China Market  ───┘  [新增可选]                   │
    │                                                  │
    │  每个分析师:                                      │
    │  1. 调用 MarketRouter.detect_market()             │
    │  2. 路由到对应工具文件的函数                        │
    │  3. 工具计数器防死循环 (max 1-3)                   │
    │  4. 报告完成检测 (>100 chars)                     │
    └─────────────────────────────────────────────────┘
            │
            ▼
    ┌─────────────────────────────────────────────────┐
    │ Phase 2: 投资辩论                                │
    │  Bull Researcher ↔ Bear Researcher               │
    │  → Research Manager (三情景目标价)                 │
    │  → Trader (强制目标价+货币)                        │
    └─────────────────────────────────────────────────┘
            │
            ▼
    ┌─────────────────────────────────────────────────┐
    │ Phase 3: 风险评估                                │
    │  Aggressive ↔ Conservative ↔ Neutral             │
    │  → Risk Judge                                    │
    └─────────────────────────────────────────────────┘
            │
            ▼
    SignalProcessor.process_signal() [重写]
    返回: {action, target_price, confidence, risk_score, reasoning}
```

### 3.3 MarketRouter 与工具文件协作

```
                    ┌──────────────────┐
                    │  MarketRouter    │
                    │                  │
                    │  detect_market() │
                    │  get_company()   │
                    │  get_source()    │
                    └────────┬─────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
  core_stock_tools.py  fundamental_data_  news_data_tools.py
  (路由到对应市场)      tools.py           (增加中国源)
            │                │                │
    ┌───────┼───────┐  ┌────┼────┐      ┌────┼────┐
    ▼       ▼       ▼  ▼    ▼    ▼      ▼         ▼
 tushare akshare baostock              akshare   yfinance
 _stock  _stock  _stock  [新]          _news     _news
    │       │       │                     │         │
    ▼       ▼       ▼                     ▼         ▼
 hk_stock.py [新]                    (中国财经新闻)
 y_finance.py
```

---

## 4. 关键设计决策

### D1: 拼写统一
- **决策**：保持原版 `aggressive_debator.py` 文件名
- **原因**：避免破坏现有用户代码
- **处理**：从 CN 版 `aggresive_debator.py` 复制内容到原版 `aggressive_debator.py`

### D2: 节点命名统一
- **决策**：保持原版 `Aggressive Analyst / Conservative Analyst / Neutral Analyst` 节点名
- **原因**：CN 版改为 `Risky/Safe/Neutral`，但这会破坏现有 graph 依赖
- **处理**：仅复制提示词内容，不改节点名和函数名

### D3: 信号处理兼容性
- **决策**：signal_processing 返回 dict（breaking change）
- **原因**：结构化输出是核心增强，无法用字符串表达
- **处理**：在 `trading_graph.py` 的 `propagate()` 中适配新返回格式

### D4: 数据源接口一致性
- **决策**：新数据源使用函数式接口，返回 CSV 字符串
- **原因**：匹配原版 tushare_stock.py / akshare_stock.py 风格
- **处理**：从 CN 版 class-based provider 提取核心逻辑，包装为函数

### D5: DashScope/DeepSeek 模型处理
- **决策**：在分析师节点中内置模型检测和预抓取逻辑
- **原因**：这些模型的 tool calling 不稳定，需要 fallback
- **处理**：
  - 在 `setup.py` 中检测当前 provider 是否为 DashScope/DeepSeek
  - 将检测结果传递给分析师工厂函数
  - 分析师根据标志决定是否使用预抓取模式

### D6: cn_market_prompts.py 移除策略
- **决策**：删除文件，将 `CN_MARKET_RULES` 内容融入各 Agent 提示词
- **处理**：
  - 搜索所有引用 `cn_market_prompts` 的文件
  - 将 T+1、涨跌停等规则直接嵌入对应分析师提示词
  - 从 `__init__.py` 和其他文件中移除导入

---

## 5. 实施顺序

建议按以下顺序分步实施，每步可独立验证：

### Step 1: 基础设施层（无破坏性变更）
1. 新建 `agents/utils/market_router.py`
2. 新建 `agents/utils/google_tool_handler.py`
3. 新建 `dataflows/baostock_stock.py`
4. 新建 `dataflows/hk_stock.py`
5. 编辑 `default_config.py` 新增配置项
6. 编辑 `dataflows/config.py` 新增配置
7. 编辑 `dataflows/interface.py` 新增路由

**验证**：现有功能不受影响，新数据源可独立调用

### Step 2: 状态和图结构扩展
1. 编辑 `agents/utils/agent_states.py` 新增字段
2. 编辑 `graph/propagation.py` 新增初始状态
3. 编辑 `graph/conditional_logic.py` 增加死循环防护 + 新方法
4. 编辑 `graph/setup.py` 注册 china_market 节点 + toolkit 参数
5. 新建 `agents/analysts/china_market_analyst.py`

**验证**：`selected_analysts=["market", "fundamentals"]` 仍正常工作

### Step 3: 工具文件增强
1. 编辑 `agents/utils/agent_utils.py` 新增统一工具函数
2. 编辑 `agents/utils/core_stock_tools.py` 接入路由
3. 编辑 `agents/utils/technical_indicators_tools.py`
4. 编辑 `agents/utils/fundamental_data_tools.py`
5. 编辑 `agents/utils/news_data_tools.py`

**验证**：工具函数可正确路由到 A 股/港股/美股数据源

### Step 4: Agent 提示词替换
1. 替换 4 个分析师文件
2. 替换 2 个研究员文件
3. 替换 3 个风控文件
4. 替换 trader.py
5. 替换 2 个 manager 文件
6. 删除 `cn_market_prompts.py`
7. 编辑 `agents/__init__.py` 更新导出

**验证**：`propagate("AAPL", "2024-01-15")` 可生成中文分析报告

### Step 5: 信号处理和反思增强
1. 重写 `graph/signal_processing.py`
2. 重写 `graph/reflection.py`
3. 编辑 `graph/trading_graph.py` 适配新返回格式

**验证**：`propagate()` 返回结构化决策 dict

### Step 6: 清理和文档
1. 移除所有对 `cn_market_prompts` 的残留引用
2. 更新 `requirements.txt` 新增 `baostock` 依赖
3. 更新 README 说明新功能
4. 编写基本测试

---

## 6. 依赖变更

### 新增 Python 包
```
baostock>=0.8.8    # BaoStock A股历史数据
```

### 已有依赖（无需新增）
```
akshare            # 已在 requirements.txt，港股/A股新功能复用
yfinance           # 已在 requirements.txt，港股数据复用
```

### 不引入的依赖
```
motor, pymongo     # MongoDB（不引入数据库层）
redis              # Redis（不引入缓存层）
fastapi, uvicorn   # 后端框架（不引入）
```

---

## 7. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| signal_processing 返回值类型变更 | 依赖旧 str 返回的代码会崩溃 | 在 CHANGELOG 中标注 breaking change；propagate() 内部适配 |
| 中文提示词对英文 LLM 效果 | 非中文 LLM 可能理解有偏差 | 提示词保持关键术语中英对照 |
| BaoStock SDK 稳定性 | login/logout 管理复杂 | 包装为 context manager，确保清理 |
| DashScope 预抓取模式 | 可能与新版本 SDK 不兼容 | 作为 fallback，非默认路径 |
| cn_market_prompts.py 删除 | 第三方如有引用会崩溃 | 发布版本号标注为 minor breaking |
