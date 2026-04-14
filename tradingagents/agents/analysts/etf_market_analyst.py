from datetime import datetime, timedelta

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.etf_data_tools import (
    get_etf_indicators,
    get_etf_price_data,
)
from tradingagents.agents.utils.etf_prompt_utils import (
    ETF_MARKET_INDICATORS,
    build_etf_report_header,
)


def _history_start_date(current_date: str, lookback_days: int = 180) -> str:
    dt = datetime.strptime(current_date, "%Y-%m-%d")
    return (dt - timedelta(days=lookback_days)).strftime("%Y-%m-%d")


def _build_etf_market_tool_calls(
    ticker: str,
    current_date: str,
    existing_tool_calls: list[dict] | None,
) -> list[dict]:
    existing_tool_calls = existing_tool_calls or []
    planned_calls = []
    history_start = _history_start_date(current_date)
    has_history_price = False
    requested_indicators = set()

    for call in existing_tool_calls:
        if call.get("name") == "get_etf_price_data":
            args = call.get("args", {})
            if args.get("start_date", "") <= history_start and args.get("end_date") == current_date:
                has_history_price = True
        elif call.get("name") == "get_etf_indicators":
            indicator = str(call.get("args", {}).get("indicator", "")).strip()
            if indicator:
                requested_indicators.add(indicator)

    if not has_history_price:
        planned_calls.append(
            {
                "name": "get_etf_price_data",
                "args": {
                    "symbol": ticker,
                    "start_date": history_start,
                    "end_date": current_date,
                },
            }
        )

    for indicator in ETF_MARKET_INDICATORS:
        if indicator not in requested_indicators:
            planned_calls.append(
                {
                    "name": "get_etf_indicators",
                    "args": {
                        "symbol": ticker,
                        "indicator": indicator,
                        "curr_date": current_date,
                        "look_back_days": 60,
                    },
                }
            )

    return planned_calls


def create_etf_market_analyst(llm, toolkit=None):
    def etf_market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        tools = [get_etf_price_data, get_etf_indicators]

        system_message = (
            f"{build_etf_report_header('ETF 市场分析', ticker)}\n"
            "你是 ETF 行情与技术分析师。必须先获取 ETF 历史行情和关键技术指标，"
            "再输出交易视角与配置视角的分析结论。"
        )
        prompt = ChatPromptTemplate.from_messages(
            [("system", "{system_message} 当前日期：{current_date}。"), MessagesPlaceholder(variable_name="messages")]
        ).partial(system_message=system_message, current_date=current_date)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke({"messages": state["messages"]})
        report = result.content if not getattr(result, "tool_calls", None) else ""
        return {"messages": [result], "etf_market_report": report, "market_report": report}

    return etf_market_analyst_node
