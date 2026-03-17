"""
Fundamentals Analyst - Adapted from CN version
Uses tool files for data access instead of toolkit methods
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, ToolMessage
import logging

logger = logging.getLogger(__name__)

# Import Google tool call handler
from tradingagents.agents.utils.google_tool_handler import GoogleToolCallHandler

# Import market router utilities
from tradingagents.agents.utils.market_router import (
    get_company_name,
    get_market_info,
    needs_prefetch,
    is_dashscope_model,
    is_deepseek_model,
    is_zhipu_model,
)

# Import tool functions
from tradingagents.agents.utils.fundamental_data_tools import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
)


def create_fundamentals_analyst(llm, toolkit=None):
    def fundamentals_analyst_node(state):
        logger.debug(f"===== Fundamentals analyst node started =====")

        # Tool call counter - prevent infinite loops
        messages = state.get("messages", [])
        tool_message_count = sum(1 for msg in messages if isinstance(msg, ToolMessage))

        tool_call_count = state.get("fundamentals_tool_call_count", 0)
        max_tool_calls = 1

        if tool_message_count > tool_call_count:
            tool_call_count = tool_message_count
            logger.info(f"[Tool call count] Detected new tool results, updating counter: {tool_call_count}")

        logger.info(f"[Tool call count] Current: {tool_call_count}/{max_tool_calls}")

        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Date range for fundamentals: fixed 10 days
        from datetime import datetime, timedelta
        try:
            end_date_dt = datetime.strptime(current_date, "%Y-%m-%d")
            start_date_dt = end_date_dt - timedelta(days=10)
            start_date = start_date_dt.strftime("%Y-%m-%d")
            logger.info(f"[Fundamentals Analyst] Data range: {start_date} to {current_date} (fixed 10 days)")
        except Exception as e:
            logger.warning(f"[Fundamentals Analyst] Date parse failed, using default range: {e}")
            start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

        logger.debug(f"Input params: ticker={ticker}, date={current_date}")

        # Get market info
        market_info = get_market_info(ticker)
        logger.info(f"[Fundamentals Analyst] Analyzing stock: {ticker}")

        logger.debug(f"Stock type: {ticker} -> {market_info['market_name']} ({market_info['currency_name']})")

        # Get company name
        company_name = get_company_name(ticker)
        logger.debug(f"Company name: {ticker} -> {company_name}")

        # Use fundamental_data_tools
        logger.info(f"[Fundamentals Analyst] Using fundamental data tools")
        tools = [get_fundamentals, get_balance_sheet, get_cashflow, get_income_statement]

        # Get tool names for debug
        tool_names_debug = []
        for tool in tools:
            if hasattr(tool, 'name'):
                tool_names_debug.append(tool.name)
            elif hasattr(tool, '__name__'):
                tool_names_debug.append(tool.__name__)
            else:
                tool_names_debug.append(str(tool))
        logger.info(f"[Fundamentals Analyst] Bound tools: {tool_names_debug}")
        logger.info(f"[Fundamentals Analyst] Target market: {market_info['market_name']}")

        # System message
        system_message = (
            f"你是一位专业的股票基本面分析师。"
            f"⚠️ 绝对强制要求：你必须调用工具获取真实数据！不允许任何假设或编造！"
            f"任务：分析{company_name}（股票代码：{ticker}，{market_info['market_name']}）"
            f"🔴 立即调用 get_fundamentals 工具获取基本面数据"
            f"参数：ticker='{ticker}', curr_date='{current_date}'"
            "📊 分析要求："
            "- 基于真实数据进行深度基本面分析"
            f"- 计算并提供合理价位区间（使用{market_info['currency_name']}{market_info['currency_symbol']}）"
            "- 分析当前股价是否被低估或高估"
            "- 提供基于基本面的目标价位建议"
            "- 包含PE、PB、PEG等估值指标分析"
            "- 结合市场特点进行分析"
            "🌍 语言和货币要求："
            "- 所有分析内容必须使用中文"
            "- 投资建议必须使用中文：买入、持有、卖出"
            "- 绝对不允许使用英文：buy、hold、sell"
            f"- 货币单位使用：{market_info['currency_name']}（{market_info['currency_symbol']}）"
            "🚫 严格禁止："
            "- 不允许说'我将调用工具'"
            "- 不允许假设任何数据"
            "- 不允许编造公司信息"
            "- 不允许直接回答而不调用工具"
            "- 不允许回复'无法确定价位'或'需要更多信息'"
            "- 不允许使用英文投资建议（buy/hold/sell）"
            "✅ 你必须："
            "- 立即调用基本面分析工具"
            "- 等待工具返回真实数据"
            "- 基于真实数据进行分析"
            "- 提供具体的价位区间和目标价"
            "- 使用中文投资建议（买入/持有/卖出）"
            "现在立即开始调用工具！不要说任何其他话！"
        )

        # System prompt template
        system_prompt = (
            "🔴 强制要求：你必须调用工具获取真实数据！"
            "🚫 绝对禁止：不允许假设、编造或直接回答任何问题！"
            "✅ 工作流程："
            "1. 【第一次调用】如果消息历史中没有工具结果（ToolMessage），立即调用 get_fundamentals 工具"
            "2. 【收到数据后】如果消息历史中已经有工具结果（ToolMessage），🚨 绝对禁止再次调用工具！🚨"
            "3. 【生成报告】收到工具数据后，必须立即生成完整的基本面分析报告，包含："
            "   - 公司基本信息和财务数据分析"
            "   - PE、PB、PEG等估值指标分析"
            "   - 当前股价是否被低估或高估的判断"
            "   - 合理价位区间和目标价位建议"
            "   - 基于基本面的投资建议（买入/持有/卖出）"
            "4. 🚨 重要：工具只需调用一次！一次调用返回所有需要的数据！不要重复调用！🚨"
            "5. 🚨 如果你已经看到ToolMessage，说明工具已经返回数据，直接生成报告，不要再调用工具！🚨"
            "可用工具：{tool_names}。\n{system_message}"
            "当前日期：{current_date}。"
            "分析目标：{company_name}（股票代码：{ticker}）。"
            "请确保在分析中正确区分公司名称和股票代码。"
        )

        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ])

        prompt = prompt.partial(system_message=system_message)
        tool_names = []
        for tool in tools:
            if hasattr(tool, 'name'):
                tool_names.append(tool.name)
            elif hasattr(tool, '__name__'):
                tool_names.append(tool.__name__)
            else:
                tool_names.append(str(tool))

        prompt = prompt.partial(tool_names=", ".join(tool_names))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)
        prompt = prompt.partial(company_name=company_name)

        # DashScope model detection - create fresh instance
        fresh_llm = llm
        if is_dashscope_model(llm):
            logger.debug(f"Detected DashScope model, creating new instance to avoid tool cache")
            try:
                from tradingagents.llm_adapters import ChatDashScopeOpenAI
                original_base_url = getattr(llm, 'openai_api_base', None)
                original_api_key = getattr(llm, 'openai_api_key', None)

                fresh_llm = ChatDashScopeOpenAI(
                    model=llm.model_name,
                    api_key=original_api_key,
                    base_url=original_base_url if original_base_url else None,
                    temperature=llm.temperature,
                    max_tokens=getattr(llm, 'max_tokens', 2000)
                )
            except Exception as e:
                logger.warning(f"Failed to create fresh DashScope instance: {e}, using original")
                fresh_llm = llm

        logger.info(f"[Fundamentals Analyst] LLM type: {fresh_llm.__class__.__name__}")
        logger.info(f"[Fundamentals Analyst] LLM model: {getattr(fresh_llm, 'model_name', 'unknown')}")
        logger.info(f"[Fundamentals Analyst] Message history count: {len(state['messages'])}")

        try:
            chain = prompt | fresh_llm.bind_tools(tools)
            logger.info(f"[Fundamentals Analyst] Tool binding successful, bound {len(tools)} tools")
        except Exception as e:
            logger.error(f"[Fundamentals Analyst] Tool binding failed: {e}")
            raise e

        logger.info(f"[Fundamentals Analyst] Starting LLM call...")

        result = chain.invoke({"messages": state["messages"]})
        logger.info(f"[Fundamentals Analyst] LLM call complete")

        # Log result details
        logger.debug(f"[Fundamentals Analyst] Result type: {type(result).__name__}")
        if hasattr(result, 'content'):
            content_preview = str(result.content)[:200] if result.content else "None"
            logger.debug(f"[Fundamentals Analyst] Content preview: {content_preview}...")

        if hasattr(result, 'tool_calls'):
            logger.debug(f"[Fundamentals Analyst] tool_calls count: {len(result.tool_calls)}")

        # Use Google tool call handler for Google models
        if GoogleToolCallHandler.is_google_model(fresh_llm):
            logger.info(f"[Fundamentals Analyst] Google model detected, using unified tool call handler")

            analysis_prompt_template = GoogleToolCallHandler.create_analysis_prompt(
                ticker=ticker,
                company_name=company_name,
                analyst_type="基本面分析",
                specific_requirements="重点关注财务数据、盈利能力、估值指标、行业地位等基本面因素。"
            )

            report, messages = GoogleToolCallHandler.handle_google_tool_calls(
                result=result,
                llm=fresh_llm,
                tools=tools,
                state=state,
                analysis_prompt_template=analysis_prompt_template,
                analyst_name="基本面分析师"
            )

            return {"fundamentals_report": report}
        else:
            # Non-Google model processing
            logger.debug(f"Non-Google model ({fresh_llm.__class__.__name__}), using standard processing")

            current_tool_calls = len(result.tool_calls) if hasattr(result, 'tool_calls') else 0

            if current_tool_calls > 0:
                messages = state.get("messages", [])
                has_tool_result = any(isinstance(msg, ToolMessage) for msg in messages)

                if has_tool_result:
                    # Already have tool results, force report generation
                    logger.warning(f"[Force report] Tool already returned data, forcing report generation")

                    force_system_prompt = (
                        f"你是专业的股票基本面分析师。"
                        f"你已经收到了股票 {company_name}（代码：{ticker}）的基本面数据。"
                        f"🚨 现在你必须基于这些数据生成完整的基本面分析报告！🚨\n\n"
                        f"报告必须包含以下内容：\n"
                        f"1. 公司基本信息和财务数据分析\n"
                        f"2. PE、PB、PEG等估值指标分析\n"
                        f"3. 当前股价是否被低估或高估的判断\n"
                        f"4. 合理价位区间和目标价位建议\n"
                        f"5. 基于基本面的投资建议（买入/持有/卖出）\n\n"
                        f"要求：\n"
                        f"- 使用中文撰写报告\n"
                        f"- 基于消息历史中的真实数据进行分析\n"
                        f"- 分析要详细且专业\n"
                        f"- 投资建议必须明确（买入/持有/卖出）"
                    )

                    force_prompt = ChatPromptTemplate.from_messages([
                        ("system", force_system_prompt),
                        MessagesPlaceholder(variable_name="messages"),
                    ])

                    force_chain = force_prompt | fresh_llm
                    logger.info(f"[Force report] Re-invoking LLM with dedicated prompt...")
                    force_result = force_chain.invoke({"messages": messages})

                    report = str(force_result.content) if hasattr(force_result, 'content') else "基本面分析完成"
                    logger.info(f"[Force report] Report generated, length: {len(report)} chars")

                    return {
                        "fundamentals_report": report,
                        "messages": [force_result],
                        "fundamentals_tool_call_count": tool_call_count
                    }

                elif tool_call_count >= max_tool_calls:
                    logger.warning(f"[Anomaly] Reached max tool calls {max_tool_calls} with no tool results")
                    fallback_report = f"基本面分析（股票代码：{ticker}）\n\n由于达到最大工具调用次数限制，使用简化分析模式。建议检查数据源连接或降低分析复杂度。"
                    return {
                        "messages": [result],
                        "fundamentals_report": fallback_report,
                        "fundamentals_tool_call_count": tool_call_count
                    }
                else:
                    # First tool call - normal flow
                    logger.info(f"[Normal flow] LLM first tool call")
                    tool_calls_info = [tc['name'] for tc in result.tool_calls]
                    logger.info(f"[Normal flow] LLM requesting tools: {tool_calls_info}")
                    return {
                        "messages": [result]
                    }
            else:
                # No tool calls - check if we need forced tool call
                logger.info(f"[Fundamentals Analyst] No tool calls, checking if forced call needed")

                messages = state.get("messages", [])
                has_tool_result = any(isinstance(msg, ToolMessage) for msg in messages)

                has_analysis_content = False
                if hasattr(result, 'content') and result.content:
                    content_length = len(str(result.content))
                    if content_length > 500:
                        has_analysis_content = True
                        logger.info(f"[Content check] LLM returned valid analysis ({content_length} chars)")

                if has_tool_result or has_analysis_content:
                    logger.info(f"[Decision] Skipping forced tool call - already have results/content")
                    report = str(result.content) if hasattr(result, 'content') else "基本面分析完成"
                    return {
                        "fundamentals_report": report,
                        "messages": [result],
                        "fundamentals_tool_call_count": tool_call_count
                    }

                # No tool results and no analysis content - forced tool call
                logger.info(f"[Decision] Executing forced tool call")
                try:
                    # Find get_fundamentals tool
                    fundamentals_tool = None
                    for tool in tools:
                        t_name = getattr(tool, 'name', None) or getattr(tool, '__name__', None)
                        if t_name == 'get_fundamentals':
                            fundamentals_tool = tool
                            break

                    if fundamentals_tool:
                        combined_data = fundamentals_tool.invoke({
                            'ticker': ticker,
                            'curr_date': current_date
                        })
                        logger.info(f"[Forced call] Tool call success, data length: {len(str(combined_data))} chars")
                    else:
                        combined_data = "Fundamentals tool not available"
                        logger.warning(f"[Forced call] Fundamentals tool not found")
                except Exception as e:
                    combined_data = f"Fundamentals tool call failed: {e}"
                    logger.error(f"[Forced call] Exception: {e}")

                currency_info = f"{market_info['currency_name']}（{market_info['currency_symbol']}）"

                analysis_prompt = f"""基于以下真实数据，对{company_name}（股票代码：{ticker}）进行详细的基本面分析：

{combined_data}

请提供：
1. 公司基本信息分析（{company_name}，股票代码：{ticker}）
2. 财务状况评估
3. 盈利能力分析
4. 估值分析（使用{currency_info}）
5. 投资建议（买入/持有/卖出）

要求：
- 基于提供的真实数据进行分析
- 正确使用公司名称"{company_name}"和股票代码"{ticker}"
- 价格使用{currency_info}
- 投资建议使用中文
- 分析要详细且专业"""

                try:
                    analysis_prompt_template = ChatPromptTemplate.from_messages([
                        ("system", "你是专业的股票基本面分析师，基于提供的真实数据进行分析。"),
                        ("human", "{analysis_request}")
                    ])

                    analysis_chain = analysis_prompt_template | fresh_llm
                    analysis_result = analysis_chain.invoke({"analysis_request": analysis_prompt})

                    if hasattr(analysis_result, 'content'):
                        report = analysis_result.content
                    else:
                        report = str(analysis_result)

                    logger.info(f"[Fundamentals Analyst] Forced tool call complete, report length: {len(report)}")

                except Exception as e:
                    logger.error(f"[Fundamentals Analyst] Forced tool call analysis failed: {e}")
                    report = f"基本面分析失败：{str(e)}"

                return {
                    "fundamentals_report": report,
                    "fundamentals_tool_call_count": tool_call_count
                }

        # Fallback
        return {
            "messages": [result],
            "fundamentals_report": result.content if hasattr(result, 'content') else str(result),
            "fundamentals_tool_call_count": tool_call_count
        }

    return fundamentals_analyst_node
