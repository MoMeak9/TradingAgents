from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.etf_data_tools import get_etf_fund_flow
from tradingagents.agents.utils.etf_prompt_utils import build_etf_flow_prompt
from tradingagents.agents.utils.agent_states import apply_asset_report_mapping


def create_etf_flow_analyst(llm, toolkit=None):
    def etf_flow_analyst_node(state):
        ticker = state["company_of_interest"]
        current_date = state["trade_date"]
        tools = [get_etf_fund_flow]

        prompt = ChatPromptTemplate.from_messages(
            [("system", "{system_message} 当前日期：{current_date}。"), MessagesPlaceholder(variable_name="messages")]
        ).partial(
            system_message=build_etf_flow_prompt(ticker),
            current_date=current_date,
        )

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke({"messages": state["messages"]})
        report = result.content if not getattr(result, "tool_calls", None) else ""
        update = {
            "messages": [result],
            "etf_flow_report": report,
            "flow_tool_call_count": state.get("flow_tool_call_count", 0) + 1,
        }
        return apply_asset_report_mapping(update, "etf")

    return etf_flow_analyst_node
