import streamlit as st
import pandas as pd
import numpy as np
import requests
import matplotlib.pyplot as plt
from fpdf import FPDF
import io
import plotly.graph_objects as go
from dateutil.relativedelta import relativedelta

# ------------------------- Helper Functions --------------------------

@st.cache_data
def load_amfi_funds():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    r = requests.get(url)
    lines = r.text.split("\n")
    data = []
    for line in lines:
        parts = line.split(";")
        if len(parts) >= 5:
            scheme_code = parts[0].strip()
            scheme_name = parts[3].strip()
            if scheme_code.isdigit():
                data.append((scheme_code, scheme_name))
    return pd.DataFrame(data, columns=["SchemeCode", "SchemeName"])

@st.cache_data
def load_nav_history(scheme_code):
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    data = requests.get(url).json()
    if "data" not in data:
        return None, None, None
    df = pd.DataFrame(data["data"])
    df["nav"] = df["nav"].astype(float)
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
    df = df.sort_values("date")
    category = data.get("meta", {}).get("scheme_category", None)
    return df, category

def compute_rolling_cagr(df, years=5):
    days = years * 365
    df = df.set_index("date")
    df["rolling_cagr"] = ((df["nav"] / df["nav"].shift(days)) ** (1/years) - 1) * 100
    return df["rolling_cagr"].dropna()

def compute_cagr(df):
    start = df["nav"].iloc[0]
    end = df["nav"].iloc[-1]
    days = (df["date"].iloc[-1] - df["date"].iloc[0]).days
    years = days / 365
    return ((end / start) ** (1 / years) - 1) * 100

def xirr(cashflows, dates):
    def npv(rate):
        return sum(
            cf / ((1 + rate) ** ((dt - dates[0]).days / 365))
            for cf, dt in zip(cashflows, dates)
        )
    rate = 0.10
    for _ in range(200):
        f = npv(rate)
        df = sum(
            -cf * ((dt - dates[0]).days / 365) *
            (1 + rate) ** (-((dt - dates[0]).days / 365) - 1)
            for cf, dt in zip(cashflows, dates)
        )
        if df == 0:
            return None
        new_rate = rate - f / df
        if abs(new_rate - rate) < 1e-6:
            return new_rate
        rate = new_rate
    return rate

def compute_sip_xirr(nav_df, sip_amount=5000, years=5):
    end_date = nav_df["date"].iloc[-1]
    start_date = end_date - relativedelta(years=years)
    
    # Filter NAVs for last 5 years
    nav_df = nav_df[nav_df["date"] >= start_date].copy()
    
    # Generate monthly SIP dates
    sip_dates = pd.date_range(start=start_date, end=end_date, freq='MS')
    cashflows = []
    units = 0
    
    # Calculate units bought each month
    for date in sip_dates:
        nav_on_date = nav_df[nav_df["date"] <= date]["nav"]
        if len(nav_on_date) == 0:
            continue  # skip if NAV not available yet
        nav_val = nav_on_date.iloc[-1]
        units_bought = sip_amount / nav_val
        units += units_bought
        cashflows.append(-sip_amount)
    
    # Final redemption value
    final_nav = nav_df["nav"].iloc[-1]
    cashflows.append(units * final_nav)
    sip_dates = list(sip_dates[:len(cashflows)-1]) + [end_date]
    
    rate = xirr(cashflows, sip_dates)
    if rate is not None:
        return rate * 100
    return np.nan

def create_pdf(results_df, charts, combined_chart_buf, pdf_xirr_buf):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("helvetica", size=14)
    pdf.cell(200, 10, "Mutual Fund Comparison Report", ln=True, align="C")
    pdf.set_font("helvetica", size=11)
    pdf.ln(5)
    for _, row in results_df.iterrows():
        pdf.multi_cell(
            0, 6,
            f"Fund: {row['Fund']}\n"
            f"NAV: {row['NAV']:.2f}\n"
            f"Annualized CAGR: {row['Annualized CAGR']:.2f}%\n"
            f"5Y Avg Rolling CAGR: {row['5Y Avg Rolling CAGR']:.2f}%\n"
            f"5Y SIP XIRR: {row.get('XIRR_5Y_SIP', np.nan):.2f}%\n"
        )
        pdf.ln(3)

    # Combined rolling return chart
    pdf.add_page()
    pdf.cell(200, 10, "Combined 5-Year Rolling CAGR", ln=True)
    pdf.image(combined_chart_buf, w=170)

    # XIRR chart
    pdf.add_page()
    pdf.cell(200, 10, "5-Year SIP XIRR Comparison (Rs. 5000/month)", ln=True)
    pdf.image(pdf_xirr_buf, w=170)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()

# ------------------------- Streamlit UI --------------------------

st.set_page_config(page_title="Mutual Fund Comparison Tool", layout="wide")

st.markdown("""
    <style>
        .stMultiSelect > label {
            font-size:150%; 
            font-weight:bold; 
            color:blue;
        } 
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Mutual Fund Comparison Tool")
st.write("Select multiple funds and compare metrics including Annualized CAGR, 5-year rolling CAGR, 5-year SIP XIRR, and export to PDF.")

# Load AMFI list
df_amfi = load_amfi_funds()
fund_names = df_amfi["SchemeName"].tolist()
selected_funds = st.multiselect("**Select Mutual Funds** (Max 5)", fund_names, max_selections=5)
if not selected_funds:
    st.stop()

results = []
category_groups = {}
charts_for_pdf = {}
rolling_returns_dict = {}

# ------------------- METRIC CALCULATION -------------------
for fund in selected_funds:
    scheme_code = df_amfi[df_amfi["SchemeName"] == fund]["SchemeCode"].values[0]
    nav_df, category = load_nav_history(scheme_code)
    if nav_df is None or len(nav_df) < 800:
        st.warning(f"Not enough NAV data for {fund}")
        continue

    rolling_5yr = compute_rolling_cagr(nav_df)
    rolling_returns_dict[fund] = rolling_5yr
    cagr = compute_cagr(nav_df)
    xirr_5y = compute_sip_xirr(nav_df)
    
    category_groups.setdefault(category, []).append(cagr)
    results.append({
        "Fund": fund,
        "NAV": nav_df["nav"].iloc[-1],
        "Annualized CAGR": cagr,
        "5Y Avg Rolling CAGR": rolling_5yr.mean(),
        "XIRR_5Y_SIP": xirr_5y
    })

# ------------------- Comparison Table --------------------
st.header("📋 Comparison Summary Table")
df_results = pd.DataFrame(results)
st.dataframe(df_results, width='stretch')

# ------------------- Combined 5-Year Rolling CAGR Chart -------------------
st.header("📉 5-Year Rolling CAGR (Interactive Combined Chart)")
fig_plotly = go.Figure()
for fund, rolling_5yr in rolling_returns_dict.items():
    fig_plotly.add_trace(go.Scatter(
        x=rolling_5yr.index,
        y=rolling_5yr.values,
        mode='lines',
        name=fund,
        hovertemplate='Date: %{x|%d-%b-%Y}<br>Rolling CAGR: %{y:.2f}%<extra></extra>'
    ))
fig_plotly.update_layout(
    title="5-Year Rolling CAGR Comparison",
    xaxis_title="Date",
    yaxis_title="Rolling CAGR (%)",
    hovermode="x unified",
    template="plotly_white",
    height=500
)
st.plotly_chart(fig_plotly, use_container_width=True)

# Save combined chart for PDF
fig, ax = plt.subplots(figsize=(10, 5))
for fund, rolling_5yr in rolling_returns_dict.items():
    ax.plot(rolling_5yr.index, rolling_5yr.values, label=fund)
ax.set_title("5-Year Rolling CAGR Comparison")
ax.set_ylabel("Rolling CAGR (%)")
ax.grid(True)
ax.legend()
combined_chart_buf = io.BytesIO()
plt.savefig(combined_chart_buf, format="png")
combined_chart_buf.seek(0)
plt.close(fig)

# ------------------- XIRR Comparison Chart -------------------
st.header("💰 5-Year SIP XIRR Comparison (₹ 5000 per month)")
funds = [r["Fund"] for r in results]
xirr_values = [r["XIRR_5Y_SIP"] for r in results]
fig_xirr = go.Figure([go.Bar(x=funds, y=xirr_values, text=[f"{v:.2f}%" for v in xirr_values],
                             textposition='auto', marker_color='orange')])
fig_xirr.update_layout(
    title="5-Year SIP XIRR Comparison",
    yaxis_title="XIRR (%)",
    template="plotly_white",
    height=400
)
st.plotly_chart(fig_xirr, use_container_width=True)

# Save XIRR chart for PDF
fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(funds, xirr_values, color='orange')
ax.set_title("5-Year SIP XIRR Comparison")
ax.set_ylabel("XIRR (%)")
for i, v in enumerate(xirr_values):
    ax.text(i, v + 0.5, f"{v:.2f}%", ha='center', fontsize=9)
pdf_xirr_buf = io.BytesIO()
plt.savefig(pdf_xirr_buf, format="png")
pdf_xirr_buf.seek(0)
plt.close(fig)

# ----------------- Export to Excel -----------------------
#st.header("📥 Export to Excel")
#excel_buf = io.BytesIO()
#with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
#    df_results.to_excel(writer, index=False, sheet_name="Summary")
#    df_cat_avg.to_excel(writer, index=False, sheet_name="Category Avg")
#st.download_button(
#    "Download Excel File",
#    data=excel_buf.getvalue(),
#    file_name="MutualFund_Comparison.xlsx",
#    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#)

# ----------------- Export to PDF -----------------------
st.header("📄 Download PDF Report")
pdf_data = create_pdf(df_results, charts_for_pdf, combined_chart_buf, pdf_xirr_buf)
st.download_button(
    label="Download PDF Report",
    data=pdf_data,
    file_name="MF_Comparison_Report.pdf",
    mime="application/pdf"
)
