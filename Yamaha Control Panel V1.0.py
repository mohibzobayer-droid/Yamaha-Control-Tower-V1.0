"""
Yamaha Regional SCM Control Tower
──────────────────────────────────
Features:
  • Live NewsAPI geopolitical sentiment → auto-populates risk scores
  • AI narrative via Anthropic Claude (2-sentence executive briefing)
  • Scenario Lab: "What if Hormuz closes for N days?" with cost/lead projections
  • Mobile-responsive layout with sidebar toggle
  • All API keys entered via sidebar (never hard-coded)
  • API key enable/disable toggles
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import json
import os
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════════════
# API KEY PERSISTENCE  (saved to .yamaha_api_keys.json next to script)
# ═══════════════════════════════════════════════════════════
_KEYS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".yamaha_api_keys.json")


def _load_saved_keys() -> dict:
    try:
        with open(_KEYS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_keys(news_key: str, claude_key: str, oil_key: str = ""):
    try:
        with open(_KEYS_FILE, "w") as f:
            json.dump({"news_api_key": news_key, "claude_api_key": claude_key,
                       "crude_oil_api_key": oil_key}, f)
    except Exception:
        pass
st.set_page_config(
    page_title="Yamaha Control Tower",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════
_SS_DEFAULTS = {
    "prev_risk":            None,
    "prev_global":          None,
    "prev_opt":             None,
    "news_cache":           None,
    "news_fetched_at":      None,
    "ai_narrative":         None,
    "ai_fetched_at":        None,
    "mobile":               False,
    "news_api_enabled":     True,
    "claude_enabled":       True,
    "oil_api_enabled":      True,
    "crude_oil_slider":     80,
    "oil_price_cache":      None,
    "oil_price_fetched_at": None,
}
for _k, _v in _SS_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# Load persisted API keys from disk once per session
if "api_keys_loaded" not in st.session_state:
    _disk = _load_saved_keys()
    st.session_state["_news_api_key"]      = _disk.get("news_api_key",      "")
    st.session_state["_claude_api_key"]    = _disk.get("claude_api_key",    "")
    st.session_state["_crude_oil_api_key"] = _disk.get("crude_oil_api_key", "")
    st.session_state["api_keys_loaded"] = True

# ═══════════════════════════════════════════════════════════
# DESIGN SYSTEM
# ═══════════════════════════════════════════════════════════
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,300&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

_CSS = """
:root {
    --glass-bg:       rgba(255,255,255,0.04);
    --glass-bg-hover: rgba(255,255,255,0.07);
    --glass-border:   rgba(255,255,255,0.08);
    --glass-blur:     blur(22px);
    --accent:   #e8ff47; --accent-glow:  rgba(232,255,71,0.25);
    --red:      #ff4444; --red-glow:     rgba(255,68,68,0.25);
    --green:    #00e5a0; --green-glow:   rgba(0,229,160,0.2);
    --amber:    #ffb020; --amber-glow:   rgba(255,176,32,0.2);
    --blue:     #3b6bff;
    --text:     #f0f4ff; --text-muted:   rgba(240,244,255,0.38);
    --bg:       #07090f; --radius: 14px;
}
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
    background: var(--bg) !important;
    color: var(--text) !important;
}
.stApp {
    background:
        radial-gradient(ellipse 70% 55% at 8% 0%,   rgba(50,70,200,0.13)  0%, transparent 60%),
        radial-gradient(ellipse 50% 45% at 92% 100%, rgba(0,229,160,0.08)  0%, transparent 60%),
        radial-gradient(ellipse 40% 35% at 50% 50%,  rgba(232,255,71,0.03) 0%, transparent 70%),
        #07090f !important;
}
@keyframes fadeUp    { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:translateY(0)} }
@keyframes fadeIn    { from{opacity:0} to{opacity:1} }
@keyframes blink     { 0%,100%{opacity:1} 50%{opacity:0.25} }
@keyframes glow-pulse{ 0%,100%{opacity:0.65} 50%{opacity:1} }

.fade-s1{animation:fadeUp .5s .00s ease both} .fade-s2{animation:fadeUp .5s .07s ease both}
.fade-s3{animation:fadeUp .5s .14s ease both} .fade-s4{animation:fadeUp .5s .21s ease both}
.fade-s5{animation:fadeUp .5s .28s ease both} .fade-s6{animation:fadeUp .5s .35s ease both}
.fade-s7{animation:fadeUp .5s .42s ease both} .fade-s8{animation:fadeUp .5s .49s ease both}

[data-testid="stSidebar"] {
    background: rgba(7,9,15,0.93) !important;
    backdrop-filter: var(--glass-blur) !important;
    border-right: 1px solid var(--glass-border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }
[data-testid="stSidebar"] [data-baseweb="slider"] [role="slider"] {
    background: var(--accent) !important;
    box-shadow: 0 0 10px var(--accent-glow) !important;
}
[data-testid="stSidebar"] input[type="password"],
[data-testid="stSidebar"] input[type="text"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.72rem !important;
}
[data-testid="metric-container"] {
    background: var(--glass-bg) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius) !important;
    backdrop-filter: var(--glass-blur) !important;
    padding: 20px 22px !important;
    transition: background .25s, box-shadow .25s, border-color .25s !important;
    animation: fadeUp .5s ease both !important;
}
[data-testid="metric-container"]:hover {
    background: var(--glass-bg-hover) !important;
    border-color: rgba(255,255,255,0.14) !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4) !important;
}
[data-testid="stMetricValue"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 1.65rem !important; font-weight: 500 !important;
    color: var(--text) !important; letter-spacing: -0.02em !important;
}
[data-testid="stMetricLabel"] {
    font-size: .63rem !important; letter-spacing: .13em !important;
    text-transform: uppercase !important; color: var(--text-muted) !important;
}
[data-testid="stMetricDelta"] {
    font-family: 'DM Mono', monospace !important; font-size: .73rem !important;
}
[data-testid="stAlert"] {
    background: var(--glass-bg) !important; border-radius: var(--radius) !important;
    backdrop-filter: var(--glass-blur) !important; border-width: 1px !important;
    animation: fadeUp .5s .1s ease both !important;
}
[data-testid="stExpander"] {
    background: var(--glass-bg) !important; border-radius: var(--radius) !important;
    border: 1px solid var(--glass-border) !important;
    backdrop-filter: var(--glass-blur) !important;
}
[data-testid="stDataFrame"] {
    border-radius: var(--radius) !important; overflow: hidden !important;
    border: 1px solid var(--glass-border) !important;
    animation: fadeUp .5s .3s ease both !important;
}
[data-testid="stPlotlyChart"] { animation: fadeUp .5s .2s ease both; }
[data-testid="stSelectbox"] > div, [data-testid="stSlider"] { background: transparent !important; }
::-webkit-scrollbar{width:3px;height:3px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:99px}
.main .block-container {
    padding-top: 2.5rem !important; padding-bottom: 3rem !important;
    max-width: 1300px !important;
}
hr { border-color: var(--glass-border) !important; }
.stCaption, small { color:var(--text-muted) !important; font-size:.7rem !important; }
.section-label {
    font-family: 'DM Mono', monospace; font-size: .6rem; letter-spacing: .16em;
    color: rgba(240,244,255,0.32); text-transform: uppercase; margin: 28px 0 14px 0;
}
.ai-card {
    background: linear-gradient(135deg, rgba(59,107,255,0.08) 0%, rgba(0,229,160,0.06) 100%);
    border: 1px solid rgba(59,107,255,0.2); border-radius: var(--radius);
    padding: 20px 24px; margin-bottom: 12px;
    backdrop-filter: var(--glass-blur); position: relative; overflow: hidden;
}
.ai-card::before {
    content:''; position:absolute; left:0; top:0; bottom:0; width:3px;
    background: linear-gradient(180deg, #3b6bff, #00e5a0); border-radius: 3px 0 0 3px;
}
.news-pill {
    display: inline-flex; align-items: center; gap: 8px;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
    border-radius: 8px; padding: 8px 14px; margin: 4px 0;
    width: 100%; box-sizing: border-box; transition: background .2s, border-color .2s;
}
.news-pill:hover { background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.12); }
.feed-badge {
    display:inline-flex; align-items:center; gap:5px; border-radius:99px;
    padding: 2px 9px; font-size:0.58rem; font-family:'DM Mono',monospace; letter-spacing:0.1em;
}
.feed-live { background:rgba(0,229,160,0.07); border:1px solid rgba(0,229,160,0.2); color:#00e5a0; }
.feed-demo { background:rgba(255,176,32,0.07); border:1px solid rgba(255,176,32,0.2); color:#ffb020; }
.feed-dot  { width:6px; height:6px; border-radius:50%; display:inline-block; }
.feed-dot-green { background:#00e5a0; box-shadow:0 0 6px rgba(0,229,160,0.9); animation:blink 1.8s ease-in-out infinite; }
.feed-dot-amber { background:#ffb020; }
@media (max-width: 768px) {
    .main .block-container { padding: 0.8rem !important; max-width: 100% !important; }
    h1 { font-size: 1.55rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.25rem !important; }
    [data-testid="column"] { min-width: 100% !important; flex: 0 0 100% !important; }
    .ai-card { padding: 14px 16px !important; }
}
"""

st.markdown(f"""
<script>
(function(){{
    var s = document.createElement('style');
    s.textContent = {repr(_CSS)};
    document.head.appendChild(s);
    var svgNS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(svgNS,'svg');
    svg.setAttribute('viewBox','0 0 256 256');
    svg.setAttribute('xmlns','http://www.w3.org/2000/svg');
    var f = document.createElementNS(svgNS,'filter');
    f.setAttribute('id','n');
    var t = document.createElementNS(svgNS,'feTurbulence');
    t.setAttribute('type','fractalNoise'); t.setAttribute('baseFrequency','0.85');
    t.setAttribute('numOctaves','4'); t.setAttribute('stitchTiles','stitch');
    f.appendChild(t);
    var r = document.createElementNS(svgNS,'rect');
    r.setAttribute('width','100%'); r.setAttribute('height','100%');
    r.setAttribute('filter','url(#n)');
    svg.appendChild(f); svg.appendChild(r);
    var ns = document.createElement('style');
    ns.textContent = '.stApp::after{{content:"";position:fixed;inset:0;pointer-events:none;z-index:9999;opacity:0.025;background-image:url("data:image/svg+xml,' + encodeURIComponent(new XMLSerializer().serializeToString(svg)) + '");background-size:180px;}}';
    document.head.appendChild(ns);
}})();
</script>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# SHARED PLOTLY THEME
# ═══════════════════════════════════════════════════════════
PLOTLY_BASE = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(255,255,255,0.015)",
    font=dict(color="#64748b", family="DM Sans"),
    margin=dict(l=16, r=16, t=36, b=16),
    height=260, showlegend=False,
)

# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════
_NEG_KW = ["attack","block","clos","escalat","conflict","war","risk","threat",
           "crisis","seiz","fire","strike","sanction","tension","danger"]
_POS_KW = ["safe","stable","calm","reopen","resum","ceasefire","resolve","normal"]


def _sentiment_score(text: str) -> float:
    t   = text.lower()
    neg = sum(1 for w in _NEG_KW if w in t)
    pos = sum(1 for w in _POS_KW if w in t)
    return min(100, max(0, (neg - pos) * 12 + 15))


def fetch_news(api_key: str):
    now     = datetime.utcnow()
    cached  = st.session_state.news_cache
    fetched = st.session_state.news_fetched_at
    if cached and fetched and (now - fetched).total_seconds() < 300:
        return cached
    # NewsAPI free tier: /v2/everything requires a `from` date (max 30 days back)
    from_date = (now - timedelta(days=29)).strftime("%Y-%m-%d")
    queries = {
        "hormuz":  "Strait of Hormuz shipping blockade",
        "redsea":  "Red Sea shipping attack Houthi",
        "general": "war risk shipping insurance Middle East",
    }
    all_articles, scores = [], {}
    try:
        for topic, q in queries.items():
            r = requests.get(
                "https://newsapi.org/v2/everything",
                params={"q": q, "language": "en", "sortBy": "publishedAt",
                        "pageSize": 5, "from": from_date, "apiKey": api_key},
                timeout=8,
            )
            # NewsAPI returns HTTP 200 even for API-level errors — must check JSON status
            payload = r.json()
            if r.status_code != 200 or payload.get("status") == "error":
                err_code = payload.get("code", r.status_code)
                err_msg  = payload.get("message", "Unknown error")
                st.session_state["_news_api_last_error"] = f"{err_code}: {err_msg}"
                return None
            articles    = payload.get("articles", [])
            topic_texts = [a.get("title","") + " " + (a.get("description") or "") for a in articles]
            scores[topic] = np.mean([_sentiment_score(t) for t in topic_texts]) if topic_texts else 20.0
            all_articles.extend(articles[:3])
        headlines = [
            {"title":     a.get("title",""),
             "source":    a.get("source",{}).get("name",""),
             "url":       a.get("url","#"),
             "sentiment": _sentiment_score(a.get("title","") + " " + (a.get("description") or ""))}
            for a in all_articles[:6]
        ]
        result = {
            "hormuz_score":  scores.get("hormuz",  20.0),
            "redsea_score":  scores.get("redsea",  20.0),
            "insurance_est": min(1.0, scores.get("general", 20.0) / 100 * 0.6 + 0.05),
            "headlines":     headlines,
        }
        st.session_state.news_cache           = result
        st.session_state.news_fetched_at      = now
        st.session_state["_news_api_last_error"] = None   # clear any previous error
        return result
    except Exception as e:
        st.session_state["_news_api_last_error"] = str(e)
        return None


def get_ai_narrative(risk_score, status_label, global_alloc, regional_alloc,
                     lead_time, headlines, api_key: str):
    now     = datetime.utcnow()
    cached  = st.session_state.ai_narrative
    fetched = st.session_state.ai_fetched_at
    if cached and fetched and (now - fetched).total_seconds() < 180:
        return cached
    headline_str = "; ".join(h["title"] for h in (headlines or [])[:3]) or "No live headlines."
    prompt = f"""You are a senior supply chain risk analyst for Yamaha Motor Co.
Provide a 2-sentence executive briefing — plain English, no jargon, no bullet points.
Sentence 1: what is specifically driving the current risk level.
Sentence 2: the recommended action for the logistics team right now.

Current system state:
- Risk Score: {risk_score:.1f}/100  - Status: {status_label}
- Global (Hormuz) allocation: {global_alloc}%
- Regional (Turkey/Morocco) allocation: {regional_alloc}%
- Lead Time: {lead_time}
- Live news signals: {headline_str}

Write exactly 2 sentences. Be specific and decisive."""
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 160,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=10,
        )
        if r.status_code == 200:
            text = r.json()["content"][0]["text"].strip()
            st.session_state.ai_narrative  = text
            st.session_state.ai_fetched_at = now
            return text
        return None
    except Exception:
        return None


def _fallback_narrative(risk_score, status_label, global_alloc, lead_time):
    if status_label == "CRITICAL":
        return (
            f"Hormuz Strait disruption has pushed the composite risk score to {risk_score:.0f}/100, "
            f"eliminating global ocean freight as a viable near-term option. "
            f"The logistics team should immediately confirm 100% volume commitment to Route C (Suez Canal & Red Sea) and "
            f"Route D (West Africa Atlantic Coast) sea lanes, and engage freight forwarders to secure vessel capacity within 48 hours."
        )
    elif status_label == "WARNING":
        return (
            f"Elevated war-risk premiums are eroding margin on Hormuz-routed shipments, "
            f"reflected in a risk score of {risk_score:.0f}/100 with {global_alloc}% still on global routes. "
            f"Recommend accelerating the shift to Morocco and Turkey lanes to lock in stable overland rates "
            f"before premiums escalate further."
        )
    else:
        return (
            f"Supply chain conditions are nominal with a risk score of {risk_score:.0f}/100 "
            f"and {global_alloc}% of volume routed via standard ocean freight at {lead_time}. "
            f"Continue monitoring Hormuz traffic and review war-risk premium benchmarks weekly "
            f"to detect early deterioration."
        )


def fetch_crude_oil_price(api_key: str):
    """Fetch latest WTI crude price via Alpha Vantage (free tier, daily interval).
    Cached for 30 minutes to stay within free-tier limits."""
    now     = datetime.utcnow()
    cached  = st.session_state.get("oil_price_cache")
    fetched = st.session_state.get("oil_price_fetched_at")
    if cached is not None and fetched and (now - fetched).total_seconds() < 1800:
        return cached
    try:
        r = requests.get(
            "https://www.alphavantage.co/query",
            params={"function": "WTI", "interval": "daily", "apikey": api_key},
            timeout=5,
        )
        if r.status_code == 200:
            data  = r.json()
            price = float(data["data"][0]["value"])
            st.session_state["oil_price_cache"]      = price
            st.session_state["oil_price_fetched_at"] = now
            return price
    except Exception:
        pass
    return None


# ═══════════════════════════════════════════════════════════
# SCENARIO ENGINE
# ═══════════════════════════════════════════════════════════
_SCENARIO_PARAMS = {
    "Hormuz Closure":     dict(base_disruption=0.85, recovery_days=21, cost_scramble=280),
    "Red Sea Escalation": dict(base_disruption=0.55, recovery_days=14, cost_scramble=180),
    "Full ME Conflict":   dict(base_disruption=1.00, recovery_days=45, cost_scramble=450),
    "Custom":             dict(base_disruption=0.60, recovery_days=20, cost_scramble=200),
}
BASE_COST_GLOBAL   = 850
BASE_COST_REGIONAL = 990
BASE_LEAD_GLOBAL   = 32
BASE_LEAD_REGIONAL = 18


def compute_scenario(scenario_type: str, duration_days: int, severity_pct: float):
    p          = _SCENARIO_PARAMS[scenario_type]
    sev        = severity_pct / 100 * p["base_disruption"]
    total_days = duration_days + p["recovery_days"]
    rows       = []
    for day in range(total_days + 1):
        if day <= 3:
            d = sev * (day / 3)
        elif day <= duration_days:
            d = sev
        else:
            d = sev * max(0.0, 1.0 - (day - duration_days) / p["recovery_days"])
        g_alloc = max(0.0, 70.0 * (1.0 - d / sev)) if sev > 0 else 70.0
        r_alloc = 100 - g_alloc
        cost    = BASE_COST_GLOBAL * (g_alloc / 100) + BASE_COST_REGIONAL * (r_alloc / 100)
        if day <= 7:
            cost += p["cost_scramble"] * d * max(0, 1 - day / 7 * 0.6)
        lead = BASE_LEAD_GLOBAL * (g_alloc / 100) + BASE_LEAD_REGIONAL * (r_alloc / 100)
        if day <= 3:
            lead += 8 * d
        rows.append({
            "Day":           day,
            "Date":          datetime.today() + timedelta(days=day),
            "Cost/Unit ($)": round(cost, 2),
            "Lead Time (d)": round(lead, 1),
            "Global (%)":    round(g_alloc, 1),
            "Regional (%)":  round(r_alloc, 1),
            "Disruption":    round(d, 3),
        })
    df = pd.DataFrame(rows)
    df["Cumulative Extra Cost ($M)"] = (
        (df["Cost/Unit ($)"] - BASE_COST_GLOBAL) * 5000 / 1_000_000
    ).cumsum().round(2)
    return df


# ═══════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════
sb = st.sidebar

sb.markdown("""
<div style="font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:.18em;
     color:rgba(232,255,71,0.65);text-transform:uppercase;margin-bottom:6px;">
     ◈ &nbsp;Control Tower
</div>""", unsafe_allow_html=True)

mobile_view = sb.toggle("📱 Mobile layout", value=st.session_state.mobile)
st.session_state.mobile = mobile_view

sb.markdown("<hr style='border-color:rgba(255,255,255,0.06);margin:12px 0'>", unsafe_allow_html=True)

# ── API Keys with enable/disable toggles ──
with sb.expander("🔑  API Keys", expanded=False):

    # NewsAPI row
    col_n1, col_n2 = st.columns([3, 1])
    with col_n1:
        st.markdown("<p style='font-size:.75rem;margin:0;padding-top:6px;color:rgba(240,244,255,0.6);'>NewsAPI</p>",
                    unsafe_allow_html=True)
    with col_n2:
        news_enabled = st.toggle(" ", value=st.session_state.news_api_enabled,
                                 key="news_toggle", help="Enable / disable NewsAPI live feed")
        st.session_state.news_api_enabled = news_enabled

    news_api_key_input = st.text_input(
        "NewsAPI key", type="password", placeholder="Paste NewsAPI key…",
        value=st.session_state["_news_api_key"],
        help="newsapi.org — free tier works", label_visibility="collapsed",
        disabled=not news_enabled,
    )
    if news_api_key_input:
        st.session_state["_news_api_key"] = news_api_key_input
        _save_keys(news_api_key_input,
                   st.session_state.get("_claude_api_key", ""),
                   st.session_state.get("_crude_oil_api_key", ""))
    news_api_key = st.session_state["_news_api_key"]
    news_color = "#00e5a0" if news_enabled else "#ff4444"
    news_status = "🟢 ENABLED" if news_enabled else "🔴 DISABLED"
    st.markdown(f"<p style='font-family:DM Mono,monospace;font-size:.6rem;color:{news_color};margin:2px 0 4px 0;'>{news_status}</p>",
                unsafe_allow_html=True)
    _news_err = st.session_state.get("_news_api_last_error")
    if _news_err and news_enabled:
        st.markdown(f"<p style='font-family:DM Mono,monospace;font-size:.58rem;"
                    f"color:#ff4444;margin:0 0 12px 0;'>⚠ {_news_err}</p>",
                    unsafe_allow_html=True)
    else:
        st.markdown("<div style='margin-bottom:12px'></div>", unsafe_allow_html=True)

    # Anthropic row
    col_a1, col_a2 = st.columns([3, 1])
    with col_a1:
        st.markdown("<p style='font-size:.75rem;margin:0;padding-top:6px;color:rgba(240,244,255,0.6);'>Anthropic (Claude)</p>",
                    unsafe_allow_html=True)
    with col_a2:
        claude_enabled = st.toggle(" ", value=st.session_state.claude_enabled,
                                   key="claude_toggle", help="Enable / disable Claude AI briefing")
        st.session_state.claude_enabled = claude_enabled

    claude_api_key_input = st.text_input(
        "Anthropic key", type="password", placeholder="Paste Anthropic key…",
        value=st.session_state["_claude_api_key"],
        help="console.anthropic.com", label_visibility="collapsed",
        disabled=not claude_enabled,
    )
    if claude_api_key_input:
        st.session_state["_claude_api_key"] = claude_api_key_input
        _save_keys(st.session_state.get("_news_api_key", ""),
                   claude_api_key_input,
                   st.session_state.get("_crude_oil_api_key", ""))
    claude_api_key = st.session_state["_claude_api_key"]
    claude_color  = "#00e5a0" if claude_enabled else "#ff4444"
    claude_status = "🟢 ENABLED" if claude_enabled else "🔴 DISABLED"
    st.markdown(f"<p style='font-family:DM Mono,monospace;font-size:.6rem;color:{claude_color};margin:2px 0 12px 0;'>{claude_status}</p>",
                unsafe_allow_html=True)

    # Crude Oil (Alpha Vantage) row
    col_o1, col_o2 = st.columns([3, 1])
    with col_o1:
        st.markdown("<p style='font-size:.75rem;margin:0;padding-top:6px;color:rgba(240,244,255,0.6);'>Crude Oil (Alpha Vantage)</p>",
                    unsafe_allow_html=True)
    with col_o2:
        oil_api_enabled = st.toggle(" ", value=st.session_state.oil_api_enabled,
                                    key="oil_toggle", help="Enable / disable live WTI crude oil price feed")
        st.session_state.oil_api_enabled = oil_api_enabled

    crude_oil_api_key_input = st.text_input(
        "Alpha Vantage key", type="password", placeholder="Paste Alpha Vantage key…",
        value=st.session_state["_crude_oil_api_key"],
        help="alphavantage.co — free tier (25 req/day). Used for live WTI crude price.",
        label_visibility="collapsed",
        disabled=not oil_api_enabled,
    )
    if crude_oil_api_key_input:
        st.session_state["_crude_oil_api_key"] = crude_oil_api_key_input
        _save_keys(st.session_state.get("_news_api_key", ""),
                   st.session_state.get("_claude_api_key", ""),
                   crude_oil_api_key_input)
    crude_oil_api_key = st.session_state["_crude_oil_api_key"]
    oil_key_color  = "#00e5a0" if oil_api_enabled else "#ff4444"
    oil_key_status = "🟢 ENABLED" if oil_api_enabled else "🔴 DISABLED"
    st.markdown(f"<p style='font-family:DM Mono,monospace;font-size:.6rem;color:{oil_key_color};margin:2px 0 0 0;'>{oil_key_status}</p>",
                unsafe_allow_html=True)

    # Saved-key indicator + clear button
    has_saved = bool(st.session_state.get("_news_api_key") or
                     st.session_state.get("_claude_api_key") or
                     st.session_state.get("_crude_oil_api_key"))
    if has_saved:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown("<p style='font-family:DM Mono,monospace;font-size:.58rem;"
                    "color:rgba(0,229,160,0.55);margin:0 0 6px 0;'>✓ Keys saved to disk</p>",
                    unsafe_allow_html=True)
        if st.button("🗑  Clear saved keys", use_container_width=True):
            st.session_state["_news_api_key"]      = ""
            st.session_state["_claude_api_key"]    = ""
            st.session_state["_crude_oil_api_key"] = ""
            _save_keys("", "", "")
            st.rerun()

    # Clear caches when disabled
    if not news_enabled:
        st.session_state.news_cache      = None
        st.session_state.news_fetched_at = None
    if not claude_enabled:
        st.session_state.ai_narrative  = None
        st.session_state.ai_fetched_at = None
    if not oil_api_enabled:
        st.session_state.oil_price_cache      = None
        st.session_state.oil_price_fetched_at = None

sb.markdown("""
<div style="font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:.15em;
     color:rgba(240,244,255,0.32);text-transform:uppercase;margin:14px 0 8px 0;">
     Signal Inputs
</div>
<p style="font-size:.72rem;color:rgba(240,244,255,0.32);line-height:1.6;margin:0 0 12px 0;">
    Live feeds override these when API keys are active.
    Sliders become manual overrides.
</p>""", unsafe_allow_html=True)

geo_risk_manual  = sb.slider("Hormuz Risk", 0, 100, 15,
                             help="Geopolitical disruption level at the Strait of Hormuz (0 = clear, 100 = fully blocked). Contributes 40% to the Risk Score.")
insurance_manual = sb.slider("War-Risk Premium", 0.0, 1.0, 0.125, step=0.05,
                             help="Shipping war-risk insurance surcharge as a fraction of 1.0 (e.g. 0.125 = 12.5%). Contributes 40% to Risk Score. At ≥0.40 alone triggers Critical status.")
red_sea_manual   = sb.slider("Red Sea Risk", 0, 100, 20,
                             help="Threat level in the Red Sea / Bab-el-Mandeb corridor (0 = calm, 100 = active attacks). Contributes 20% to the Risk Score.")

sb.markdown("<div style='border-top:1px solid rgba(255,255,255,0.06);margin:12px 0'></div>",
            unsafe_allow_html=True)
sb.markdown("""
<div style="font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:.15em;
     color:rgba(240,244,255,0.32);text-transform:uppercase;margin:0 0 8px 0;">
     Commodity Index
</div>""", unsafe_allow_html=True)
# key="crude_oil_slider" lets Streamlit manage session_state automatically —
# avoids the double-drag bug caused by manually writing value= + session_state sync.
crude_oil_manual = sb.slider("Crude Oil — WTI ($/bbl)", min_value=40, max_value=150,
                              step=1, key="crude_oil_slider",
                              help="Manual WTI crude price override ($40–$150/bbl). Above $80 adds up to 15 pts to the Risk Score. Overridden by live Alpha Vantage feed when key is active.")

if crude_oil_manual >= 110:
    oil_label, oil_color = "HIGH", "#ff4444"
elif crude_oil_manual >= 80:
    oil_label, oil_color = "ELEVATED", "#ffb020"
else:
    oil_label, oil_color = "NORMAL", "#00e5a0"
sb.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px;">
  <span style="font-family:'DM Mono',monospace;font-size:.72rem;
        color:rgba(240,244,255,0.65);">${crude_oil_manual} / bbl</span>
  <span style="font-family:'DM Mono',monospace;font-size:.58rem;
        color:{oil_color};letter-spacing:.1em;">{oil_label}</span>
</div>""", unsafe_allow_html=True)

sb.markdown("""
<div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:14px;margin-top:16px;">
  <div style="font-family:'DM Mono',monospace;font-size:.58rem;letter-spacing:.12em;
       color:rgba(240,244,255,0.2);text-transform:uppercase;margin-bottom:8px;">Threshold Guide</div>
  <div style="font-size:.7rem;line-height:2.1;">
    <span style="color:#ff4444;">■</span>&nbsp;<span style="color:rgba(240,244,255,0.42);">Critical > 75</span><br>
    <span style="color:#ffb020;">■</span>&nbsp;<span style="color:rgba(240,244,255,0.42);">Warning > 40</span><br>
    <span style="color:#00e5a0;">■</span>&nbsp;<span style="color:rgba(240,244,255,0.42);">Stable ≤ 40</span>
  </div>
</div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# LIVE DATA LAYER
# ═══════════════════════════════════════════════════════════
news_data  = fetch_news(news_api_key) if (news_api_key and news_enabled) else None
live_feeds = news_data is not None

if live_feeds:
    geo_risk        = news_data["hormuz_score"]
    red_sea_risk    = news_data["redsea_score"]
    insurance_spike = news_data["insurance_est"]
    feed_label      = "LIVE"
    feed_class      = "feed-live"
    feed_dot_class  = "feed-dot-green"
else:
    geo_risk        = geo_risk_manual
    red_sea_risk    = red_sea_manual
    insurance_spike = insurance_manual
    feed_label      = "DEMO"
    feed_class      = "feed-demo"
    feed_dot_class  = "feed-dot-amber"

# Crude oil: live feed overrides slider when API key is active
_oil_live = fetch_crude_oil_price(crude_oil_api_key) if (crude_oil_api_key and oil_api_enabled) else None
if _oil_live is not None:
    crude_oil_price  = _oil_live
    oil_feed_live    = True
else:
    crude_oil_price  = float(crude_oil_manual)
    oil_feed_live    = False

# ═══════════════════════════════════════════════════════════
# DECISION ENGINE
# ═══════════════════════════════════════════════════════════
# Crude oil adds up to +15 pts when above the $80 neutral baseline (caps at $150).
oil_risk_contrib = max(0.0, (crude_oil_price - 80.0) / 70.0 * 15.0)
risk_score = ((geo_risk * 0.4) + ((insurance_spike / 1.0) * 100 * 0.4)
              + (red_sea_risk * 0.2) + oil_risk_contrib)
g75 = risk_score > 75 or insurance_spike >= 0.4
g40 = risk_score > 40

if g75:
    status_label, status_color = "CRITICAL", "#ff4444"
    global_alloc, regional_alloc = 0, 100
    lead_time  = "3–5 d"
    alert_msg  = "Hormuz blocked — Route C Suez Canal & Red Sea (Japan → Indian Ocean → Suez Canal → Turkey Mersin → Red Sea → Oman) and Route D West Africa Regional (Japan → Indian Ocean → Cape of Good Hope → Morocco → W.Africa) fully activated."
    alert_type = "error"
elif g40:
    status_label, status_color = "WARNING", "#ffb020"
    global_alloc, regional_alloc = 40, 60
    lead_time  = "15–20 d"
    alert_msg  = "Insurance premiums rising — Route B Strait of Gibraltar (Morocco→Algeciras→Europe, 1–2 d) primary; Route A Mediterranean Sea (Turkey Izmir→Europe, 3–5 d) as contingency."
    alert_type = "warning"
else:
    status_label, status_color = "STABLE", "#00e5a0"
    global_alloc, regional_alloc = 70, 30
    lead_time  = "30–35 d"
    alert_msg  = "Conditions nominal — Route A Mediterranean Sea (Turkey Izmir → Europe, 3–5 d) and Route E Global (Japan → Indian Ocean → Malacca → Arabian Sea → Hormuz → Arabian Gulf, 18–22 d) both active."
    alert_type = "success"

opt_score = 100 - (risk_score / 100 * 50)


def _delta(curr, prev):
    if prev is None: return None
    d = curr - prev
    return f"+{d:.1f}" if d > 0 else (f"{d:.1f}" if d < 0 else None)


risk_delta  = _delta(risk_score,   st.session_state.prev_risk)
opt_delta   = _delta(opt_score,    st.session_state.prev_opt)
alloc_delta = _delta(global_alloc, st.session_state.prev_global)
st.session_state.prev_risk   = risk_score
st.session_state.prev_global = global_alloc
st.session_state.prev_opt    = opt_score

now_str   = datetime.now().strftime("%H:%M:%S")
headlines = news_data["headlines"] if live_feeds else []

if claude_api_key and claude_enabled:
    narrative = get_ai_narrative(risk_score, status_label, global_alloc,
                                 regional_alloc, lead_time, headlines, claude_api_key)
    narrative = narrative or _fallback_narrative(risk_score, status_label, global_alloc, lead_time)
    ai_source = "Claude"
else:
    narrative = _fallback_narrative(risk_score, status_label, global_alloc, lead_time)
    ai_source = "Template"


def cols(ratios: list, gap="medium"):
    if st.session_state.mobile:
        return [st.container() for _ in ratios]
    return st.columns(ratios, gap=gap)


# ═══════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════
ai_badge = ""
if claude_api_key and claude_enabled:
    ai_badge = "<span class='feed-badge feed-live' style='background:rgba(59,107,255,0.08);border-color:rgba(59,107,255,0.25);color:#3b6bff;'><span class='feed-dot' style='background:#3b6bff;'></span>AI</span>"

st.markdown(f"""
<div class="fade-s1" style="display:flex;align-items:flex-start;
     justify-content:space-between;margin-bottom:24px;flex-wrap:wrap;gap:14px;">
  <div>
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:7px;flex-wrap:wrap;">
      <span style="font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:.18em;
            color:rgba(232,255,71,0.6);text-transform:uppercase;">YMH — SCM v3.0</span>
      <span class="feed-badge {feed_class}">
        <span class="feed-dot {feed_dot_class}"></span>{feed_label}
      </span>{ai_badge}
    </div>
    <h1 style="font-size:2.05rem;font-weight:600;margin:0 0 4px 0;
        letter-spacing:-.04em;color:#f0f4ff;line-height:1.1;">Control Tower</h1>
    <p style="color:rgba(240,244,255,0.32);font-size:.77rem;margin:0;font-style:italic;">
        Supply chain routing &nbsp;·&nbsp; real-time geopolitical risk
    </p>
  </div>
  <div style="text-align:right;padding-top:4px;">
    <div style="display:inline-block;padding:8px 22px;border-radius:99px;
         background:rgba(255,255,255,0.03);border:1px solid {status_color}40;
         box-shadow:0 0 20px {status_color}28;animation:glow-pulse 2.8s ease-in-out infinite;">
      <span style="font-family:'DM Mono',monospace;font-size:.72rem;
            font-weight:500;letter-spacing:.13em;color:{status_color};">{status_label}</span>
    </div>
    <div style="font-family:'DM Mono',monospace;font-size:.58rem;
         color:rgba(240,244,255,0.18);margin-top:8px;letter-spacing:.08em;">
         {now_str} &nbsp;SGT
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# AI BRIEFING CARD
# ═══════════════════════════════════════════════════════════
claude_hint = "" if (claude_api_key and claude_enabled) else " · add & enable Anthropic key for live AI"
st.markdown(f"""
<div class="ai-card fade-s2">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
    <span style="font-family:'DM Mono',monospace;font-size:.58rem;letter-spacing:.15em;
          color:rgba(59,107,255,0.8);text-transform:uppercase;">AI Briefing</span>
    <span style="font-family:'DM Mono',monospace;font-size:.55rem;
          color:rgba(240,244,255,0.25);">— {ai_source}{claude_hint}</span>
  </div>
  <p style="font-size:.82rem;line-height:1.7;color:rgba(240,244,255,0.75);margin:0;">{narrative}</p>
</div>
""", unsafe_allow_html=True)

if   alert_type == "error":   st.error(alert_msg)
elif alert_type == "warning": st.warning(alert_msg)
else:                         st.success(alert_msg)

# ═══════════════════════════════════════════════════════════
# KPI ROW
# ═══════════════════════════════════════════════════════════
st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
k1, k2, k3, k4, k5 = cols([1, 1, 1, 1, 1], gap="small")
with k1:
    st.metric("Risk Score", f"{risk_score:.1f}", delta=risk_delta,
              help="Composite 0–100 score. Formula: 40% Hormuz risk + 40% war-risk premium + 20% Red Sea risk + crude oil bonus (up to +15 pts above $80). Triggers: >40 → Warning, >75 or premium ≥0.40 → Critical.")
with k2:
    st.metric("Global Alloc", f"{global_alloc}%", delta=alloc_delta,
              help="Share of total shipping volume routed via Hormuz (ocean freight). Stable = 70%, Warning = 40%, Critical = 0%. Delta shows change since last rerun.")
with k3:
    st.metric("Lead Time", lead_time,
              help="Estimated end-to-end delivery window for the current route mix. Stable = 30–35 d (ocean), Warning = 15–20 d (mixed), Critical = 3–5 d (full overland Turkey/Morocco).")
with k4:
    st.metric("Optimisation", f"{opt_score:.0f}%", delta=opt_delta,
              help="Routing efficiency index: 100% = fully optimal (zero disruption). Calculated as 100 − (Risk Score / 100 × 50), so a risk of 100 still preserves 50% efficiency via overland fallback.")
with k5:
    oil_delta_str = "🔴 HIGH" if crude_oil_price >= 110 else ("🟡 ELEVATED" if crude_oil_price >= 80 else "🟢 NORMAL")
    oil_src_tag   = " · LIVE" if oil_feed_live else " · MANUAL"
    st.metric("WTI Crude Oil", f"${crude_oil_price:.0f}/bbl", delta=f"{oil_delta_str}{oil_src_tag}",
              help=f"WTI crude futures price ($/bbl). Normal < $80, Elevated $80–$109, High ≥ $110. Adds up to +15 pts to Risk Score above the $80 baseline (currently +{oil_risk_contrib:.1f} pts). {'Live via Alpha Vantage.' if oil_feed_live else 'Using manual slider — add Alpha Vantage key for live feed.'}")

# ── Risk score & allocation logic summary ──
st.markdown(f"""
<div style="font-size:.68rem;color:rgba(240,244,255,0.28);font-family:'DM Mono',monospace;
     margin:8px 0 0 2px;letter-spacing:.03em;line-height:1.8;">
  Risk&nbsp;=&nbsp;Hormuz×0.4&nbsp;+&nbsp;Premium×0.4&nbsp;+&nbsp;RedSea×0.2&nbsp;+&nbsp;Oil&nbsp;bonus
  &nbsp;&nbsp;│&nbsp;&nbsp;
  Routing:&nbsp;≤40&nbsp;→&nbsp;70/30&nbsp;global/regional&nbsp;·&nbsp;>40&nbsp;→&nbsp;40/60&nbsp;·&nbsp;>75&nbsp;→&nbsp;0/100
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# NEWS FEED
# ═══════════════════════════════════════════════════════════
if live_feeds and headlines:
    st.markdown("""<div class="fade-s3"><div class="section-label">Live Intelligence Feed</div></div>""",
                unsafe_allow_html=True)
    for h in headlines[:4]:
        sentiment = h.get("sentiment", 50)
        dot_color = "#ff4444" if sentiment > 60 else ("#ffb020" if sentiment > 35 else "#00e5a0")
        st.markdown(f"""
        <a href="{h['url']}" target="_blank" style="text-decoration:none;">
          <div class="news-pill">
            <span style="width:7px;height:7px;border-radius:50%;background:{dot_color};
                  flex-shrink:0;box-shadow:0 0 5px {dot_color}77;"></span>
            <span style="font-size:.74rem;color:rgba(240,244,255,0.65);flex:1;
                  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{h['title']}</span>
            <span style="font-family:'DM Mono',monospace;font-size:.6rem;
                  color:rgba(240,244,255,0.3);flex-shrink:0;">{h['source']}</span>
          </div>
        </a>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# SIGNAL BARS + DONUT
# ═══════════════════════════════════════════════════════════
st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
sig_col, alloc_col = cols([1, 1])

with sig_col:
    st.markdown("""<div class="fade-s4"><div class="section-label">Signal Inputs</div>""",
                unsafe_allow_html=True)

    def signal_row(label, display_val, pct, bar_color, live=False):
        filled   = min(max(pct, 0), 100)
        live_tag = (f"<span style='font-family:DM Mono,monospace;font-size:.52rem;"
                    f"letter-spacing:.1em;color:{bar_color}88;margin-left:6px;'>LIVE</span>"
                    if live else "")
        st.markdown(f"""
        <div style="margin-bottom:20px;">
          <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:7px;">
            <span style="font-size:.78rem;color:rgba(240,244,255,0.5);">{label}{live_tag}</span>
            <span style="font-family:'DM Mono',monospace;font-size:.8rem;
                  color:{bar_color};font-weight:500;">{display_val}</span>
          </div>
          <div style="height:3px;background:rgba(255,255,255,0.06);border-radius:99px;overflow:hidden;">
            <div style="height:3px;width:{filled}%;
                 background:linear-gradient(90deg,{bar_color}66,{bar_color});
                 border-radius:99px;box-shadow:0 0 8px {bar_color}44;
                 transition:width .5s cubic-bezier(0.4,0,0.2,1);"></div>
          </div>
        </div>""", unsafe_allow_html=True)

    signal_row("Hormuz Risk",      f"{geo_risk:.0f} / 100",       geo_risk,              "#ff4444", live_feeds)
    signal_row("War-Risk Premium", f"{insurance_spike*100:.1f}%", insurance_spike * 100, "#ffb020", live_feeds)
    signal_row("Red Sea Risk",     f"{red_sea_risk:.0f} / 100",   red_sea_risk,          "#e8ff47", live_feeds)
    oil_bar_pct = min(100, max(0, (crude_oil_price - 40) / (150 - 40) * 100))
    signal_row("WTI Crude Oil",    f"${crude_oil_price:.0f}/bbl", oil_bar_pct,           "#a78bfa", oil_feed_live)
    st.markdown("</div>", unsafe_allow_html=True)

with alloc_col:
    st.markdown("""<div class="fade-s5"><div class="section-label">Volume Allocation</div></div>""",
                unsafe_allow_html=True)
    pie = go.Figure(go.Pie(
        labels=["Sea Routes (Med / Gibraltar)", "Overland / W.Africa"],
        values=[max(global_alloc, 0.001), regional_alloc],
        hole=0.74,
        marker=dict(colors=["#3b6bff", "#00e5a0"], line=dict(color="rgba(0,0,0,0)", width=0)),
        textinfo="none",
        hovertemplate="%{label}: <b>%{value}%</b><extra></extra>",
    ))
    pie.add_annotation(
        text=f"<b>{regional_alloc}%</b><br><span style='font-size:11px'>Regional</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=22, color="#00e5a0", family="DM Mono"),
    )
    pie.update_layout(**{
        **PLOTLY_BASE, "height": 230,
        "margin": dict(l=0,r=0,t=0,b=0), "showlegend": True,
        "legend": dict(orientation="v", x=1.02, y=0.5,
                       font=dict(size=11, color="#64748b"), bgcolor="rgba(0,0,0,0)"),
    })
    st.plotly_chart(pie, use_container_width=True)

# ═══════════════════════════════════════════════════════════
# TREND CHART
# ═══════════════════════════════════════════════════════════
st.markdown('<div style="height:20px"></div><div class="fade-s6"><div class="section-label">30-Day Risk Trend</div></div>',
            unsafe_allow_html=True)
dates      = pd.date_range(start="2024-09-01", periods=30, freq="D")
trend_vals = np.clip(risk_score + np.sin(np.linspace(0, 4*np.pi, 30)) * 15, 0, 100)
trend_fig  = go.Figure()
trend_fig.add_trace(go.Scatter(
    x=dates, y=trend_vals, mode="lines",
    line=dict(color="#e8ff47", width=2.5),
    fill="tozeroy", fillcolor="rgba(232,255,71,0.05)",
    hovertemplate="%{x|%b %d}: <b>%{y:.1f}</b><extra></extra>",
))
for yv, col, lbl in [(75, "#ff4444", "Critical"), (40, "#ffb020", "Warning")]:
    trend_fig.add_hline(y=yv, line=dict(color=col, width=1, dash="dot"),
                        annotation_text=lbl, annotation_position="right",
                        annotation_font=dict(size=9, color=col))
trend_fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(size=10))
trend_fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)",
                       zeroline=False, range=[0, 105], tickfont=dict(size=10))
trend_fig.update_layout(**{**PLOTLY_BASE, "height": 210})
st.plotly_chart(trend_fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════
# ROUTE MAP — accurate sea lanes, recommended route only
# ═══════════════════════════════════════════════════════════
st.markdown('<div style="height:20px"></div><div class="fade-s7"><div class="section-label">Recommended Route</div></div>',
            unsafe_allow_html=True)

# Key port / chokepoint markers
locations = {
    "Turkey (Izmir)":     dict(lat=38.4,  lon=27.1,  color="#00e5a0"),
    "Turkey (Mersin)":    dict(lat=36.8,  lon=34.6,  color="#00e5a0"),
    "Suez Canal":         dict(lat=31.3,  lon=32.3,  color="#ffb020"),
    "Red Sea":            dict(lat=20.0,  lon=38.0,  color="#ffb020"),
    "Oman (Salalah)":     dict(lat=17.0,  lon=54.1,  color="#e8ff47"),
    "Strait of Hormuz":   dict(lat=26.5,  lon=56.5,  color="#e8ff47"),
    "Arabian Gulf":       dict(lat=25.2,  lon=55.3,  color="#e8ff47"),
    "Morocco":            dict(lat=33.6,  lon=-7.6,  color="#00e5a0"),
    "Gibraltar":          dict(lat=36.14, lon=-5.35, color="#3b6bff"),
    "Europe":             dict(lat=51.9,  lon=4.5,   color="#e8ff47"),
    "Senegal (Dakar)":    dict(lat=14.7,  lon=-17.4, color="#a78bfa"),
    "Nigeria (Lagos)":    dict(lat=6.5,   lon=3.4,   color="#a78bfa"),
    "Japan":              dict(lat=34.7,  lon=135.5, color="#e8ff47"),
}

# ── Route A — Mediterranean Sea (Turkey Izmir → Med → Gibraltar → Atlantic coast → Rotterdam) ──
_MED_SEA_LONS = [27.1, 22.0, 16.0, 12.0, 8.0, 4.5, 0.5, -2.0, -5.35, -8.0, -9.5, -9.0, -5.0, -2.0, 1.5, 4.5]
_MED_SEA_LATS = [38.4, 36.5, 37.5, 40.5, 41.0, 43.5, 40.5, 37.0, 35.9, 37.0, 39.5, 42.5, 47.5, 49.5, 51.0, 51.9]

# ── Route E — Global (Hormuz): Japan → South China Sea → Malacca → Indian Ocean → Arabian Sea → around Oman → Strait of Hormuz → Arabian Gulf ──
_HORMUZ_GLOBAL_LONS = [135.5, 121.0, 110.0, 103.8, 80.0, 65.0, 57.5, 59.0, 58.0, 56.5, 55.3]
_HORMUZ_GLOBAL_LATS = [ 34.7,  30.0,  20.0,   1.3,  5.0, 12.0, 18.0, 21.5, 23.5, 26.5, 25.2]

# ── Route C — Suez Canal & Red Sea (Japan → Indian Ocean → Suez Canal → Turkey Mersin → Red Sea → Gulf of Aden → Oman) ──
_SUEZ_RED_SEA_LONS = [135.5, 121.0, 110.0, 103.8, 80.0, 65.0, 50.0, 43.5, 38.0, 32.3, 33.5, 34.6, 33.5, 32.3, 33.0, 36.5, 38.5, 42.0, 43.5, 50.0, 54.1]
_SUEZ_RED_SEA_LATS = [34.7,  30.0,  20.0,   1.3,  5.0, 12.0, 12.0, 12.5, 20.0, 31.3, 34.0, 36.8, 34.0, 31.3, 27.5, 23.5, 18.0, 14.5, 12.5, 15.0, 17.0]

# ── Route B — Strait of Gibraltar (Morocco → Gibraltar → Atlantic coast → Rotterdam) ──
_GIBRALTAR_LONS = [-7.6, -6.0, -5.35, -6.5, -8.5, -9.5, -9.0, -5.0, -2.0, 1.5, 4.5]
_GIBRALTAR_LATS = [33.6, 35.2, 36.14, 36.0, 37.0, 39.5, 42.5, 47.5, 49.5, 51.0, 51.9]

# ── Route D — West Africa Regional (Japan → Indian Ocean → Cape of Good Hope → Morocco → Atlantic coast → Senegal → Nigeria) ──
_WEST_AFRICA_LONS = [135.5, 110.0, 90.0, 75.0, 55.0, 18.4,  0.0, -10.0, -7.6, -13.0, -17.4, -16.5, -14.5, -13.0, -10.5, -6.0, -4.0, -0.2, 3.4]
_WEST_AFRICA_LATS = [ 34.7,  10.0,  5.0, -15.0, -30.0, -34.4, -20.0,  10.0, 33.6,  20.0,  14.7,  12.0,  10.5,   8.5,   6.3,  4.8,  5.3,  5.5, 6.5]

map_fig = go.Figure()


def add_route(lons, lats, color, name, dash="solid", width=2.5):
    map_fig.add_trace(go.Scattergeo(
        lon=lons, lat=lats, mode="lines",
        line=dict(width=width, color=color, dash=dash),
        name=name, showlegend=True,
        hovertemplate=f"<b>{name}</b><extra></extra>",
    ))


# Draw only the recommended route(s) for current risk status
if not g40:
    # STABLE — Route A Mediterranean Sea: Turkey (Izmir) → Med → Europe
    #          Route E Global (Hormuz): Turkey (Mersin) → Suez → Red Sea → Hormuz → Arabian Gulf
    add_route(_MED_SEA_LONS, _MED_SEA_LATS,
              "rgba(59,107,255,0.95)", "✦ Route A — Mediterranean Sea", width=3)
    add_route(_HORMUZ_GLOBAL_LONS, _HORMUZ_GLOBAL_LATS,
              "rgba(232,255,71,0.9)", "✦ Route E — Global (Hormuz)", width=3)
    shown_locations = ["Turkey (Izmir)", "Japan", "Gibraltar", "Europe",
                       "Strait of Hormuz", "Arabian Gulf"]

elif not g75:
    # WARNING — Route B Strait of Gibraltar primary; Mediterranean Sea contingency
    add_route(_GIBRALTAR_LONS, _GIBRALTAR_LATS,
              "rgba(0,229,160,0.95)", "✦ Route B — Strait of Gibraltar", width=3)
    add_route(_MED_SEA_LONS, _MED_SEA_LATS,
              "rgba(59,107,255,0.65)", "Alt — Route A Mediterranean Sea", dash="dash", width=2)
    shown_locations = ["Morocco", "Gibraltar", "Europe", "Turkey (Izmir)"]

else:
    # CRITICAL — Route C Suez Canal & Red Sea + Route D West Africa Regional
    add_route(_SUEZ_RED_SEA_LONS, _SUEZ_RED_SEA_LATS,
              "rgba(0,229,160,0.95)", "✦ Route C — Suez Canal & Red Sea", width=3)
    add_route(_WEST_AFRICA_LONS, _WEST_AFRICA_LATS,
              "rgba(139,92,246,0.9)", "✦ Route D — West Africa Regional", width=3)
    shown_locations = ["Japan", "Suez Canal", "Red Sea", "Oman (Salalah)",
                       "Morocco", "Senegal (Dakar)", "Nigeria (Lagos)"]

# Draw only the markers relevant to the active route(s)
for name, c in locations.items():
    if name not in shown_locations:
        continue
    map_fig.add_trace(go.Scattergeo(
        lon=[c["lon"]], lat=[c["lat"]], mode="markers+text", text=[name],
        textposition="top center",
        textfont=dict(size=10, color="rgba(240,244,255,0.6)"),
        marker=dict(size=9, color=c["color"], opacity=0.95,
                    line=dict(width=1.5, color="rgba(255,255,255,0.15)")),
        showlegend=False,
        hovertemplate=f"<b>{name}</b><extra></extra>",
    ))

# Expand lat/lon range to show West Africa + Cape of Good Hope route if needed, Japan always
_lat_min = -40 if g75 else -5
_lon_max = 145 if (not g40 or g75) else 70
map_fig.update_layout(**{
    **PLOTLY_BASE, "height": 450,
    "margin": dict(l=0, r=0, t=0, b=0), "showlegend": True,
    "legend": dict(orientation="h", y=-0.05, x=0.5, xanchor="center",
                   bgcolor="rgba(0,0,0,0)", font=dict(size=11, color="#64748b"),
                   entrywidth=260, entrywidthmode="pixels"),
    "geo": dict(
        projection_type="natural earth",
        showland=True,  landcolor="rgb(14,20,36)",
        coastlinecolor="rgb(35,48,75)", coastlinewidth=0.7,
        countrycolor="rgb(25,35,58)",   countrywidth=0.4,
        showocean=True, oceancolor="rgb(7,10,18)",
        showcountries=True, bgcolor="rgba(0,0,0,0)",
        lataxis=dict(range=[_lat_min, 60]),
        lonaxis=dict(range=[-25, _lon_max]),
    ),
})
st.plotly_chart(map_fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════
# ROUTE TABLE
# ═══════════════════════════════════════════════════════════
st.markdown('<div style="height:20px"></div><div class="fade-s8"><div class="section-label">Route Comparison</div></div>',
            unsafe_allow_html=True)
metrics_df = pd.DataFrame({
    "Route": [
        "Route A — Mediterranean Sea",
        "Route B — Strait of Gibraltar",
        "Route C — Suez Canal & Red Sea",
        "Route D — West Africa Regional",
        "Route E — Global (Hormuz)",
    ],
    "Path": [
        "Turkey (Izmir) → Mediterranean Sea → Italy · Greece · Spain · France · Portugal",
        "Morocco → Strait of Gibraltar → Algeciras · Spain → All Europe",
        "Japan → Indian Ocean → Suez Canal → Turkey (Mersin) → Red Sea → Gulf of Aden → Oman",
        "Japan → Indian Ocean → Cape of Good Hope → Morocco → Atlantic Coast → Senegal · Nigeria · Ghana · Ivory Coast",
        "Japan → Malacca Strait → Indian Ocean → Arabian Sea → Strait of Hormuz → Arabian Gulf",
    ],
    "Lead Time": ["3–5 d", "1–2 d", "8–10 d", "5–8 d", "18–22 d"],
    "Distance":  ["~2,500 nm", "~500 nm", "~3,200 nm", "~3,800 nm", "~4,800 nm"],
    "Status": [
        "🟢 Recommended" if not g40 else ("🟡 Contingency" if not g75 else "⚪ Standby"),
        "⚪ Standby"      if not g40 else ("🟢 Recommended" if not g75 else "⚪ Standby"),
        "⚪ Standby"      if not g75 else "🟢 Recommended",
        "⚪ Standby"      if not g75 else "🟢 Recommended",
        "🟢 Recommended" if not g40 else "🔴 Suspended",   # open only when STABLE
    ],
})
st.dataframe(
    metrics_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Route":     st.column_config.TextColumn("Route",           width="medium"),
        "Path":      st.column_config.TextColumn("Sea Lane / Path", width="large"),
        "Lead Time": st.column_config.TextColumn("Lead Time",       width="small"),
        "Distance":  st.column_config.TextColumn("Distance",        width="small"),
        "Status":    st.column_config.TextColumn("Status",          width="small"),
    },
)

# ═══════════════════════════════════════════════════════════
# SCENARIO LAB
# ═══════════════════════════════════════════════════════════
st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)
st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
  <div class="section-label" style="margin:0;">Scenario Lab</div>
  <span style="font-family:'DM Mono',monospace;font-size:.6rem;letter-spacing:.1em;
        color:rgba(232,255,71,0.5);background:rgba(232,255,71,0.06);
        border:1px solid rgba(232,255,71,0.15);border-radius:99px;padding:2px 10px;">
    WHAT-IF SIMULATOR
  </span>
</div>""", unsafe_allow_html=True)

with st.expander("⚗️  Configure & Run Scenario", expanded=True):
    sc1, sc2, sc3 = cols([1, 1, 1])
    with sc1:
        scenario_type = st.selectbox("Scenario", list(_SCENARIO_PARAMS.keys()),
                                     help="Preset disruption profile. Each preset bakes in a base severity, scramble cost penalty, and recovery period: Hormuz Closure (21-day recovery), Red Sea Escalation (14-day), Full ME Conflict (45-day), Custom (20-day, freely adjustable).")
    with sc2:
        duration_days = st.slider("Disruption Duration (days)", 1, 90, 14,
                                   help="How many days the disruption stays at peak intensity. After this window the model linearly recovers over the preset recovery period.")
    with sc3:
        severity_pct = st.slider("Severity Override (%)", 0, 100, 70,
                                  help="Scales the preset's base disruption intensity. 100% = full preset impact, 50% = half-strength (e.g. contested strait vs full closure).")

    df_scenario      = compute_scenario(scenario_type, duration_days, severity_pct)
    peak_cost        = df_scenario["Cost/Unit ($)"].max()
    total_extra_m    = df_scenario["Cumulative Extra Cost ($M)"].iloc[-1]
    peak_lead        = df_scenario["Lead Time (d)"].max()
    zero_global_days = int((df_scenario["Global (%)"] < 1).sum())

    sm1, sm2, sm3, sm4 = cols([1, 1, 1, 1], gap="small")
    with sm1:
        st.metric("Peak Cost / Unit", f"${peak_cost:,.0f}",
                  delta=f"+${peak_cost-BASE_COST_GLOBAL:,.0f} vs baseline",
                  help=f"Highest per-unit shipping cost reached during the scenario. Baseline is ${BASE_COST_GLOBAL:,} (standard ocean freight). Delta shows the premium over normal cost.")
    with sm2:
        st.metric("Peak Lead Time", f"{peak_lead:.0f} d",
                  delta=f"+{peak_lead-BASE_LEAD_GLOBAL:.0f} d vs baseline",
                  help=f"Longest delivery lead time hit during the scenario. Baseline is {BASE_LEAD_GLOBAL} days (ocean freight). Rises as volume shifts to slower overland alternatives, plus a 3-day shock spike.")
    with sm3:
        st.metric("Cumulative Extra Cost", f"${total_extra_m:.1f}M",
                  delta="5,000 units/day assumed",
                  help="Total additional spend above the baseline cost across the full scenario window (disruption + recovery). Assumes 5,000 units shipped per day. This is the all-in financial impact of the disruption.")
    with sm4:
        st.metric("Days Global = 0%", f"{zero_global_days} d",
                  help="Number of days during the scenario where the Hormuz route is completely unusable (allocation drops below 1%). During these days you are 100% dependent on overland Turkey / Morocco routes.")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Dual-axis chart: cost + lead time
    sc_fig = go.Figure()
    sc_fig.add_trace(go.Scatter(
        x=df_scenario["Date"], y=df_scenario["Cost/Unit ($)"],
        name="Cost / Unit ($)", mode="lines",
        line=dict(color="#e8ff47", width=2),
        fill="tozeroy", fillcolor="rgba(232,255,71,0.05)",
        hovertemplate="%{x|%b %d}: <b>$%{y:,.0f}</b><extra></extra>",
        yaxis="y1",
    ))
    sc_fig.add_trace(go.Scatter(
        x=df_scenario["Date"], y=df_scenario["Lead Time (d)"],
        name="Lead Time (d)", mode="lines",
        line=dict(color="#00e5a0", width=2, dash="dot"),
        hovertemplate="%{x|%b %d}: <b>%{y:.1f} d</b><extra></extra>",
        yaxis="y2",
    ))
    end_date = datetime.today() + timedelta(days=duration_days)
    sc_fig.add_vrect(
        x0=datetime.today(), x1=end_date,
        fillcolor="rgba(255,68,68,0.07)", line_width=0,
        annotation_text="Disruption", annotation_position="top left",
        annotation_font=dict(size=9, color="rgba(255,68,68,0.53)"),   # ← fix 1: was #ff444488
    )
    sc_fig.add_hline(
        y=BASE_COST_GLOBAL,
        line=dict(color="rgba(255,255,255,0.15)", width=1, dash="dot"),
        annotation_text="Baseline cost", annotation_position="right",
        annotation_font=dict(size=9, color="rgba(255,255,255,0.3)"),
        yref="y1",
    )
    sc_fig.update_layout(**{
        **PLOTLY_BASE, "height": 300, "showlegend": True,
        "legend": dict(orientation="h", y=1.08, x=0,
                       font=dict(size=11, color="#94a3b8"), bgcolor="rgba(0,0,0,0)"),
        # ↓ fix 2: use title=dict(text=..., font=dict(...)) instead of deprecated titlefont
        "yaxis": dict(
            title=dict(text="Cost / Unit ($)", font=dict(color="#e8ff47")),
            showgrid=True, gridcolor="rgba(255,255,255,0.04)",
            tickfont=dict(size=10), zeroline=False,
        ),
        "yaxis2": dict(
            title=dict(text="Lead Time (d)", font=dict(color="#00e5a0")),
            overlaying="y", side="right",
            showgrid=False,
            tickfont=dict(size=10, color="#00e5a0"),   # ← fix 3: removed invalid tickfont2
            zeroline=False,
        ),
        "hovermode": "x unified",
    })
    st.plotly_chart(sc_fig, use_container_width=True)

    # Allocation shift chart
    alloc_fig = go.Figure()
    alloc_fig.add_trace(go.Scatter(
        x=df_scenario["Date"], y=df_scenario["Global (%)"],
        name="Global (%)", mode="lines",
        line=dict(color="#3b6bff", width=2),
        fill="tozeroy", fillcolor="rgba(59,107,255,0.07)",
        hovertemplate="%{x|%b %d}: <b>%{y:.0f}%</b><extra></extra>",
    ))
    alloc_fig.add_trace(go.Scatter(
        x=df_scenario["Date"], y=df_scenario["Regional (%)"],
        name="Regional (%)", mode="lines",
        line=dict(color="#00e5a0", width=2, dash="dot"),
        hovertemplate="%{x|%b %d}: <b>%{y:.0f}%</b><extra></extra>",
    ))
    alloc_fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(size=10))
    alloc_fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.04)",
                           zeroline=False, range=[0, 105], tickfont=dict(size=10))
    alloc_fig.update_layout(**{
        **PLOTLY_BASE, "height": 220, "showlegend": True,
        "title": dict(text="Allocation Shift Over Scenario", font=dict(size=13, color="#64748b"), x=0),
        "legend": dict(orientation="h", y=1.12, x=0,
                       font=dict(size=11, color="#94a3b8"), bgcolor="rgba(0,0,0,0)"),
    })
    st.plotly_chart(alloc_fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
     border-top:1px solid rgba(255,255,255,0.05);padding-top:16px;margin-top:32px;
     animation:fadeIn .8s .55s ease both;flex-wrap:wrap;gap:10px;">
  <span style="font-family:'DM Mono',monospace;font-size:.57rem;
        color:rgba(240,244,255,0.14);letter-spacing:.1em;">
    YAMAHA MOTOR CO. &nbsp;·&nbsp; REGIONAL SCM CONTROL TOWER &nbsp;·&nbsp; v3.0
  </span>
  <div style="display:flex;align-items:center;gap:14px;">
    <span style="font-family:'DM Mono',monospace;font-size:.57rem;color:rgba(240,244,255,0.14);">
      {"3 FEEDS ACTIVE" if live_feeds else "DEMO MODE"}
      &nbsp;·&nbsp; NEWS: {"ON" if news_enabled else "OFF"}
      &nbsp;·&nbsp; AI: {"ON" if claude_enabled else "OFF"}
    </span>
    <span style="display:inline-flex;align-items:center;gap:5px;">
      <span style="width:5px;height:5px;border-radius:50%;background:#00e5a0;display:inline-block;
            animation:blink 1.8s ease-in-out infinite;box-shadow:0 0 5px rgba(0,229,160,0.8);"></span>
      <span style="font-family:'DM Mono',monospace;font-size:.57rem;
            color:rgba(0,229,160,0.55);letter-spacing:.1em;">{now_str} SGT</span>
    </span>
  </div>
</div>
""", unsafe_allow_html=True)
