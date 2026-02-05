import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="Mini Investment Analyst", layout="wide")
st.title("📊 Mini Investment Analyst")

# -------------------------
# Helper function
# -------------------------
def resolve(name):
    try:
        return yf.Search(name).quotes[0]["symbol"]
    except:
        return None

# -------------------------
# Session memory
# -------------------------
if "companies" not in st.session_state:
    st.session_state.companies = []

company = st.text_input("Enter Company Name")

col1, col2 = st.columns(2)

with col1:
    if st.button("➕ Add to Compare") and company:
        ticker = resolve(company)
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

        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")

        if hist.empty:
            continue

        revenue_growth = info.get("revenueGrowth")
        roe = info.get("returnOnEquity")
        debt_equity = info.get("debtToEquity")
        beta = info.get("beta")

        revenue_growth = revenue_growth*100 if revenue_growth else np.nan
        roe = roe*100 if roe else np.nan
        debt_equity = debt_equity if debt_equity else np.nan
        beta = beta if beta else np.nan

        returns = (hist["Close"][-1]/hist["Close"][0]-1)*100
        volatility = hist["Close"].pct_change().std()*np.sqrt(252)*100
        price = hist["Close"][-1]

        score = (
            (revenue_growth if not np.isnan(revenue_growth) else -10) +
            (roe if not np.isnan(roe) else -10) +
            returns -
            volatility -
            ((debt_equity if not np.isnan(debt_equity) else 1)*5) -
            ((beta if not np.isnan(beta) else 1)*3)
        )

        rating = "BUY" if score > 25 else "HOLD" if score > 10 else "AVOID"

        results.append([
            ticker,
            round(price,2),
            revenue_growth,
            roe,
            debt_equity,
            returns,
            volatility,
            score,
            rating
        ])

    # -------------------------
    # DataFrame
    # -------------------------
    df = pd.DataFrame(results, columns=[
        "Company","Price","Revenue Growth %","ROE %",
        "Debt/Equity","1Y Return %","Volatility %","Score","Rating"
    ])

    if df.empty:
        st.error("No valid companies.")
        st.stop()

    df = df.sort_values("Score", ascending=False)

    # -------------------------
    # Ranked Table
    # -------------------------
    st.subheader("📊 Ranked Companies")
    st.dataframe(df)

    # -------------------------
    # Portfolio Allocation
    # -------------------------
    eligible = df[df["Rating"] != "AVOID"].copy()
    if not eligible.empty:
        eligible["Weight %"] = eligible["Score"] / eligible["Score"].sum() * 100
        st.subheader("💼 Portfolio Allocation")
        st.dataframe(eligible[["Company","Rating","Weight %"]])

    # -------------------------
    # Excel Export
    # -------------------------
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

    # -------------------------
    # Charts
    # -------------------------
    st.subheader("📉 Score Comparison")
    st.bar_chart(df.set_index("Company")["Score"])

    st.subheader("📈 Price Charts")
    for comp in df["Company"]:
        hist = yf.Ticker(comp).history(period="1y")
        st.write(comp)
        st.line_chart(hist["Close"])
