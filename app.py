import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from io import BytesIO

# -------------------------
# Streamlit page setup
# -------------------------
st.set_page_config(page_title="Mini Investment Analyst", layout="wide")
st.title("📊 Mini Investment Analyst")

# -------------------------
# Helper functions
# -------------------------
def resolve(name):
    """Resolve company name to ticker symbol"""
    try:
        return yf.Search(name).quotes[0]["symbol"]
    except:
        return None

@st.cache_data(ttl=86400)  # Cache data for 1 day
def get_company_data(ticker):
    """Fetch data from cache if exists, else online and save locally"""
    filepath = f"data/{ticker}.csv"
    
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
    else:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if hist.empty:
            return None  # No data
        
        info = stock.fast_info  # Fast info (price, beta)
        df = hist[["Close"]].copy()
        df["Price"] = hist["Close"]
        df["Beta"] = info.get("beta", np.nan)
        df.to_csv(filepath, index=False)
    return df

# -------------------------
# Session memory
# -------------------------
if "companies" not in st.session_state:
    st.session_state.companies = []

company_name = st.text_input("Enter Company Name")

col1, col2 = st.columns(2)

with col1:
    if st.button("➕ Add to Compare") and company_name:
        ticker = resolve(company_name)
        if ticker and ticker not in st.session_state.companies:
            st.session_state.companies.append(ticker)
            st.success(f"{ticker} added")
        else:
            st.warning("Company not found or already added.")

with col2:
    if st.button("🧹 Clear List"):
        st.session_state.companies = []

st.subheader("Companies Selected")
st.write(st.session_state.companies)

# -------------------------
# Run Analysis
# -------------------------
if st.button("🚀 Run Analysis") and st.session_state.companies:

    results = []

    for ticker in st.session_state.companies:
        df_stock = get_company_data(ticker)
        if df_stock is None or df_stock.empty:
            st.warning(f"No data for {ticker}")
            continue

        # Basic metrics
        price = df_stock["Price"].iloc[-1]
        returns = (df_stock["Price"].iloc[-1] / df_stock["Price"].iloc[0] - 1) * 100
        volatility = df_stock["Price"].pct_change().std() * np.sqrt(252) * 100
        beta = df_stock["Beta"].iloc[0] if "Beta" in df_stock.columns else np.nan

        # Placeholder for fundamentals (can integrate free API here later)
        revenue_growth = np.nan
        roe = np.nan
        debt_equity = np.nan

        score = (
            (revenue_growth if not np.isnan(revenue_growth) else -10) +
            (roe if not np.isnan(roe) else -10) +
            returns -
            volatility -
            ((debt_equity if not np.isnan(debt_equity) else 1) * 5) -
            ((beta if not np.isnan(beta) else 1) * 3)
        )

        rating = "BUY" if score > 25 else "HOLD" if score > 10 else "AVOID"

        results.append([
            ticker, round(price,2), revenue_growth, roe,
            debt_equity, returns, volatility, score, rating
        ])

    # DataFrame
    df = pd.DataFrame(results, columns=[
        "Company","Price","Revenue Growth %","ROE %",
        "Debt/Equity","1Y Return %","Volatility %","Score","Rating"
    ])
    if df.empty:
        st.error("No valid companies to analyze.")
        st.stop()

    df = df.sort_values("Score", ascending=False)

    # Ranked table
    st.subheader("📊 Ranked Companies")
    st.dataframe(df)

    # Portfolio allocation
    eligible = df[df["Rating"] != "AVOID"].copy()
    if not eligible.empty:
        eligible["Weight %"] = eligible["Score"] / eligible["Score"].sum() * 100
        st.subheader("💼 Portfolio Allocation")
        st.dataframe(eligible[["Company","Rating","Weight %"]])

    # Excel export
    report = df.copy()
    if not eligible.empty:
        report = report.merge(
            eligible[["Company","Weight %"]],
            on="Company",
            how="left"
        )
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        report.to_excel(writer, sheet_name="Analysis", index=False)

    st.download_button(
        "⬇ Download Full Analyst Report",
        buffer.getvalue(),
        "analyst_report.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Charts
    st.subheader("📉 Score Comparison")
    st.bar_chart(df.set_index("Company")["Score"])

    st.subheader("📈 Price Charts")
    for comp in df["Company"]:
        hist = get_company_data(comp)
        if hist is not None and not hist.empty:
            st.write(comp)
            st.line_chart(hist["Price"])
