from typing import Annotated

# Import from vendor-specific modules
from .y_finance import (
    get_YFin_data_online,
    get_stock_stats_indicators_window,
    get_fundamentals as get_yfinance_fundamentals,
    get_balance_sheet as get_yfinance_balance_sheet,
    get_cashflow as get_yfinance_cashflow,
    get_income_statement as get_yfinance_income_statement,
    get_insider_transactions as get_yfinance_insider_transactions,
)
from .yfinance_news import get_news_yfinance, get_global_news_yfinance
from .alpha_vantage import (
    get_stock as get_alpha_vantage_stock,
    get_indicator as get_alpha_vantage_indicator,
    get_fundamentals as get_alpha_vantage_fundamentals,
    get_balance_sheet as get_alpha_vantage_balance_sheet,
    get_cashflow as get_alpha_vantage_cashflow,
    get_income_statement as get_alpha_vantage_income_statement,
    get_insider_transactions as get_alpha_vantage_insider_transactions,
    get_news as get_alpha_vantage_news,
    get_global_news as get_alpha_vantage_global_news,
)
from .alpha_vantage_common import AlphaVantageRateLimitError

# A-share vendor imports
from .akshare_stock import (
    get_stock_data as get_akshare_stock,
    get_indicators as get_akshare_indicators,
    get_fundamentals as get_akshare_fundamentals,
    get_balance_sheet as get_akshare_balance_sheet,
    get_cashflow as get_akshare_cashflow,
    get_income_statement as get_akshare_income_statement,
    get_insider_transactions as get_akshare_insider_transactions,
)
from .akshare_news import (
    get_news as get_akshare_news,
    get_global_news as get_akshare_global_news,
)

# Tushare vendor imports (primary for A-share)
from .tushare_stock import (
    get_stock_data as get_tushare_stock,
    get_indicators as get_tushare_indicators,
    get_fundamentals as get_tushare_fundamentals,
    get_balance_sheet as get_tushare_balance_sheet,
    get_cashflow as get_tushare_cashflow,
    get_income_statement as get_tushare_income_statement,
    get_insider_transactions as get_tushare_insider_transactions,
    TushareError,
)

# Market detection
from .market_utils import detect_market, normalize_symbol

# Configuration and routing logic
from .config import get_config, get_market_context

# Methods where the first argument is NOT a stock symbol
_NON_SYMBOL_METHODS = {"get_global_news"}

# Tools organized by category
TOOLS_CATEGORIES = {
    "core_stock_apis": {
        "description": "OHLCV stock price data",
        "tools": [
            "get_stock_data"
        ]
    },
    "technical_indicators": {
        "description": "Technical analysis indicators",
        "tools": [
            "get_indicators"
        ]
    },
    "fundamental_data": {
        "description": "Company fundamentals",
        "tools": [
            "get_fundamentals",
            "get_balance_sheet",
            "get_cashflow",
            "get_income_statement"
        ]
    },
    "news_data": {
        "description": "News and insider data",
        "tools": [
            "get_news",
            "get_global_news",
            "get_insider_transactions",
        ]
    }
}

VENDOR_LIST = [
    "yfinance",
    "alpha_vantage",
    "akshare",
    "tushare",
]

# Mapping of methods to their vendor-specific implementations
VENDOR_METHODS = {
    # core_stock_apis
    "get_stock_data": {
        "alpha_vantage": get_alpha_vantage_stock,
        "yfinance": get_YFin_data_online,
        "akshare": get_akshare_stock,
        "tushare": get_tushare_stock,
    },
    # technical_indicators
    "get_indicators": {
        "alpha_vantage": get_alpha_vantage_indicator,
        "yfinance": get_stock_stats_indicators_window,
        "akshare": get_akshare_indicators,
        "tushare": get_tushare_indicators,
    },
    # fundamental_data
    "get_fundamentals": {
        "alpha_vantage": get_alpha_vantage_fundamentals,
        "yfinance": get_yfinance_fundamentals,
        "akshare": get_akshare_fundamentals,
        "tushare": get_tushare_fundamentals,
    },
    "get_balance_sheet": {
        "alpha_vantage": get_alpha_vantage_balance_sheet,
        "yfinance": get_yfinance_balance_sheet,
        "akshare": get_akshare_balance_sheet,
        "tushare": get_tushare_balance_sheet,
    },
    "get_cashflow": {
        "alpha_vantage": get_alpha_vantage_cashflow,
        "yfinance": get_yfinance_cashflow,
        "akshare": get_akshare_cashflow,
        "tushare": get_tushare_cashflow,
    },
    "get_income_statement": {
        "alpha_vantage": get_alpha_vantage_income_statement,
        "yfinance": get_yfinance_income_statement,
        "akshare": get_akshare_income_statement,
        "tushare": get_tushare_income_statement,
    },
    # news_data
    "get_news": {
        "alpha_vantage": get_alpha_vantage_news,
        "yfinance": get_news_yfinance,
        "akshare": get_akshare_news,
    },
    "get_global_news": {
        "yfinance": get_global_news_yfinance,
        "alpha_vantage": get_alpha_vantage_global_news,
        "akshare": get_akshare_global_news,
    },
    "get_insider_transactions": {
        "alpha_vantage": get_alpha_vantage_insider_transactions,
        "yfinance": get_yfinance_insider_transactions,
        "akshare": get_akshare_insider_transactions,
        "tushare": get_tushare_insider_transactions,
    },
}

def get_category_for_method(method: str) -> str:
    """Get the category that contains the specified method."""
    for category, info in TOOLS_CATEGORIES.items():
        if method in info["tools"]:
            return category
    raise ValueError(f"Method '{method}' not found in any category")

def get_vendor(category: str, method: str = None) -> str:
    """Get the configured vendor for a US data category or specific tool method.
    Tool-level configuration takes precedence over category-level.
    """
    config = get_config()

    # Check tool-level configuration first (if method provided)
    if method:
        tool_vendors = config.get("tool_vendors", {})
        if method in tool_vendors:
            return tool_vendors[method]

    # Fall back to category-level configuration
    return config.get("data_vendors", {}).get(category, "default")

def get_vendor_cn(category: str, method: str = None) -> str:
    """Get the configured vendor for a CN (A-share) data category or specific tool method.
    Tool-level configuration takes precedence over category-level.
    """
    config = get_config()

    # Check CN tool-level configuration first
    if method:
        cn_tool_vendors = config.get("cn_tool_vendors", {})
        if method in cn_tool_vendors:
            return cn_tool_vendors[method]

    # Fall back to CN category-level configuration
    return config.get("cn_data_vendors", {}).get(category, "tushare")

def _detect_market_for_route(method: str, args, kwargs) -> str:
    """Detect market from the method call arguments."""
    if method in _NON_SYMBOL_METHODS:
        # get_global_news has no symbol arg; use thread-local context
        return get_market_context()

    # Extract symbol from first positional arg or keyword
    symbol = ""
    if args:
        symbol = args[0]
    else:
        symbol = kwargs.get("symbol", kwargs.get("ticker", ""))

    if not symbol:
        return "us"

    return detect_market(str(symbol))

def route_to_vendor(method: str, *args, **kwargs):
    """Route method calls to appropriate vendor implementation with market-aware fallback."""
    # Detect market from symbol
    market = _detect_market_for_route(method, args, kwargs)

    # Get vendor config based on market
    category = get_category_for_method(method)
    if market == "cn":
        vendor_config = get_vendor_cn(category, method)
    else:
        vendor_config = get_vendor(category, method)

    primary_vendors = [v.strip() for v in vendor_config.split(',')]

    if method not in VENDOR_METHODS:
        raise ValueError(f"Method '{method}' not supported")

    # Normalize symbol for the target vendor
    if method not in _NON_SYMBOL_METHODS and args:
        symbol = str(args[0])
        normalized = normalize_symbol(symbol, market)
        args = (normalized,) + args[1:]

    # Build fallback chain: primary vendors first, then remaining available vendors
    # For CN market, only include CN-compatible vendors in fallback
    all_available_vendors = list(VENDOR_METHODS[method].keys())
    if market == "cn":
        cn_vendors = ["tushare", "akshare"]
        all_available_vendors = [v for v in all_available_vendors if v in cn_vendors]
    else:
        us_vendors = ["yfinance", "alpha_vantage"]
        all_available_vendors = [v for v in all_available_vendors if v in us_vendors]

    fallback_vendors = primary_vendors.copy()
    for vendor in all_available_vendors:
        if vendor not in fallback_vendors:
            fallback_vendors.append(vendor)

    last_error = None
    for vendor in fallback_vendors:
        if vendor not in VENDOR_METHODS[method]:
            continue

        vendor_impl = VENDOR_METHODS[method][vendor]
        impl_func = vendor_impl[0] if isinstance(vendor_impl, list) else vendor_impl

        try:
            return impl_func(*args, **kwargs)
        except AlphaVantageRateLimitError:
            continue  # Rate limits trigger fallback
        except Exception as e:
            last_error = e
            # For CN vendors, any exception triggers fallback to next CN vendor
            if market == "cn":
                continue
            raise

    # All vendors exhausted — return error string instead of raising,
    # so the LLM agent can see the error and continue gracefully.
    return f"Error: All data vendors failed for '{method}' (market={market}). Last error: {last_error}"
