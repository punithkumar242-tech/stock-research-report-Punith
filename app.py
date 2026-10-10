
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import io

st.set_page_config(page_title="Stock Research Report", page_icon="📊", layout="wide")

st.title("📊 2-Page Stock Research Report")
st.caption("Free prototype • India-focused • Data from Yahoo Finance via yfinance")

ticker_input = st.text_input(
    "Enter NSE ticker / stock symbol",
    value="RELIANCE",
    placeholder="Example: RELIANCE, TCS, INFY, HDFCBANK"
).strip().upper()

def fmt_num(x, digits=2):
    if x is None or pd.isna(x):
        return "N/A"
    x = float(x)
    if abs(x) >= 1e9: return f"₹{x/1e9:.{digits}f} B"
    if abs(x) >= 1e7: return f"₹{x/1e7:.{digits}f} Cr"
    if abs(x) >= 1e5: return f"₹{x/1e5:.{digits}f} L"
    return f"₹{x:,.{digits}f}"

def pct(x, digits=1):
    if x is None or pd.isna(x): return "N/A"
    return f"{float(x)*100:.{digits}f}%"

def latest_value(df, row):
    if df is None or row not in df.index:
        return np.nan
    s = df.loc[row].dropna()
    return s.iloc[0] if len(s) else np.nan

def cagr(start, end, years):
    if start is None or end is None or years <= 0 or start <= 0 or end <= 0:
        return np.nan
    return (end/start)**(1/years)-1

def clean_statement(df):
    if df is None or df.empty:
        return pd.DataFrame()
    x = df.copy()
    x = x.loc[:, ~x.columns.duplicated()]
    return x

@st.cache_data(ttl=1800)
def load_data(symbol):
    # NSE convention. If user enters an explicit Yahoo symbol, retain it.
    sym = symbol if "." in symbol else symbol + ".NS"
    tk = yf.Ticker(sym)

    info = {}
    try: info = tk.info or {}
    except Exception: pass

    try: hist = tk.history(period="5y", auto_adjust=False)
    except Exception: hist = pd.DataFrame()

    try: income = clean_statement(tk.financials)
    except Exception: income = pd.DataFrame()

    try: balance = clean_statement(tk.balance_sheet)
    except Exception: balance = pd.DataFrame()

    try: cashflow = clean_statement(tk.cashflow)
    except Exception: cashflow = pd.DataFrame()

    try: holders = tk.institutional_holders
    except Exception: holders = pd.DataFrame()

    try: major = tk.major_holders
    except Exception: major = pd.DataFrame()

    try: officers = tk.get_insider_roster_holders()
    except Exception: officers = pd.DataFrame()

    return sym, info, hist, income, balance, cashflow, holders, major, officers

if st.button("Generate Report", type="primary"):
    with st.spinner("Collecting market and financial data..."):
        try:
            sym, info, hist, income, balance, cashflow, holders, major, officers = load_data(ticker_input)
        except Exception as e:
            st.error(f"Could not load data: {e}")
            st.stop()

    if hist.empty:
        st.error("No market data found. Try an NSE ticker such as RELIANCE, TCS, INFY or HDFCBANK.")
        st.stop()

    name = info.get("longName") or info.get("shortName") or ticker_input
    sector = info.get("sector", "N/A")
    industry = info.get("industry", "N/A")
    price = float(hist["Close"].dropna().iloc[-1])
    market_cap = info.get("marketCap", np.nan)

    # ---------- Core financial metrics ----------
    revenue = latest_value(income, "Total Revenue")
    op_income = latest_value(income, "Operating Income")
    net_income = latest_value(income, "Net Income")
    gross_profit = latest_value(income, "Gross Profit")

    equity = latest_value(balance, "Stockholders Equity")
    assets = latest_value(balance, "Total Assets")
    debt = latest_value(balance, "Total Debt")
    cash = latest_value(balance, "Cash Cash Equivalents And Short Term Investments")
    current_assets = latest_value(balance, "Current Assets")
    current_liab = latest_value(balance, "Current Liabilities")
    interest_expense = latest_value(income, "Interest Expense")
    cfo = latest_value(cashflow, "Operating Cash Flow")
    capex = latest_value(cashflow, "Capital Expenditure")

    shares = info.get("sharesOutstanding", np.nan)
    eps = info.get("trailingEps", np.nan)
    pe = info.get("trailingPE", np.nan)
    pb = info.get("priceToBook", np.nan)
    roe = info.get("returnOnEquity", np.nan)
    roa = info.get("returnOnAssets", np.nan)
    profit_margin = info.get("profitMargins", np.nan)
    op_margin = info.get("operatingMargins", np.nan)
    debt_to_equity = info.get("debtToEquity", np.nan)
    current_ratio = info.get("currentRatio", np.nan)
    dividend_yield = info.get("dividendYield", np.nan)
    beta = info.get("beta", np.nan)
    book_value = info.get("bookValue", np.nan)

    # Historical return
    hist2 = hist["Close"].dropna()
    returns = {}
    for days, label in [(252,"1Y"), (756,"3Y"), (1260,"5Y")]:
        if len(hist2) > days:
            returns[label] = hist2.iloc[-1] / hist2.iloc[-days-1] - 1
        else:
            returns[label] = np.nan

    # Revenue CAGR from annual statements (approximate)
    rev_growth = np.nan
    if "Total Revenue" in income.index:
        vals = income.loc["Total Revenue"].dropna()
        if len(vals) >= 3:
            vals = vals.sort_index()
            years = len(vals)-1
            rev_growth = cagr(float(vals.iloc[0]), float(vals.iloc[-1]), years)

    # Profit CAGR
    profit_growth = np.nan
    if "Net Income" in income.index:
        vals = income.loc["Net Income"].dropna()
        if len(vals) >= 3:
            vals = vals.sort_index()
            profit_growth = cagr(float(vals.iloc[0]), float(vals.iloc[-1]), len(vals)-1)

    # Forward scenario estimate based on historical growth, capped for realism.
    base_growth = np.nanmean([rev_growth, profit_growth])
    if pd.isna(base_growth):
        base_growth = 0.10
    base_growth = float(np.clip(base_growth, -0.20, 0.25))
    bull = min(base_growth + 0.05, 0.30)
    bear = max(base_growth - 0.07, -0.25)

    future_revenue_base = revenue * (1 + base_growth) if not pd.isna(revenue) else np.nan
    future_profit_base = net_income * (1 + base_growth) if not pd.isna(net_income) else np.nan

    # Score
    score = 5.0
    if not pd.isna(roe) and roe > .15: score += 0.8
    if not pd.isna(roa) and roa > .07: score += 0.4
    if not pd.isna(debt_to_equity) and debt_to_equity < 100: score += 0.5
    if not pd.isna(current_ratio) and current_ratio > 1: score += 0.3
    if not pd.isna(profit_margin) and profit_margin > .10: score += 0.5
    if not pd.isna(rev_growth) and rev_growth > .10: score += 0.6
    if not pd.isna(pe) and pe < 25: score += 0.4
    if not pd.isna(pe) and pe > 50: score -= 0.8
    score = float(np.clip(score, 0, 10))

    if score >= 7.5: view = "Positive"
    elif score >= 6: view = "Neutral / Selective"
    else: view = "Cautious"

    valuation = "N/A"
    if not pd.isna(pe):
        if pe < 18: valuation = "Potentially Attractive"
        elif pe < 30: valuation = "Fair / Growth-dependent"
        else: valuation = "Premium Valuation"

    # ---------- Industry/global framework ----------
    industry_risk = {
        "Financial Services": "Credit cycle, interest rates, regulation and asset quality.",
        "Technology": "Global IT spending, USD/INR, AI disruption, wage costs and US/Europe demand.",
        "Energy": "Crude/gas prices, energy transition, geopolitics and refining/petrochemical cycles.",
        "Consumer Cyclical": "Disposable income, inflation, rates and consumer demand.",
        "Healthcare": "USFDA/regulatory changes, pricing, R&D and global healthcare demand.",
        "Industrials": "Capex cycle, government spending, commodity costs and order inflows.",
        "Basic Materials": "Commodity prices, China demand, capacity additions and trade policy.",
        "Communication Services": "Advertising cycle, subscriber growth, regulation and technology shifts.",
        "Consumer Defensive": "Rural/urban consumption, inflation, input costs and distribution.",
        "Real Estate": "Interest rates, property demand, liquidity and regulation.",
    }
    industry_note = industry_risk.get(sector, "Demand cycle, competition, input costs, regulation and macroeconomic conditions.")

    # ---------- Report UI ----------
    st.success(f"{name} — report generated")
    st.caption(f"Ticker: {sym} • Sector: {sector} • Industry: {industry} • Generated: {datetime.now():%d-%b-%Y %H:%M}")

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Price", f"₹{price:,.2f}")
    c2.metric("Market Cap", fmt_num(market_cap))
    c3.metric("P/E", "N/A" if pd.isna(pe) else f"{pe:.1f}x")
    c4.metric("ROE", pct(roe))
    c5.metric("Overall Score", f"{score:.1f}/10")

    st.divider()

    # PAGE 1
    st.header("PAGE 1 — Company & Financial Analysis")

    left, right = st.columns(2)
    with left:
        st.subheader("Historical Performance")
        perf = pd.DataFrame({
            "Period": ["1 Year", "3 Years", "5 Years"],
            "Return": [pct(returns["1Y"]), pct(returns["3Y"]), pct(returns["5Y"])]
        })
        st.dataframe(perf, hide_index=True, use_container_width=True)
        if not hist2.empty:
            st.line_chart(hist2.tail(756), height=220)

    with right:
        st.subheader("Key Ratios")
        ratios = {
            "EPS": eps, "P/E": pe, "P/B": pb, "ROE": roe, "ROA": roa,
            "Net Margin": profit_margin, "Operating Margin": op_margin,
            "Debt/Equity": debt_to_equity, "Current Ratio": current_ratio,
            "Dividend Yield": dividend_yield, "Beta": beta
        }
        ratio_df = pd.DataFrame([
            [k, ("N/A" if pd.isna(v) else (f"{v*100:.1f}%" if k in ["ROE","ROA","Net Margin","Operating Margin","Dividend Yield"] else f"{v:.2f}"))]
            for k,v in ratios.items()
        ], columns=["Ratio","Value"])
        st.dataframe(ratio_df, hide_index=True, use_container_width=True, height=300)

    st.subheader("P&L — Key Advantages & Disadvantages")
    adv, disadv = st.columns(2)
    with adv:
        st.markdown("**Advantages**")
        if not pd.isna(rev_growth) and rev_growth > .08: st.write("• Revenue has shown healthy multi-year growth.")
        if not pd.isna(profit_growth) and profit_growth > .08: st.write("• Profit growth supports operating scalability.")
        if not pd.isna(op_margin) and op_margin > .12: st.write("• Operating margin indicates reasonable earnings quality.")
        if all(pd.isna(x) or x is False for x in []): pass
        st.write("• Review segment mix and recurring vs. one-time income before investing.")
    with disadv:
        st.markdown("**Risks / Disadvantages**")
        if not pd.isna(profit_growth) and profit_growth < 0: st.write("• Profit growth has been weak/negative.")
        if not pd.isna(op_margin) and op_margin < .08: st.write("• Operating margin is relatively low.")
        if not pd.isna(debt_to_equity) and debt_to_equity > 150: st.write("• Leverage deserves close monitoring.")
        st.write("• Historical financials do not guarantee future performance.")

    st.subheader("Balance Sheet — Key Advantages & Disadvantages")
    b1,b2,b3,b4 = st.columns(4)
    b1.metric("Total Assets", fmt_num(assets))
    b2.metric("Equity", fmt_num(equity))
    b3.metric("Debt", fmt_num(debt))
    b4.metric("Cash", fmt_num(cash))
    st.write(f"**Balance-sheet view:** {'Healthy liquidity profile' if not pd.isna(current_ratio) and current_ratio >= 1 else 'Liquidity requires monitoring'}; "
             f"{'leverage appears moderate' if not pd.isna(debt_to_equity) and debt_to_equity < 100 else 'leverage requires monitoring'}.")

    st.subheader("Cash Flow")
    st.write(f"Operating Cash Flow: **{fmt_num(cfo)}**  |  Capital Expenditure: **{fmt_num(capex)}**")

    st.divider()

    # PAGE 2
    st.header("PAGE 2 — Future, Industry & Ownership Outlook")

    st.subheader("Future Income Estimation — Scenario Model")
    st.caption("This is a calculated scenario, not a guaranteed forecast or analyst consensus.")
    forecast = pd.DataFrame({
        "Scenario": ["Bear", "Base", "Bull"],
        "Assumed Growth": [f"{bear*100:.1f}%", f"{base_growth*100:.1f}%", f"{bull*100:.1f}%"],
        "Next-Year Revenue": [
            fmt_num(revenue*(1+bear)) if not pd.isna(revenue) else "N/A",
            fmt_num(future_revenue_base),
            fmt_num(revenue*(1+bull)) if not pd.isna(revenue) else "N/A"
        ],
        "Next-Year Profit": [
            fmt_num(net_income*(1+bear)) if not pd.isna(net_income) else "N/A",
            fmt_num(future_profit_base),
            fmt_num(net_income*(1+bull)) if not pd.isna(net_income) else "N/A"
        ]
    })
    st.dataframe(forecast, hide_index=True, use_container_width=True)

    st.subheader("Industry View")
    st.write(f"**Sector:** {sector}  |  **Industry:** {industry}")
    st.write(f"**Industry/global factors to monitor:** {industry_note}")
    i1,i2 = st.columns(2)
    with i1:
        st.markdown("**Industry advantages**")
        st.write("• Structural demand and long-term industry growth can support earnings.")
        st.write("• Scale, technology and market share can create competitive advantages.")
        st.write("• Global diversification can reduce dependence on a single market.")
    with i2:
        st.markdown("**Industry disadvantages**")
        st.write("• Cyclicality, competition and regulatory changes can pressure margins.")
        st.write("• Currency, rates, commodities and geopolitical events may affect profitability.")
        st.write("• Industry disruption can make historical valuations unreliable.")

    st.subheader("Global Impact — Present & Future")
    st.write("**Present:** Interest rates, inflation, USD/INR, commodity prices, global growth, geopolitical risk and trade policy can influence Indian equities.")
    st.write("**Future:** AI/automation, energy transition, supply-chain relocation, China/global demand, monetary policy and regulation may change industry economics.")

    st.subheader("Shareholding & Market Float")
    sh1, sh2, sh3, sh4 = st.columns(4)
    sh1.metric("Promoter", info.get("heldPercentInsiders", np.nan) if not pd.isna(info.get("heldPercentInsiders", np.nan)) else "N/A")
    sh2.metric("Institutions", info.get("heldPercentInstitutions", np.nan) if not pd.isna(info.get("heldPercentInstitutions", np.nan)) else "N/A")
    sh3.metric("Shares Outstanding", f"{shares/1e7:.2f} Cr" if not pd.isna(shares) else "N/A")
    sh4.metric("Market Cap", fmt_num(market_cap))
    st.caption("For production use, connect NSE/SEBI filings or a licensed market-data provider for precise quarterly Promoter/FII/DII/Mutual Fund classification. The prototype does not invent missing ownership data.")

    st.subheader("Valuation Highlight")
    st.markdown(f"### {valuation}")
    st.write(f"Current P/E: **{'N/A' if pd.isna(pe) else f'{pe:.1f}x'}** | P/B: **{'N/A' if pd.isna(pb) else f'{pb:.1f}x'}** | EPS: **{'N/A' if pd.isna(eps) else f'₹{eps:.2f}'}**")

    st.subheader("Key Management / Company Information")
    st.write(info.get("longBusinessSummary", "Company description unavailable from the data source."))
    if not officers.empty:
        st.dataframe(officers.head(8), hide_index=True, use_container_width=True)

    st.subheader("Final View")
    st.markdown(f"## {view} — {score:.1f}/10")
    st.write("This score is a screening model based on available financial and valuation metrics. It is not investment advice.")

    st.info("⚠️ Prototype limitation: free public data can be incomplete or delayed. Verify important figures against NSE/SEBI/company filings before making an investment decision.")

else:
    st.markdown("""
    ### How it works
    1. Enter an NSE ticker.
    2. Click **Generate Report**.
    3. The app pulls available market/financial data.
    4. It calculates ratios and historical performance.
    5. It produces a two-page research-style dashboard with scenario estimates.

    **Example tickers:** RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, SBIN, LT
    """)
