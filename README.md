
# Free Stock Research Report Prototype

## What this is
A Streamlit prototype that accepts an NSE stock symbol and generates a two-page research-style report.

## Cost
The prototype itself is free/open-source software. It uses `yfinance` to retrieve Yahoo Finance data. No paid AI API is required.

## Run locally
1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Run:

   pip install -r requirements.txt
   streamlit run app.py

4. Open the local URL shown by Streamlit.

## Example
Enter:
RELIANCE

The app converts it to:
RELIANCE.NS

## Important data limitation
The prototype uses Yahoo Finance data through the `yfinance` Python package. It is suitable for prototyping, not a production-grade licensed market-data service.

For exact quarterly Indian ownership classification (Promoter, FII/FPI, DII, Mutual Funds, Public and free float), connect the production version to official exchange/company filings or a licensed provider. NSE publishes shareholding-pattern filings publicly, while its dedicated corporate-data feed is a paid service.

## Future upgrades
- PDF export
- NSE/SEBI filing parser
- Exact FII/DII/MF ownership
- Quarterly trend charts
- DCF valuation
- Peer comparison
- Industry-specific scoring
- News/geopolitical impact engine
- Optional LLM-generated narrative
- User login and report history
- WhatsApp/email delivery
