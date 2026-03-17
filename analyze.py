#!/usr/bin/env python3
"""
TradingAgents 多股票并行分析工具

功能:
  - 支持多只股票并行分析
  - 5档分析强度 (1-闪电 ~ 5-极致)
  - 完整 CLI 参数支持
  - 自动市场检测 (A股/港股/美股)
  - 结果汇总与对比输出

用法示例:
  # 分析单只A股
  python analyze.py 000001

  # 并行分析多只股票，强度3
  python analyze.py 000001 600519 00700 AAPL -l 3

  # 深度分析，指定日期
  python analyze.py 000001 600519 -l 5 -d 2025-03-17

  # 快速扫描，4线程并行
  python analyze.py 000001 600519 300750 601318 -l 1 -w 4
"""

import argparse
import json
import os
import sys
import time
import threading
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    MofNCompleteColumn,
)
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich import box
from rich.columns import Columns
from rich.align import Align

console = Console()

# ─── 5 档分析强度定义 ────────────────────────────────────────────
# 每档对应不同的分析师组合、辩论轮数和递归限制
INTENSITY_PROFILES = {
    1: {
        "name": "闪电",
        "desc": "极速扫描，最少分析师，单轮辩论",
        "analysts": ["market"],
        "max_debate_rounds": 1,
        "max_risk_discuss_rounds": 1,
        "max_recur_limit": 50,
    },
    2: {
        "name": "快速",
        "desc": "快速分析，核心分析师，单轮辩论",
        "analysts": ["market", "fundamentals"],
        "max_debate_rounds": 1,
        "max_risk_discuss_rounds": 1,
        "max_recur_limit": 80,
    },
    3: {
        "name": "标准",
        "desc": "均衡分析，三路分析师，双轮辩论",
        "analysts": ["market", "fundamentals", "news"],
        "max_debate_rounds": 2,
        "max_risk_discuss_rounds": 2,
        "max_recur_limit": 100,
    },
    4: {
        "name": "深度",
        "desc": "深度分析，全部分析师，三轮辩论",
        "analysts": ["market", "fundamentals", "news", "social"],
        "max_debate_rounds": 3,
        "max_risk_discuss_rounds": 3,
        "max_recur_limit": 150,
    },
    5: {
        "name": "极致",
        "desc": "最高精度，全部分析师，五轮辩论",
        "analysts": ["market", "fundamentals", "news", "social"],
        "max_debate_rounds": 5,
        "max_risk_discuss_rounds": 5,
        "max_recur_limit": 200,
    },
}


def build_config(args: argparse.Namespace, intensity: dict) -> Dict[str, Any]:
    """根据 CLI 参数和强度档位构建配置。"""
    from tradingagents.default_config import DEFAULT_CONFIG

    config = DEFAULT_CONFIG.copy()

    # LLM 设置
    config["llm_provider"] = args.provider
    config["deep_think_llm"] = args.deep_model
    config["quick_think_llm"] = args.quick_model

    if args.backend_url:
        url = args.backend_url.rstrip("/")
        if not url.endswith("/v1"):
            url += "/v1"
        config["backend_url"] = url

    # 强度参数覆盖
    config["max_debate_rounds"] = intensity["max_debate_rounds"]
    config["max_risk_discuss_rounds"] = intensity["max_risk_discuss_rounds"]
    config["max_recur_limit"] = intensity["max_recur_limit"]

    # A股数据源
    if args.cn_vendor:
        config["cn_data_vendors"] = {
            "core_stock_apis": args.cn_vendor,
            "technical_indicators": args.cn_vendor,
            "fundamental_data": args.cn_vendor,
            "news_data": "akshare",
        }

    return config


def _log(msg: str, ticker: str = "", style: str = ""):
    """带时间戳的日志输出。"""
    ts = datetime.now().strftime("%H:%M:%S")
    prefix = f"[dim]{ts}[/dim]"
    tag = f"[cyan]{ticker}[/cyan] " if ticker else ""
    if style:
        console.print(f"  {prefix} {tag}[{style}]{msg}[/{style}]")
    else:
        console.print(f"  {prefix} {tag}{msg}")


def analyze_single(
    ticker: str,
    trade_date: str,
    config: Dict[str, Any],
    analysts: List[str],
    debug: bool,
    log_fn=None,
) -> Dict[str, Any]:
    """分析单只股票，返回结果字典。适用于主进程或子进程调用。"""
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from cli.stats_handler import StatsCallbackHandler

    log = log_fn or (lambda msg, **kw: _log(msg, ticker=ticker, **kw))
    t0 = time.time()
    result: Dict[str, Any] = {"ticker": ticker, "date": trade_date}

    try:
        # 统计回调
        stats = StatsCallbackHandler()

        log("初始化分析图 ...", style="yellow")
        ta = TradingAgentsGraph(
            selected_analysts=analysts,
            debug=debug,
            config=config,
            callbacks=[stats],
        )
        elapsed_init = round(time.time() - t0, 1)
        log(f"初始化完成 ({elapsed_init}s)，开始数据采集与分析 ...", style="green")

        final_state, decision = ta.propagate(ticker, trade_date)

        st = stats.get_stats()
        result["status"] = "success"
        result["decision"] = decision
        result["elapsed"] = round(time.time() - t0, 1)
        result["stats"] = st
        result["report_lens"] = {
            "market_report": len(final_state.get("market_report", "")),
            "fundamentals_report": len(final_state.get("fundamentals_report", "")),
            "news_report": len(final_state.get("news_report", "")),
            "sentiment_report": len(final_state.get("sentiment_report", "")),
            "final_trade_decision": len(final_state.get("final_trade_decision", "")),
        }
        log(
            f"分析完成 — LLM调用: {st['llm_calls']}  工具调用: {st['tool_calls']}  "
            f"Token: {st['tokens_in']}↓ {st['tokens_out']}↑  耗时: {result['elapsed']}s",
            style="bold green",
        )
    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)
        result["traceback"] = traceback.format_exc()
        result["elapsed"] = round(time.time() - t0, 1)
        log(f"失败: {exc}", style="bold red")

    return result


# ─── 子进程入口 ──────────────────────────────────────────────────
def _worker(
    ticker: str,
    trade_date: str,
    config_json: str,
    analysts: List[str],
    debug: bool,
) -> Dict[str, Any]:
    """ProcessPoolExecutor 工作函数，接收 JSON 序列化的 config。"""
    load_dotenv()
    config = json.loads(config_json)
    return analyze_single(ticker, trade_date, config, analysts, debug)


def _serializable_config(config: Dict[str, Any]) -> str:
    """将 config 序列化为 JSON 字符串以便跨进程传递。"""
    clean = {}
    for k, v in config.items():
        try:
            json.dumps(v)
            clean[k] = v
        except (TypeError, ValueError):
            clean[k] = str(v)
    return json.dumps(clean, ensure_ascii=False)


# ─── 格式化工具 ──────────────────────────────────────────────────
def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def _action_style(action: str) -> str:
    """为操作建议配色。"""
    a = str(action).strip()
    if a in ("买入", "buy", "Buy"):
        return "bold green"
    if a in ("卖出", "sell", "Sell"):
        return "bold red"
    return "bold yellow"


# ─── 输出格式化 ──────────────────────────────────────────────────
def print_header(args: argparse.Namespace, intensity: dict):
    """用 Rich Panel 打印分析任务头部信息。"""
    level_colors = {1: "cyan", 2: "green", 3: "yellow", 4: "magenta", 5: "red"}
    lv_color = level_colors.get(args.level, "white")

    info_lines = [
        f"[bold]股票列表[/bold]  : [cyan]{', '.join(args.tickers)}[/cyan]",
        f"[bold]分析日期[/bold]  : {args.date}",
        f"[bold]分析强度[/bold]  : [{lv_color}]Lv.{args.level} {intensity['name']} — {intensity['desc']}[/{lv_color}]",
        f"[bold]分析师团队[/bold]: {', '.join(intensity['analysts'])}",
        f"[bold]辩论轮数[/bold]  : {intensity['max_debate_rounds']}   [bold]风控轮数[/bold]: {intensity['max_risk_discuss_rounds']}",
        f"[bold]并行进程[/bold]  : {args.workers}",
        f"[bold]LLM[/bold]       : {args.provider} / {args.quick_model}",
    ]
    panel = Panel(
        "\n".join(info_lines),
        title="[bold]TradingAgents 多股票分析工具[/bold]",
        subtitle=f"共 {len(args.tickers)} 只股票",
        border_style="blue",
        padding=(1, 2),
    )
    console.print(panel)
    console.print()


def print_result(result: Dict[str, Any], idx: int, total: int):
    """用 Rich 打印单只股票的结果摘要。"""
    ticker = result["ticker"]

    if result["status"] == "error":
        console.print(
            f"  [bold red]✗[/bold red] [{idx}/{total}] "
            f"[cyan]{ticker}[/cyan] — [red]失败[/red] ({result['elapsed']}s)"
        )
        console.print(f"    [dim red]{result['error']}[/dim red]")
        return

    d = result["decision"]
    action = d.get("action", "N/A")
    astyle = _action_style(action)
    conf = d.get("confidence")
    conf_str = f"{conf:.0%}" if isinstance(conf, (int, float)) else str(conf or "-")
    risk = d.get("risk_score")
    risk_str = f"{risk:.0%}" if isinstance(risk, (int, float)) else str(risk or "-")

    console.print(
        f"  [bold green]✓[/bold green] [{idx}/{total}] "
        f"[cyan]{ticker}[/cyan] — [{astyle}]{action}[/{astyle}]  "
        f"目标价: {d.get('target_price', '-')}  "
        f"置信度: {conf_str}  风险: {risk_str}  "
        f"[dim]({result['elapsed']}s)[/dim]"
    )
    reason = str(d.get("reasoning", ""))
    if len(reason) > 150:
        reason = reason[:150] + "…"
    console.print(f"    [dim]{reason}[/dim]")

    # 展示 stats
    st = result.get("stats")
    if st:
        console.print(
            f"    [dim]LLM: {st['llm_calls']}次  "
            f"工具: {st['tool_calls']}次  "
            f"Token: {_fmt_tokens(st['tokens_in'])}↓ {_fmt_tokens(st['tokens_out'])}↑[/dim]"
        )


def print_summary(results: List[Dict[str, Any]]):
    """用 Rich Table 打印最终汇总表。"""
    console.print()

    # ── 决策汇总表 ──
    table = Table(
        title="分析汇总",
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold magenta",
        title_style="bold",
        padding=(0, 1),
    )
    table.add_column("股票", style="cyan", justify="center", width=10)
    table.add_column("操作", justify="center", width=8)
    table.add_column("目标价", justify="right", width=12)
    table.add_column("置信度", justify="center", width=8)
    table.add_column("风险", justify="center", width=8)
    table.add_column("LLM次", justify="right", width=7)
    table.add_column("工具次", justify="right", width=7)
    table.add_column("Token↓", justify="right", width=8)
    table.add_column("Token↑", justify="right", width=8)
    table.add_column("耗时", justify="right", width=8)

    success = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "error"]

    for r in success:
        d = r["decision"]
        action = str(d.get("action", "-"))
        astyle = _action_style(action)
        price = str(d.get("target_price", "-"))
        conf = d.get("confidence")
        conf_str = f"{conf:.0%}" if isinstance(conf, (int, float)) else str(conf or "-")
        risk = d.get("risk_score")
        risk_str = f"{risk:.0%}" if isinstance(risk, (int, float)) else str(risk or "-")
        st = r.get("stats", {})
        table.add_row(
            r["ticker"],
            f"[{astyle}]{action}[/{astyle}]",
            price,
            conf_str,
            risk_str,
            str(st.get("llm_calls", "-")),
            str(st.get("tool_calls", "-")),
            _fmt_tokens(st.get("tokens_in", 0)),
            _fmt_tokens(st.get("tokens_out", 0)),
            f"{r['elapsed']}s",
        )

    for r in failed:
        table.add_row(
            r["ticker"],
            "[red]失败[/red]",
            "-", "-", "-", "-", "-", "-", "-",
            f"{r['elapsed']}s",
        )

    console.print(table)

    # ── 统计行 ──
    total_time = sum(r["elapsed"] for r in results)
    total_llm = sum(r.get("stats", {}).get("llm_calls", 0) for r in success)
    total_tool = sum(r.get("stats", {}).get("tool_calls", 0) for r in success)
    total_in = sum(r.get("stats", {}).get("tokens_in", 0) for r in success)
    total_out = sum(r.get("stats", {}).get("tokens_out", 0) for r in success)
    console.print(
        f"  [bold]成功: {len(success)}/{len(results)}[/bold]  |  "
        f"LLM: {total_llm}次  工具: {total_tool}次  "
        f"Token: {_fmt_tokens(total_in)}↓ {_fmt_tokens(total_out)}↑  |  "
        f"总耗时: [bold]{total_time:.1f}s[/bold]"
    )

    # ── 保存汇总 JSON ──
    summary_dir = Path("eval_results/_batch_summary")
    summary_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = summary_dir / f"batch_{ts}.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    console.print(f"  [dim]汇总已保存: {summary_file}[/dim]")
    console.print()


# ─── CLI 定义 ────────────────────────────────────────────────────
def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="analyze",
        description="TradingAgents 多股票并行分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
分析强度档位:
  1  闪电  极速扫描，市场分析师，单轮辩论
  2  快速  核心双分析师（市场+基本面），单轮辩论
  3  标准  三路分析师（+新闻），双轮辩论
  4  深度  全部分析师，三轮辩论
  5  极致  全部分析师，五轮辩论

示例:
  %(prog)s 000001                       # A股单只，默认强度2
  %(prog)s 000001 600519 -l 4           # 两只A股，深度分析
  %(prog)s AAPL MSFT GOOGL -l 3 -w 3   # 三只美股并行
  %(prog)s 000001 -l 5 -d 2025-03-17   # 极致分析，指定日期
""",
    )

    parser.add_argument(
        "tickers",
        nargs="+",
        help="股票代码列表（空格分隔），支持A股/港股/美股混合",
    )
    parser.add_argument(
        "-l", "--level",
        type=int,
        choices=[1, 2, 3, 4, 5],
        default=2,
        help="分析强度 1-5（默认: 2）",
    )
    parser.add_argument(
        "-d", "--date",
        type=str,
        default=date.today().strftime("%Y-%m-%d"),
        help="分析日期 YYYY-MM-DD（默认: 今天）",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=1,
        help="并行进程数（默认: 1，即串行）",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default=os.getenv("LLM_PROVIDER", "custom"),
        help="LLM 提供商（默认: custom）",
    )
    parser.add_argument(
        "--deep-model",
        type=str,
        default=os.getenv("DEEP_LLM_MODEL", os.getenv("CUSTOM_LLM_MODEL", "gpt-5.4")),
        help="深度思考模型名",
    )
    parser.add_argument(
        "--quick-model",
        type=str,
        default=os.getenv("QUICK_LLM_MODEL", os.getenv("CUSTOM_LLM_MODEL", "gpt-5.4")),
        help="快速思考模型名",
    )
    parser.add_argument(
        "--backend-url",
        type=str,
        default=os.getenv("CUSTOM_LLM_API_URL", ""),
        help="LLM API 地址",
    )
    parser.add_argument(
        "--cn-vendor",
        type=str,
        choices=["tushare", "akshare", "baostock"],
        default="tushare",
        help="A股数据源（默认: tushare）",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="开启调试模式（打印详细 LLM 交互日志）",
    )

    return parser.parse_args(argv)


# ─── 进度条工厂 ──────────────────────────────────────────────────
def _make_batch_progress() -> Progress:
    """创建批量总进度条。"""
    return Progress(
        SpinnerColumn("earth"),
        TextColumn("[bold]总进度"),
        BarColumn(bar_width=30, complete_style="green", finished_style="bold green"),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
    )


def _make_stock_progress() -> Progress:
    """创建每只股票的状态进度条。"""
    return Progress(
        SpinnerColumn("dots"),
        TextColumn("[bold blue]{task.fields[ticker]}"),
        BarColumn(bar_width=20),
        TaskProgressColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TextColumn("{task.fields[phase]}"),
    )


# ─── 主入口 ──────────────────────────────────────────────────────
def main(argv: Optional[List[str]] = None):
    args = parse_args(argv)
    intensity = INTENSITY_PROFILES[args.level]
    config = build_config(args, intensity)
    analysts = intensity["analysts"]

    print_header(args, intensity)

    tickers = args.tickers
    results: List[Dict[str, Any]] = []
    batch_t0 = time.time()

    if len(tickers) == 1 or args.workers <= 1:
        # ── 串行执行（带逐条进度条）──
        batch_progress = _make_batch_progress()
        batch_task = batch_progress.add_task("batch", total=len(tickers))

        for i, ticker in enumerate(tickers, 1):
            console.rule(f"[bold cyan]{ticker}[/bold cyan]  ({i}/{len(tickers)})")
            _log("开始分析 ...", ticker=ticker, style="bold blue")
            result = analyze_single(ticker, args.date, config, analysts, args.debug)
            results.append(result)
            print_result(result, i, len(tickers))
            console.print()
            batch_progress.update(batch_task, advance=1)

        console.print(batch_progress)
    else:
        # ── 并行执行（带总进度条 + 每股状态）──
        max_w = min(args.workers, len(tickers))
        console.print(f"  [bold]启动 {max_w} 个并行进程 ...[/bold]\n")
        config_json = _serializable_config(config)

        # 两个 Progress 共享同一个 Live 以避免 "Only one live display" 错误
        batch_progress = _make_batch_progress()
        batch_task = batch_progress.add_task("batch", total=len(tickers))

        stock_tasks: Dict[str, Any] = {}
        stock_progress = _make_stock_progress()
        for t in tickers:
            tid = stock_progress.add_task(
                t, total=1, ticker=t, phase="排队中"
            )
            stock_tasks[t] = tid

        progress_group = Group(batch_progress, stock_progress)

        with Live(progress_group, console=console, refresh_per_second=4):
            with ProcessPoolExecutor(max_workers=max_w) as pool:
                future_map = {
                    pool.submit(_worker, t, args.date, config_json, analysts, args.debug): t
                    for t in tickers
                }

                # 标记已提交的为"分析中"
                for fut, t in future_map.items():
                    stock_progress.update(stock_tasks[t], phase="[yellow]分析中 ...[/yellow]")

                done_count = 0
                for future in as_completed(future_map):
                    done_count += 1
                    t = future_map[future]
                    result = future.result()
                    results.append(result)

                    if result["status"] == "success":
                        phase_text = f"[green]✓ {result['decision'].get('action', '')}[/green]"
                    else:
                        phase_text = "[red]✗ 失败[/red]"
                    stock_progress.update(stock_tasks[t], completed=1, phase=phase_text)
                    batch_progress.update(batch_task, advance=1)

        # 打印每条结果
        console.print()
        for i, r in enumerate(results, 1):
            print_result(r, i, len(tickers))
            console.print()

    # 按原始顺序排序结果
    order = {t: i for i, t in enumerate(tickers)}
    results.sort(key=lambda r: order.get(r["ticker"], 999))

    total_wall = round(time.time() - batch_t0, 1)
    print_summary(results)
    console.print(f"  [dim]总墙钟时间: {total_wall}s[/dim]")

    # 退出码: 有失败则返回 1
    if any(r["status"] == "error" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
