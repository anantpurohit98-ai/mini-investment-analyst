import yfinance as yf
import pandas as pd
import numpy as np

# ---------------- INPUT ----------------

companies = pd.read_csv("companies.csv")

rows = []

print("Building investment model...")

for _, row in companies.iterrows():

    name = row["Company"]
    symbol = row["Ticker"]

    print(f"Processing {name}")

    t = yf.Ticker(symbol)

    income = t.financials.fillna(0)
    balance = t.balance_sheet.fillna(0)
    prices = t.history(period="2y")

    latest = income.columns[0]
    prev = income.columns[1]

    rev_now = income.loc["Total Revenue", latest]
    rev_prev = income.loc["Total Revenue", prev]
    net_income = income.loc["Net Income", latest]

    equity = balance.loc["Stockholders Equity", latest]
    debt = balance.loc["Total Debt", latest]

    growth = ((rev_now - rev_prev) / rev_prev) * 100
    roe = (net_income / equity) * 100
    debt_equity = debt / equity

    prices["ret"] = prices["Close"].pct_change()

    one_year = ((prices["Close"].iloc[-1] / prices["Close"].iloc[-252]) - 1) * 100
    vol = prices["ret"].std() * np.sqrt(252) * 100

    rows.append([name, growth, roe, debt_equity, one_year, vol])

df = pd.DataFrame(rows, columns=[
    "Company","Growth","ROE","DebtEquity","Return","Volatility"
])

# ---------------- NORMALIZATION ----------------

for col in ["Growth","ROE","Return"]:
    df[col+"_N"] = (df[col]-df[col].min())/(df[col].max()-df[col].min())

for col in ["Volatility","DebtEquity"]:
    df[col+"_N"] = 1-(df[col]-df[col].min())/(df[col].max()-df[col].min())

df["Score"] = (
    df["Growth_N"]*0.25 +
    df["ROE_N"]*0.25 +
    df["Return_N"]*0.30 +
    df["Volatility_N"]*0.10 +
    df["DebtEquity_N"]*0.10
)

df["Rating"] = np.where(df["Score"]>0.7,"BUY",
                np.where(df["Score"]>0.5,"HOLD","AVOID"))

df = df.sort_values("Score",ascending=False)

df.to_csv("data/investment_model.csv",index=False)

# ---------------- REPORT GENERATION ----------------

reports = []

for _, r in df.iterrows():

    text = f"""
Company: {r['Company']}
Score: {round(r['Score'],2)}
Rating: {r['Rating']}

Growth: {round(r['Growth'],2)}%
ROE: {round(r['ROE'],2)}%
Return: {round(r['Return'],2)}%
Volatility: {round(r['Volatility'],2)}%
Debt/Equity: {round(r['DebtEquity'],2)}

"""

    if r["Rating"] == "BUY":
        text += "Strong fundamentals with favorable risk-adjusted returns.\n"
    elif r["Rating"] == "HOLD":
        text += "Moderate growth with acceptable risk. Maintain position.\n"
    else:
        text += "Weak risk-adjusted profile. Avoid fresh exposure.\n"

    reports.append(text)

with open("data/analyst_report.txt","w") as f:
    for rep in reports:
        f.write(rep)
        f.write("\n-------------------------\n")

print("\nFULL PIPELINE COMPLETE.")
