"""
IMPERIUM WEBHOOK SERVER — ZERO KEYS REQUIRED
All tools work 100% free with no API keys.

Tools:
  /searchWeb      → DuckDuckGo Instant Answer API (free, no key)
  /browseWebsite  → Jina.ai reader (free, no key)
  /askAI          → Uses Jina.ai to research + summarize (free, no key)
  /getLiveData    → CoinGecko (crypto), wttr.in (weather), RSS (news)
  /lookupLead     → DuckDuckGo search (free, no key)
  /              → Health check
"""

import os, json, requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Optional keys — server works WITHOUT them, they just add power
SERPER_API_KEY     = os.environ.get("SERPER_API_KEY", "")
OPENAI_API_KEY     = os.environ.get("OPENAI_API_KEY", "")
WEATHER_API_KEY    = os.environ.get("WEATHER_API_KEY", "")

# Security — Vapi webhook secret
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

def verify_request():
    """Verify the request comes from Vapi using the secret header"""
    if not WEBHOOK_SECRET:
        return True  # No secret set — allow all (dev mode)
    auth = request.headers.get("X-Imperium-Secret", "")
    return auth == WEBHOOK_SECRET

# ─────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "LIVE",
        "service": "Imperium Webhook Server",
        "version": "2.0 — Zero Keys Required",
        "tools": ["searchWeb", "browseWebsite", "askAI", "getLiveData", "lookupLead"],
        "powered_by": "DuckDuckGo + Jina.ai + CoinGecko + wttr.in (all free)"
    })

# ─────────────────────────────────────────
# TOOL 1: searchWeb
# ─────────────────────────────────────────
@app.route("/searchWeb", methods=["POST"])
def search_web():
    if not verify_request():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(force=True)
    args = extract_args(data)
    query = args.get("query", "")

    if not query:
        return vapi_response("I need a search query.", data)

    result = do_search(query)
    return vapi_response(result, data)

# ─────────────────────────────────────────
# TOOL 2: browseWebsite
# ─────────────────────────────────────────
@app.route("/browseWebsite", methods=["POST"])
def browse_website():
    if not verify_request():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(force=True)
    args = extract_args(data)
    url = args.get("url", "")

    if not url:
        return vapi_response("I need a URL to visit.", data)

    try:
        jina_url = f"https://r.jina.ai/{url}"
        r = requests.get(jina_url, timeout=15, headers={"Accept": "text/plain"})
        content = r.text[:1500].strip()
        if not content:
            return vapi_response(f"Could not read {url}", data)
        return vapi_response(content, data)
    except Exception as e:
        return vapi_response(f"Could not browse that site right now.", data)

# ─────────────────────────────────────────
# TOOL 3: askAI
# ─────────────────────────────────────────
@app.route("/askAI", methods=["POST"])
def ask_ai():
    if not verify_request():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(force=True)
    args = extract_args(data)
    prompt = args.get("prompt", "")
    context = args.get("context", "")

    if not prompt:
        return vapi_response("I need a question to research.", data)

    # Use OpenAI if available, otherwise use Jina.ai to search + read
    if OPENAI_API_KEY:
        try:
            result = call_openai(f"Context: {context}\n\nQuestion: {prompt}" if context else prompt)
            return vapi_response(result, data)
        except:
            pass

    # Free fallback: search + read top result via Jina
    search_query = prompt[:200]
    result = do_search(search_query)
    return vapi_response(f"Here's what I found: {result}", data)

# ─────────────────────────────────────────
# TOOL 4: getLiveData
# ─────────────────────────────────────────
@app.route("/getLiveData", methods=["POST"])
def get_live_data():
    if not verify_request():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(force=True)
    args = extract_args(data)
    data_type = args.get("dataType", "")
    query = args.get("query", "")

    try:
        if data_type == "crypto":
            result = get_crypto(query)
        elif data_type == "weather":
            result = get_weather(query)
        elif data_type == "news":
            result = get_news(query)
        elif data_type == "stocks":
            result = get_stock(query)
        elif data_type == "real_estate":
            result = do_search(f"real estate market {query} 2025 median home price")
        elif data_type == "forex":
            result = get_forex(query)
        else:
            result = do_search(f"{query} live data today {data_type}")
        return vapi_response(result, data)
    except Exception as e:
        return vapi_response(f"Could not fetch that data right now.", data)

# ─────────────────────────────────────────
# TOOL 5: lookupLead
# ─────────────────────────────────────────
@app.route("/lookupLead", methods=["POST"])
def lookup_lead():
    if not verify_request():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(force=True)
    args = extract_args(data)
    name = args.get("name", "")
    city = args.get("city", "")
    industry = args.get("industry", "")
    goal = args.get("goal", "contact info")

    if not name:
        return vapi_response("I need a name to look up.", data)

    query = f"{name} {city} {industry} {goal}".strip()
    result = do_search(query)

    # Also try to read their website if it's a company
    try:
        site_result = do_search(f"{name} official website")
        return vapi_response(f"Intel on {name}:\n{result}\n\n{site_result}", data)
    except:
        return vapi_response(f"Intel on {name}:\n{result}", data)

# ─────────────────────────────────────────
# HELPER: Universal Search (Serper if key exists, else DuckDuckGo)
# ─────────────────────────────────────────
def do_search(query):
    # Try Serper first (better results, optional)
    if SERPER_API_KEY:
        try:
            headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
            r = requests.post(
                "https://google.serper.dev/search",
                headers=headers,
                json={"q": query, "num": 4},
                timeout=8
            )
            data = r.json()
            lines = []
            answer = data.get("answerBox", {}).get("answer") or data.get("answerBox", {}).get("snippet", "")
            if answer:
                lines.append(answer)
            for item in data.get("organic", [])[:3]:
                lines.append(f"• {item.get('title', '')}: {item.get('snippet', '')}")
            if lines:
                return "\n".join(lines)
        except:
            pass

    # Free fallback: Jina.ai reads DuckDuckGo search results page
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        jina_url = f"https://r.jina.ai/{search_url}"
        r = requests.get(jina_url, timeout=12, headers={"Accept": "text/plain", "X-Return-Format": "text"})
        text = r.text[:2000].strip()

        # Extract meaningful lines
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if len(line) > 40 and not line.startswith('http') and not line.startswith('['):
                lines.append(f"• {line[:200]}")
            if len(lines) >= 4:
                break

        if lines:
            return "\n".join(lines)
        return f"Searched for: {query}. No direct answer found — try browsing a specific URL."
    except Exception as e:
        return f"Search unavailable right now."

# ─────────────────────────────────────────
# HELPER: Live Crypto (CoinGecko — free, no key)
# ─────────────────────────────────────────
def get_crypto(query):
    coin_map = {
        "bitcoin": "bitcoin", "btc": "bitcoin",
        "ethereum": "ethereum", "eth": "ethereum",
        "solana": "solana", "sol": "solana",
        "xrp": "ripple", "ripple": "ripple",
        "cardano": "cardano", "ada": "cardano",
        "dogecoin": "dogecoin", "doge": "dogecoin"
    }
    coin_id = coin_map.get(query.lower().strip(), query.lower().strip().replace(" ", "-"))
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd", "include_24hr_change": "true"},
            timeout=8
        )
        data = r.json()
        if coin_id in data:
            price = data[coin_id]["usd"]
            change = data[coin_id].get("usd_24h_change", 0)
            direction = "up" if change > 0 else "down"
            return f"{query.upper()} is trading at ${price:,.2f}, {direction} {abs(change):.1f}% in the last 24 hours."
    except:
        pass
    return do_search(f"{query} price today")

# ─────────────────────────────────────────
# HELPER: Live Weather (wttr.in — free, no key)
# ─────────────────────────────────────────
def get_weather(query):
    try:
        r = requests.get(
            f"https://wttr.in/{query.replace(' ', '+')}",
            params={"format": 3},
            timeout=8,
            headers={"User-Agent": "ImperiumBot/1.0"}
        )
        if r.status_code == 200 and r.text.strip():
            return f"Weather in {r.text.strip()}"
    except:
        pass
    return do_search(f"current weather {query} today temperature")

# ─────────────────────────────────────────
# HELPER: News (RSS-based, free)
# ─────────────────────────────────────────
def get_news(query):
    try:
        r = requests.get(
            f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en",
            timeout=8
        )
        content = r.text
        # Quick parse — extract titles between <title> tags
        import re
        titles = re.findall(r'<title>(.*?)</title>', content)[2:7]  # skip first 2 (feed title)
        if titles:
            return "Latest news:\n" + "\n".join(f"• {t}" for t in titles[:5])
    except:
        pass
    return do_search(f"{query} news today latest")

# ─────────────────────────────────────────
# HELPER: Stock (search-based)
# ─────────────────────────────────────────
def get_stock(query):
    return do_search(f"{query} stock price today market cap 52 week")

# ─────────────────────────────────────────
# HELPER: Forex
# ─────────────────────────────────────────
def get_forex(query):
    try:
        r = requests.get(f"https://open.er-api.com/v6/latest/USD", timeout=8)
        data = r.json()
        rates = data.get("rates", {})
        query_upper = query.upper()
        if query_upper in rates:
            return f"1 USD = {rates[query_upper]} {query_upper} (live rate)"
    except:
        pass
    return do_search(f"{query} exchange rate today USD")

# ─────────────────────────────────────────
# HELPER: OpenAI (only used if key provided)
# ─────────────────────────────────────────
def call_openai(prompt):
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a concise AI assistant supporting a sales agent on a live call. Keep responses under 80 words, business-focused."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 250
    }
    r = requests.post("https://api.openai.com/v1/chat/completions",
                      headers=headers, json=body, timeout=12)
    return r.json()["choices"][0]["message"]["content"]

# ─────────────────────────────────────────
# HELPER: Extract Vapi tool arguments
# ─────────────────────────────────────────
def extract_args(data):
    """Extract tool arguments from any Vapi payload format"""
    try:
        msg = data.get("message", data)

        # Format 1: message.toolCallList (server-side tool calls)
        tool_list = msg.get("toolCallList", [])
        if tool_list:
            args = tool_list[0].get("function", {}).get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)
            return args

        # Format 2: message.toolCalls
        tool_calls = msg.get("toolCalls", [])
        if tool_calls:
            args = tool_calls[0].get("function", {}).get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)
            return args

        # Format 3: flat payload (direct post)
        if any(k in data for k in ["query", "url", "prompt", "dataType", "name"]):
            return data

    except:
        pass
    return {}

def get_tool_call_id(data):
    """Extract toolCallId for proper Vapi response"""
    try:
        msg = data.get("message", data)
        tool_list = msg.get("toolCallList", [])
        if tool_list:
            return tool_list[0].get("id", "imperium")
        tool_calls = msg.get("toolCalls", [])
        if tool_calls:
            return tool_calls[0].get("id", "imperium")
    except:
        pass
    return "imperium"

# ─────────────────────────────────────────
# HELPER: Format Vapi response
# ─────────────────────────────────────────
def vapi_response(result_text, data=None):
    tool_id = get_tool_call_id(data) if data else "imperium"
    return jsonify({
        "results": [{"toolCallId": tool_id, "result": str(result_text)}]
    })

# ─────────────────────────────────────────
# RUN
# ─────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    print(f"IMPERIUM WEBHOOK SERVER — PORT {port} — ZERO KEYS REQUIRED")
    app.run(host="0.0.0.0", port=port)
