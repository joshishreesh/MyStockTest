import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import io

# --- PAGE CONFIG ---
st.set_page_config(page_title="Indian Market AI", page_icon="📈", layout="wide")

# --- CUSTOM CSS FOR UI ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .stButton>button {
        width: 100%;
        background-color: #FF4B4B;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CACHED FUNCTIONS (Speed up the app) ---

@st.cache_data
def get_nifty50_tickers():
    return [
        "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS", "AXISBANK.NS",
        "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "BHARTIARTL.NS", "BPCL.NS",
        "BRITANNIA.NS", "CIPLA.NS", "COALINDIA.NS", "DIVISLAB.NS", "DRREDDY.NS",
        "EICHERMOT.NS", "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS",
        "HEROMOTOCO.NS", "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS", "INDUSINDBK.NS",
        "INFY.NS", "ITC.NS", "JSWSTEEL.NS", "KOTAKBANK.NS", "LT.NS",
        "LTIM.NS", "M&M.NS", "MARUTI.NS", "NESTLEIND.NS", "NTPC.NS",
        "ONGC.NS", "POWERGRID.NS", "RELIANCE.NS", "SBILIFE.NS", "SBIN.NS",
        "SUNPHARMA.NS", "TATACONSUM.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "TCS.NS",
        "TECHM.NS", "TITAN.NS", "ULTRACEMCO.NS", "UPL.NS", "WIPRO.NS"
    ]

@st.cache_data
def get_all_nse_tickers():
    try:
        url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            s = response.content
            df = pd.read_csv(io.StringIO(s.decode('utf-8')))
            df = df[df[' SERIES'] == 'EQ']
            return [f"{symbol}.NS" for symbol in df['SYMBOL'].tolist()]
    except:
        return []
    return []

def analyze_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        if len(hist) < 10: return None
        
        current = hist['Close'].iloc[-1]
        sma_20 = hist['Close'].tail(20).mean()
        
        # RSI
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).mean()
        loss = (-delta.where(delta < 0, 0)).mean()
        rs = gain / loss if loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        
        # Momentum
        momentum = (current - hist['Close'].iloc[0]) / hist['Close'].iloc[0]
        
        # Score
        score = 50
        if rsi < 35: score += 15
        elif rsi > 70: score -= 15
        if current > sma_20: score += 15
        if momentum > 0: score += 10
        
        return {
            "Ticker": ticker.replace(".NS", ""),
            "Price": current,
            "Score": score,
            "RSI": rsi,
            "Trend": "Bullish" if current > sma_20 else "Bearish"
        }
    except:
        return None

# --- SIDEBAR UI ---
st.sidebar.header("⚙️ Settings")

scan_mode = st.sidebar.radio("Market Scope", ["Nifty 50 (Fast)", "Full Market (Slow)"])
budget = st.sidebar.number_input("Total Investment (₹)", min_value=1000, value=50000, step=1000)
num_stocks = st.sidebar.number_input("Number of Stocks", min_value=1, max_value=20, value=5)

run_btn = st.sidebar.button("🚀 Analyze Market")

# --- MAIN UI ---
st.title("🇮🇳 AI Stock Allocator")
st.markdown("Use technical indicators to find the best stocks within your budget.")

if run_btn:
    with st.spinner("Fetching market data..."):
        # 1. Get List
        if scan_mode == "Nifty 50 (Fast)":
            tickers = get_nifty50_tickers()
        else:
            tickers = get_all_nse_tickers()
            if len(tickers) > 200:
                st.warning("Scanning first 200 stocks only to save time.")
                tickers = tickers[:200]
        
        # 2. Analyze
        results = []
        progress_bar = st.progress(0)
        
        for i, ticker in enumerate(tickers):
            data = analyze_stock(ticker)
            if data: results.append(data)
            progress_bar.progress((i + 1) / len(tickers))
            
        progress_bar.empty()
        
        if not results:
            st.error("No data found.")
            st.stop()
            
        # 3. Process & Filter
        df = pd.DataFrame(results)
        df = df.sort_values(by="Score", ascending=False)
        
        target_per_stock = budget / num_stocks
        affordable_df = df[df['Price'] <= target_per_stock]
        
        if affordable_df.empty:
            st.error(f"No stocks found under ₹{target_per_stock:.2f}. Increase budget.")
        else:
            # Select top N
            portfolio = affordable_df.head(num_stocks).copy()
            portfolio['Qty'] = (target_per_stock // portfolio['Price']).astype(int)
            portfolio['Total Cost'] = portfolio['Qty'] * portfolio['Price']
            
            # Remove 0 quantity rows
            portfolio = portfolio[portfolio['Qty'] > 0]
            
            # --- RESULTS DASHBOARD ---
            total_invested = portfolio['Total Cost'].sum()
            savings = budget - total_invested
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Target Companies", len(portfolio))
            col2.metric("Total Investment", f"₹{total_invested:,.2f}")
            col3.metric("Savings", f"₹{savings:,.2f}")
            
            st.subheader("🏆 Recommended Portfolio")
            
            # Formatting for display
            display_df = portfolio[['Ticker', 'Price', 'Qty', 'Total Cost', 'Score', 'Trend', 'RSI']]
            st.dataframe(
                display_df.style.background_gradient(subset=['Score'], cmap="Greens"),
                use_container_width=True
            )
            
            st.success("Analysis Complete! Prices are delayed by 15 mins (Standard NSE Data).")

else:
    st.info("👈 Set your budget in the sidebar and click 'Analyze Market' to start.")
