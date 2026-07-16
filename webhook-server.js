/**
 * IMPERIUM WEBHOOK SERVER
 * Handles all 5 Vapi tool calls with real APIs
 * Deploy on: Railway, Render, or Vercel (free tier)
 *
 * Tools handled:
 *   searchWeb       → Serper.dev (Google Search API)
 *   browseWebsite   → Jina.ai reader API (free, no key needed)
 *   askAI           → OpenAI GPT-4o
 *   getLiveData     → Multiple free APIs
 *   lookupLead      → Hunter.io + Serper
 */

const express = require('express');
const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3000;

// ── ENV VARS (set these in your Railway/Render dashboard) ──
const SERPER_KEY   = process.env.SERPER_API_KEY;   // serper.dev - $50/month for 50k searches
const OPENAI_KEY   = process.env.OPENAI_API_KEY;   // openai.com
const HUNTER_KEY   = process.env.HUNTER_API_KEY;   // hunter.io free tier
const ANTHROPIC_KEY = process.env.ANTHROPIC_API_KEY; // claude

// ── HEALTH CHECK ──
app.get('/', (req, res) => {
  res.json({
    status: 'IMPERIUM WEBHOOK SERVER LIVE',
    version: '1.0',
    tools: ['searchWeb', 'browseWebsite', 'askAI', 'getLiveData', 'lookupLead']
  });
});

// ── MAIN ROUTER ── Vapi sends all tool calls here
app.post('/tools', async (req, res) => {
  const { name, parameters } = req.body;
  console.log(`[TOOL CALL] ${name}`, parameters);

  try {
    let result;
    switch (name) {
      case 'searchWeb':    result = await searchWeb(parameters);    break;
      case 'browseWebsite': result = await browseWebsite(parameters); break;
      case 'askAI':        result = await askAI(parameters);        break;
      case 'getLiveData':  result = await getLiveData(parameters);  break;
      case 'lookupLead':   result = await lookupLead(parameters);   break;
      default:
        return res.json({ result: `Unknown tool: ${name}` });
    }
    res.json({ result });
  } catch (err) {
    console.error(`[ERROR] ${name}:`, err.message);
    res.json({ result: `Tool error: ${err.message}` });
  }
});

// ── INDIVIDUAL ROUTES (alternative endpoints) ──
app.post('/imperium-search-web',    async (req, res) => { try { res.json({ result: await searchWeb(req.body) }) } catch(e) { res.json({ result: e.message }) }});
app.post('/imperium-browse-website',async (req, res) => { try { res.json({ result: await browseWebsite(req.body) }) } catch(e) { res.json({ result: e.message }) }});
app.post('/imperium-ask-ai',        async (req, res) => { try { res.json({ result: await askAI(req.body) }) } catch(e) { res.json({ result: e.message }) }});
app.post('/imperium-live-data',     async (req, res) => { try { res.json({ result: await getLiveData(req.body) }) } catch(e) { res.json({ result: e.message }) }});
app.post('/imperium-lookup-lead',   async (req, res) => { try { res.json({ result: await lookupLead(req.body) }) } catch(e) { res.json({ result: e.message }) }});

// ════════════════════════════════════════════════
// TOOL IMPLEMENTATIONS
// ════════════════════════════════════════════════

/**
 * searchWeb — Real Google search via Serper.dev
 */
async function searchWeb({ query, intent }) {
  const response = await fetch('https://google.serper.dev/search', {
    method: 'POST',
    headers: { 'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({ q: query, num: 5 })
  });
  const data = await response.json();

  const results = (data.organic || []).slice(0, 4).map(r =>
    `• ${r.title}: ${r.snippet}`
  ).join('\n');

  const answer = data.answerBox?.answer || data.answerBox?.snippet || '';

  return answer
    ? `${answer}\n\nMore context:\n${results}`
    : results || 'No results found.';
}

/**
 * browseWebsite — Read any URL via Jina.ai (free, no key)
 */
async function browseWebsite({ url, goal }) {
  const jinaUrl = `https://r.jina.ai/${url}`;
  const response = await fetch(jinaUrl, {
    headers: { 'Accept': 'text/plain' }
  });
  const text = await response.text();

  // Trim to first 2000 chars to keep response fast
  const trimmed = text.slice(0, 2000);
  return `Content from ${url}:\n\n${trimmed}`;
}

/**
 * askAI — Route to GPT-4o, Claude, Gemini, or Perplexity
 */
async function askAI({ model, prompt, context }) {
  const fullPrompt = context
    ? `Context from current call: ${context}\n\nTask: ${prompt}`
    : prompt;

  if (model === 'claude' && ANTHROPIC_KEY) {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': ANTHROPIC_KEY,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'claude-3-5-sonnet-20241022',
        max_tokens: 500,
        messages: [{ role: 'user', content: fullPrompt }]
      })
    });
    const data = await response.json();
    return data.content?.[0]?.text || 'No response from Claude.';
  }

  if (model === 'perplexity') {
    // Perplexity via OpenAI-compatible API
    const response = await fetch('https://api.perplexity.ai/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${process.env.PERPLEXITY_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'llama-3.1-sonar-large-128k-online',
        messages: [{ role: 'user', content: fullPrompt }],
        max_tokens: 500
      })
    });
    const data = await response.json();
    return data.choices?.[0]?.message?.content || 'No response from Perplexity.';
  }

  // Default: GPT-4o
  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${OPENAI_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      model: 'gpt-4o',
      messages: [
        {
          role: 'system',
          content: 'You are an expert AI assistant helping an Imperium AI agent during a live business call. Be concise, accurate, and actionable. Respond in 2-4 sentences max unless detail is needed.'
        },
        { role: 'user', content: fullPrompt }
      ],
      max_tokens: 500,
      temperature: 0.3
    })
  });
  const data = await response.json();
  return data.choices?.[0]?.message?.content || 'No response from GPT-4o.';
}

/**
 * getLiveData — Stocks, Crypto, Weather, News etc
 */
async function getLiveData({ dataType, query }) {
  switch (dataType) {
    case 'crypto': {
      const coin = query.toLowerCase().replace(/\s/g, '-');
      const r = await fetch(`https://api.coingecko.com/api/v3/simple/price?ids=${coin}&vs_currencies=usd&include_24hr_change=true`);
      const d = await r.json();
      const data = d[coin];
      if (!data) return `Could not find crypto data for ${query}.`;
      return `${query} price: $${data.usd?.toLocaleString()} USD | 24h change: ${data.usd_24h_change?.toFixed(2)}%`;
    }

    case 'weather': {
      const r = await fetch(`https://wttr.in/${encodeURIComponent(query)}?format=3`);
      const text = await r.text();
      return `Weather in ${text}`;
    }

    case 'stocks': {
      // Use Alpha Vantage free tier
      const symbol = query.toUpperCase().replace(/\s/g, '');
      const r = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1d&range=1d`);
      const d = await r.json();
      const price = d?.chart?.result?.[0]?.meta?.regularMarketPrice;
      const prev = d?.chart?.result?.[0]?.meta?.previousClose;
      const change = price && prev ? ((price - prev) / prev * 100).toFixed(2) : 'N/A';
      return price
        ? `${symbol}: $${price.toFixed(2)} | Change today: ${change}%`
        : `Could not get stock data for ${query}.`;
    }

    case 'news': {
      // Use Serper news search
      const r = await fetch('https://google.serper.dev/news', {
        method: 'POST',
        headers: { 'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json' },
        body: JSON.stringify({ q: query, num: 3 })
      });
      const d = await r.json();
      const items = (d.news || []).slice(0, 3).map(n => `• ${n.title} (${n.date})`).join('\n');
      return `Latest news on "${query}":\n${items}`;
    }

    case 'real_estate': {
      // Web search for real estate market data
      return await searchWeb({ query: `${query} real estate market data prices 2025`, intent: 'real estate research' });
    }

    case 'forex': {
      const r = await fetch(`https://open.er-api.com/v6/latest/USD`);
      const d = await r.json();
      const upper = query.toUpperCase();
      const rate = d.rates?.[upper];
      return rate
        ? `1 USD = ${rate} ${upper}`
        : `Exchange rate data for ${query} not found.`;
    }

    default:
      return await searchWeb({ query, intent: 'live data lookup' });
  }
}

/**
 * lookupLead — Research person/company mid-call
 */
async function lookupLead({ name, city, industry, goal }) {
  const searchQuery = [name, city, industry, 'contact email phone LinkedIn'].filter(Boolean).join(' ');

  // Run Google search
  const searchResult = await searchWeb({ query: searchQuery, intent: 'lead research' });

  // If we have Hunter.io for email finding
  if (HUNTER_KEY && goal?.includes('email')) {
    const domain = name.toLowerCase().replace(/\s+/g, '') + '.com';
    const r = await fetch(`https://api.hunter.io/v2/domain-search?domain=${domain}&api_key=${HUNTER_KEY}`);
    const d = await r.json();
    const emails = (d.data?.emails || []).slice(0, 3).map(e => e.value).join(', ');
    if (emails) return `Emails found for ${name}: ${emails}\n\nContext:\n${searchResult}`;
  }

  return `Research on ${name}:\n${searchResult}`;
}

// ── START ──
app.listen(PORT, () => {
  console.log(`
╔══════════════════════════════════════════════╗
║   IMPERIUM WEBHOOK SERVER — PORT ${PORT}       ║
║   Tools: searchWeb, browseWebsite, askAI,   ║
║          getLiveData, lookupLead            ║
╚══════════════════════════════════════════════╝
  `);
});

module.exports = app;
