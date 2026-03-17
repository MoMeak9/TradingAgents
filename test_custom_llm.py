"""Test script for custom LLM service - protocol compatibility tests."""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("CUSTOM_LLM_API_KEY")
api_url = os.getenv("CUSTOM_LLM_API_URL", "").rstrip("/")
model = os.getenv("CUSTOM_LLM_MODEL")

openai_base = api_url if api_url.endswith("/v1") else api_url + "/v1"
anthropic_url = api_url + "/v1/messages"

print(f"API URL:      {api_url}")
print(f"Model:        {model}")
print(f"OpenAI base:  {openai_base}")
print(f"Anthropic url:{anthropic_url}")
print(f"API Key:      {api_key[:20]}..." if api_key else "API Key: NOT SET")

results = {}

LONG_PROMPT = """你是一位专业的股票多头研究员。请基于以下市场数据对平安银行（000001）进行多头角度的深度分析，
并给出明确的投资建议。

市场数据摘要（模拟）：
- 收盘价：11.50 元，涨跌幅 +1.2%
- 成交量：1.2亿股，较昨日放量20%
- MA5: 11.30, MA10: 11.15, MA20: 10.95, MA60: 10.80（多头排列）
- MACD: DIF=0.15, DEA=0.08，金叉形成
- RSI(14): 58.3，处于健康区间
- BOLL: 上轨 12.10, 中轨 11.20, 下轨 10.30，价格在中轨上方运行

基本面数据（模拟）：
- 2024年营业收入：1400亿元，同比+3.5%
- 净利润：450亿元，同比+5.2%
- ROE: 12.1%, 不良贷款率 1.06%（改善）
- 市盈率（PE）: 5.8倍，处于历史低位
- 市净率（PB）: 0.65倍，具备安全边际

请从多头角度分析技术面支撑、基本面质地以及当前估值，并给出目标价与投资建议（300字以上）。"""

# ──────────────────────────────────────────────
# Test 1: OpenAI protocol – short message
# ──────────────────────────────────────────────
print("\n=== Test 1: OpenAI protocol (short message) ===")
try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=openai_base, timeout=30)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "请用中文说：你好，我正在工作！"}],
        max_tokens=50,
    )
    print("Response:", resp.choices[0].message.content)
    results["openai_short"] = "PASS"
except Exception as e:
    print(f"FAIL: {e}")
    results["openai_short"] = f"FAIL: {e}"

# ──────────────────────────────────────────────
# Test 2: OpenAI protocol – streaming long message
# ──────────────────────────────────────────────
print("\n=== Test 2: OpenAI protocol (streaming long message, timeout=60s) ===")
try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=openai_base, timeout=60)
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": LONG_PROMPT}],
        max_tokens=500,
        stream=True,
    )
    collected = []
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        collected.append(delta)
        if len("".join(collected)) > 200:
            break
    content = "".join(collected)
    print(f"Streaming response ({len(content)} chars): {content[:200]}...")
    results["openai_stream"] = "PASS"
except Exception as e:
    print(f"FAIL: {e}")
    results["openai_stream"] = f"FAIL: {e}"

# ──────────────────────────────────────────────
# Test 3: List available models
# ──────────────────────────────────────────────
print("\n=== Test 3: List available models ===")
try:
    r = requests.get(
        f"{openai_base}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10,
    )
    if r.status_code == 200:
        data = r.json()
        model_ids = [m["id"] for m in data.get("data", [])]
        print(f"Available models ({len(model_ids)}):", json.dumps(model_ids[:15], ensure_ascii=False, indent=2))
        results["list_models"] = f"PASS ({len(model_ids)} models)"
    else:
        print(f"HTTP {r.status_code}: {r.text[:300]}")
        results["list_models"] = f"HTTP {r.status_code}"
except Exception as e:
    print(f"FAIL: {e}")
    results["list_models"] = f"FAIL: {e}"

# ──────────────────────────────────────────────
# Test 4: Anthropic protocol (raw HTTP)
# ──────────────────────────────────────────────
print("\n=== Test 4: Anthropic protocol (raw HTTP) ===")
try:
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 50,
        "messages": [{"role": "user", "content": "请用中文说：你好！"}],
    }
    r = requests.post(anthropic_url, headers=headers, json=payload, timeout=30)
    if r.status_code == 200:
        data = r.json()
        text = data.get("content", [{}])[0].get("text", "")
        print("Response:", text)
        results["anthropic"] = "PASS"
    else:
        print(f"HTTP {r.status_code}: {r.text[:300]}")
        results["anthropic"] = f"HTTP {r.status_code}: {r.text[:150]}"
except Exception as e:
    print(f"FAIL: {e}")
    results["anthropic"] = f"FAIL: {e}"

# ──────────────────────────────────────────────
# Test 5: Non-streaming long request with timeout=60s
# ──────────────────────────────────────────────
print("\n=== Test 5: OpenAI protocol (non-streaming long, timeout=60s) ===")
try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=openai_base, timeout=60)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": LONG_PROMPT}],
        max_tokens=500,
    )
    content = resp.choices[0].message.content
    print(f"Response ({len(content)} chars): {content[:200]}...")
    results["openai_long_nonsstream"] = "PASS"
except Exception as e:
    print(f"FAIL: {type(e).__name__}: {str(e)[:200]}")
    results["openai_long_nonstream"] = f"FAIL: {type(e).__name__}: {str(e)[:100]}"

# ──────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("测试汇总：")
print("=" * 60)
for name, status in results.items():
    icon = "✓" if status.startswith("PASS") else "✗"
    print(f"  {icon} {name:<28} {status}")


load_dotenv()

api_key = os.getenv("CUSTOM_LLM_API_KEY")
api_url = os.getenv("CUSTOM_LLM_API_URL", "").rstrip("/")
model = os.getenv("CUSTOM_LLM_MODEL")

# Normalize OpenAI-style base URL
openai_base = api_url if api_url.endswith("/v1") else api_url + "/v1"
# Possible Anthropic endpoint
anthropic_url = api_url + "/v1/messages"

print(f"API URL:      {api_url}")
print(f"Model:        {model}")
print(f"OpenAI base:  {openai_base}")
print(f"Anthropic url:{anthropic_url}")
print(f"API Key:      {api_key[:20]}..." if api_key else "API Key: NOT SET")

results = {}

# ──────────────────────────────────────────────
# Test 1: OpenAI protocol – short message
# ──────────────────────────────────────────────
print("\n=== Test 1: OpenAI protocol (short message) ===")
try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=openai_base, timeout=30)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "请用中文说：你好，我正在工作！"}],
        max_tokens=50,
    )
    print("Response:", resp.choices[0].message.content)
    results["openai_short"] = "PASS"
except Exception as e:
    print(f"FAIL: {e}")
    results["openai_short"] = f"FAIL: {e}"

# ──────────────────────────────────────────────
# Test 2: OpenAI protocol – long/complex message (simulates bull_researcher)
# ──────────────────────────────────────────────
print("\n=== Test 2: OpenAI protocol (long complex message) ===")
LONG_PROMPT = """你是一位专业的股票多头研究员。请基于以下市场数据对平安银行（000001）进行多头角度的深度分析，
并给出明确的投资建议。

市场数据摘要（模拟）：
- 收盘价：11.50 元，涨跌幅 +1.2%
- 成交量：1.2亿股，较昨日放量20%
- MA5: 11.30, MA10: 11.15, MA20: 10.95, MA60: 10.80（多头排列）
- MACD: DIF=0.15, DEA=0.08，金叉形成
- RSI(14): 58.3，处于健康区间
- BOLL: 上轨 12.10, 中轨 11.20, 下轨 10.30，价格在中轨上方运行

基本面数据（模拟）：
- 2024年营业收入：1400亿元，同比+3.5%
- 净利润：450亿元，同比+5.2%
- ROE: 12.1%, 不良贷款率 1.06%（改善）
- 市盈率（PE）: 5.8倍，处于历史低位
- 市净率（PB）: 0.65倍，具备安全边际

请从多头角度：
1. 分析技术面支撑与趋势
2. 评估基本面质地
3. 判断当前估值吸引力
4. 给出目标价与投资建议（字数不少于300字）"""

try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=openai_base, timeout=120)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": LONG_PROMPT}],
        max_tokens=800,
    )
    content = resp.choices[0].message.content
    print(f"Response ({len(content)} chars):", content[:200], "...")
    results["openai_long"] = "PASS"
except Exception as e:
    print(f"FAIL: {e}")
    results["openai_long"] = f"FAIL: {e}"

# ──────────────────────────────────────────────
# Test 3: List available models (OpenAI /models endpoint)
# ──────────────────────────────────────────────
print("\n=== Test 3: List available models ===")
try:
    r = requests.get(
        f"{openai_base}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10,
    )
    if r.status_code == 200:
        data = r.json()
        model_ids = [m["id"] for m in data.get("data", [])]
        print(f"Available models ({len(model_ids)}):", model_ids[:10])
        results["list_models"] = f"PASS ({len(model_ids)} models)"
    else:
        print(f"HTTP {r.status_code}: {r.text[:200]}")
        results["list_models"] = f"HTTP {r.status_code}"
except Exception as e:
    print(f"FAIL: {e}")
    results["list_models"] = f"FAIL: {e}"

# ──────────────────────────────────────────────
# Test 4: Anthropic protocol (raw HTTP)
# ──────────────────────────────────────────────
print("\n=== Test 4: Anthropic protocol (raw HTTP) ===")
try:
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 50,
        "messages": [{"role": "user", "content": "请用中文说：你好！"}],
    }
    r = requests.post(anthropic_url, headers=headers, json=payload, timeout=30)
    if r.status_code == 200:
        data = r.json()
        text = data.get("content", [{}])[0].get("text", "")
        print("Response:", text)
        results["anthropic"] = "PASS"
    else:
        print(f"HTTP {r.status_code}: {r.text[:300]}")
        results["anthropic"] = f"HTTP {r.status_code}: {r.text[:100]}"
except Exception as e:
    print(f"FAIL: {e}")
    results["anthropic"] = f"FAIL: {e}"

# ──────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("测试汇总：")
print("=" * 60)
for name, status in results.items():
    icon = "✓" if status.startswith("PASS") else "✗"
    print(f"  {icon} {name:<20} {status}")

