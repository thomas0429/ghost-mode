"""
IMPERIUM WEBHOOK SERVER
Handles all 5 Vapi tool calls with real live APIs
Deploy free on: Railway, Render, or Fly.io

Tools:
  /searchWeb      → Serper.dev (Google Search)
  /browseWebsite  → Jina.ai reader (free, no key needed)
  /askAI          → OpenAI GPT-4o / Claude / Perplexity
  /getLiveData    → CoinGecko, OpenWeatherMap, NewsAPI
  /lookupLead     → Serper + Hunter.io
  /              → Health check
"""

import os, json, requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ── ENV VARS — set these in Railway/Render dashboard ──
SERPER_API_KEY    = os.environ.get("SERPER_API_KEY", "")
OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
PERPLEXITY_API_KEY= os.environ.get("PERPLEXITY_API_KEY", "")
HUNTER_API_KEY    = os.environ.get("HUNTER_API_KEY", "")
WEATHER_API_KEY   = os.environ.get("WEATHER_API_KEY", "")   # openweathermap.org free
NEWS_API_KEY      = os.environ.get("NEWS_API_KEY", "")       # newsapi.org free

# ─────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "live",
        "service": "Imperium Webhook Server",
        "tools": ["searchWeb", "browseWebsite", "askAI", "getLiveData", "lookupLead"],
        "apis_connected": {
            "serper": bool(SERPER_API_KEY),
            "openai": bool(OPENAI_API_KEY),
            "anthropic": bool(ANTHROPIC_API_KEY),
            "perplexity": bool(PERPLEXITY_API_KEY),
            "hunter": bool(HUNTER_API_KEY),
            "weather": bool(WEATHER_API_KEY),
            "news": bool(NEWS_API_KEY)
        }
    })

# ─────────────────────────────────────────
# TOOL 1: searchWeb
# ─────────────────────────────────────────
@app.route("/searchWeb", methods=["POST"])
def search_web():
    data = request.get_json(force=True)
    # Vapi sends tool args inside "function" > "arguments"
    args = extract_args(data)
    query = args.get("query", "")
    intent = args.get("intent", "")

    if not query:
        return vapi_response("I need a search query to look that up.")

    try:
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        r = requests.post(
            "https://google.serper.dev/search",
            headers=headers,
            json={"q": query, "num": 5},
            timeout=8
        )
        results = r.json()
        organic = results.get("organic", [])
        answer_box = results.get("answerBox", {})

        lines = []
        if answer_box.get("answer"):
            lines.append(f"Direct answer: {answer_box['answer']}")
        elif answer_box.get("snippet"):
            lines.append(f"Quick answer: {answer_box['snippet']}")

        for item in organic[:4]:
            lines.append(f"• {item.get('title', '')}: {item.get('snippet', '')}")

        result = "\n".join(lines) if lines else "No results found."
        return vapi_response(result)

    except Exception as e:
        return vapi_response(f"Search failed: {str(e)}")

# ─────────────────────────────────────────
# TOOL 2: browseWebsite
# ─────────────────────────────────────────
@app.route("/browseWebsite", methods=["POST"])
def browse_website():
    data = request.get_json(force=True)
    args = extract_args(data)
    url = args.get("url", "")
    goal = args.get("goal", "summarize the page")

    if not url:
        return vapi_response("I need a URL to visit.")

    try:
        # Jina.ai reader — free, no key needed, reads any webpage
        jina_url = f"https://r.jina.ai/{url}"
        r = requests.get(jina_url, timeout=12, headers={"Accept": "text/plain"})
        content = r.text[:3000]  # First 3000 chars

        if not content:
            return vapi_response(f"Could not read {url}")

        # Summarize with OpenAI if available
        if OPENAI_API_KEY:
            summary = gpt_summarize(content, goal)
            return vapi_response(summary)
        else:
            # Return raw first 500 chars
            return vapi_response(content[:500])

    except Exception as e:
        return vapi_response(f"Could not browse that site: {str(e)}")

# ─────────────────────────────────────────
# TOOL 3: askAI
# ─────────────────────────────────────────
@app.route("/askAI", methods=["POST"])
def ask_ai():
    data = request.get_json(force=True)
    args = extract_args(data)
    model = args.get("model", "auto")
    prompt = args.get("prompt", "")
    context = args.get("context", "")

    if not prompt:
        return vapi_response("I need a question to ask the AI.")

    full_prompt = f"Context from current call: {context}\n\nTask: {prompt}" if context else prompt

    try:
        if model in ["gpt4o", "auto"] and OPENAI_API_KEY:
            result = call_openai(full_prompt)
        elif model == "claude" and ANTHROPIC_API_KEY:
            result = call_claude(full_prompt)
        elif model == "perplexity" and PERPLEXITY_API_KEY:
            result = call_perplexity(full_prompt)
        elif OPENAI_API_KEY:
            result = call_openai(full_prompt)
        else:
            result = "AI model not configured. Add API keys to the server."

        return vapi_response(result)

    except Exception as e:
        return vapi_response(f"AI query failed: {str(e)}")

# ─────────────────────────────────────────
# TOOL 4: getLiveData
# ─────────────────────────────────────────
@app.route("/getLiveData", methods=["POST"])
def get_live_data():
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
            result = get_stock_news(query)
        elif data_type == "real_estate":
            result = get_real_estate(query)
        else:
            # Fall back to web search
            result = serper_search(f"{data_type} {query} live data today")

        return vapi_response(result)

    except Exception as e:
        return vapi_response(f"Could not fetch live data: {str(e)}")

# ─────────────────────────────────────────
# TOOL 5: lookupLead
# ─────────────────────────────────────────
@app.route("/lookupLead", methods=["POST"])
def lookup_lead():
    data = request.get_json(force=True)
    args = extract_args(data)
    name = args.get("name", "")
    city = args.get("city", "")
    industry = args.get("industry", "")
    goal = args.get("goal", "contact info")

    if not name:
        return vapi_response("I need a name to look up.")

    results = []

    try:
        # Search for company/person info
        search_query = f"{name} {city} {industry}".strip()
        search_result = serper_search(search_query)
        results.append(f"Web results for {name}:\n{search_result}")

        # If looking for email and Hunter.io is configured
        if "email" in goal.lower() and HUNTER_API_KEY:
            # Try to find domain from company name
            domain_search = serper_search(f"{name} official website domain")
            # Hunter domain search
            hunter_r = requests.get(
                f"https://api.hunter.io/v2/domain-search",
                params={"company": name, "api_key": HUNTER_API_KEY},
                timeout=8
            )
            if hunter_r.status_code == 200:
                hunter_data = hunter_r.json().get("data", {})
                emails = hunter_data.get("emails", [])[:3]
                if emails:
                    email_list = [f"{e.get('value')} ({e.get('type')})" for e in emails]
                    results.append(f"Emails found: {', '.join(email_list)}")

        return vapi_response("\n\n".join(results))

    except Exception as e:
        return vapi_response(f"Lookup failed: {str(e)}")

# ─────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────

def extract_args(data):
    """Extract tool arguments from Vapi webhook payload"""
    # Vapi format: {"message": {"toolCalls": [{"function": {"arguments": {...}}}]}}
    try:
        tool_calls = data.get("message", {}).get("toolCalls", [])
        if tool_calls:
            args = tool_calls[0].get("function", {}).get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)
            return args
    except:
        pass
    # Fallback: args at top level
    return data

def vapi_response(result_text):
    """Format response for Vapi tool call"""
    return jsonify({
        "results": [{"toolCallId": "imperium", "result": result_text}]
    })

def serper_search(query):
    """Run a Google search via Serper.dev"""
    if not SERPER_API_KEY:
        return "Search not configured (no Serper API key)"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    r = requests.post("https://google.serper.dev/search", headers=headers,
                      json={"q": query, "num": 4}, timeout=8)
    organic = r.json().get("organic", [])
    answer = r.json().get("answerBox", {}).get("answer", "")
    lines = []
    if answer:
        lines.append(answer)
    for item in organic[:3]:
        lines.append(f"• {item.get('title')}: {item.get('snippet', '')}")
    return "\n".join(lines) or "No results."

def gpt_summarize(content, goal):
    """Summarize webpage content with GPT-4o"""
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a research assistant. Summarize the provided content concisely and extract what's relevant to the user's goal. Be brief — 2-4 sentences max."},
            {"role": "user", "content": f"Goal: {goal}\n\nContent:\n{content}"}
        ],
        "max_tokens": 300
    }
    r = requests.post("https://api.openai.com/v1/chat/completions",
                      headers=headers, json=body, timeout=12)
    return r.json()["choices"][0]["message"]["content"]

def call_openai(prompt):
    """Call GPT-4o"""
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant supporting a sales agent on a live call. Be concise, accurate, and business-focused. Keep answers under 100 words."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 400
    }
    r = requests.post("https://api.openai.com/v1/chat/completions",
                      headers=headers, json=body, timeout=15)
    return r.json()["choices"][0]["message"]["content"]

def call_claude(prompt):
    """Call Claude"""
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    body = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 400,
        "messages": [{"role": "user", "content": prompt}]
    }
    r = requests.post("https://api.anthropic.com/v1/messages",
                      headers=headers, json=body, timeout=15)
    return r.json()["content"][0]["text"]

def call_perplexity(prompt):
    """Call Perplexity"""
    headers = {"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": "llama-3.1-sonar-large-128k-online",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 400
    }
    r = requests.post("https://api.perplexity.ai/chat/completions",
                      headers=headers, json=body, timeout=15)
    return r.json()["choices"][0]["message"]["content"]

def get_crypto(query):
    """Get live crypto price from CoinGecko (free, no key)"""
    coin_map = {
        "bitcoin": "bitcoin", "btc": "bitcoin",
        "ethereum": "ethereum", "eth": "ethereum",
        "solana": "solana", "sol": "solana",
        "xrp": "ripple", "ripple": "ripple",
        "cardano": "cardano", "ada": "cardano"
    }
    coin_id = coin_map.get(query.lower(), query.lower().replace(" ", "-"))
    r = requests.get(
        f"https://api.coingecko.com/api/v3/simple/price",
        params={"ids": coin_id, "vs_currencies": "usd", "include_24hr_change": "true"},
        timeout=8
    )
    data = r.json()
    if coin_id in data:
        price = data[coin_id]["usd"]
        change = data[coin_id].get("usd_24h_change", 0)
        direction = "↑" if change > 0 else "↓"
        return f"{query.upper()}: ${price:,.2f} ({direction}{abs(change):.1f}% today)"
    return f"Could not find price for {query}"

def get_weather(query):
    """Get live weather"""
    if WEATHER_API_KEY:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": query, "appid": WEATHER_API_KEY, "units": "imperial"},
            timeout=8
        )
        if r.status_code == 200:
            d = r.json()
            temp = d["main"]["temp"]
            feels = d["main"]["feels_like"]
            desc = d["weather"][0]["description"]
            return f"{query}: {temp}°F, feels like {feels}°F, {desc}"
    # Fallback to search
    return serper_search(f"current weather {query} today temperature")

def get_news(query):
    """Get live news"""
    if NEWS_API_KEY:
        r = requests.get(
            "https://newsapi.org/v2/everything",
            params={"q": query, "sortBy": "publishedAt", "pageSize": 3, "apiKey": NEWS_API_KEY},
            timeout=8
        )
        articles = r.json().get("articles", [])
        if articles:
            lines = [f"• {a['title']} ({a['source']['name']})" for a in articles[:3]]
            return "Latest news:\n" + "\n".join(lines)
    return serper_search(f"{query} news today")

def get_stock_news(query):
    """Get stock info via search"""
    return serper_search(f"{query} stock price today market cap")

def get_real_estate(query):
    """Get real estate market data via search"""
    return serper_search(f"real estate market {query} 2025 home prices median")

# ─────────────────────────────────────────
# RUN
# ─────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    print(f"""
╔══════════════════════════════════════════════╗
║      IMPERIUM WEBHOOK SERVER — PORT {port}     ║
║  Tools: searchWeb · browseWebsite · askAI   ║
║         getLiveData · lookupLead            ║
╚══════════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=port)
