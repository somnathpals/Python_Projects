import streamlit as st
import pandas as pd
import numpy as np
import requests
import matplotlib.pyplot as plt
from fpdf import FPDF
import io

# ------------------------- Helper Functions --------------------------

@st.cache_data
def load_amfi_funds():
    """Load AMFI mutual fund list for autocomplete"""
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
    """Load NAV history and meta (AUM & Category) from MFAPI"""
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    data = requests.get(url).json()
    if "data" not in data:
        return None, None, None
    df = pd.DataFrame(data["data"])
    df["nav"] = df["nav"].astype(float)
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
    df = df.sort_values("date")
    aum = data.get("meta", {}).get("aum", None)
    category = data.get("meta", {}).get("scheme_category", None)
    return df, category, aum

def compute_rolling_return(df, years=5):
    days = years * 365
    df = df.set_index("date")
    df["rolling"] = df["nav"].pct_change(days) * 100
    return df["rolling"].dropna()

def compute_cagr(df):
    start = df["nav"].iloc[0]
    end = df["nav"].iloc[-1]
    days = (df["date"].iloc[-1] - df["date"].iloc[0]).days
    years = days / 365
    return ((end / start) ** (1 / years) - 1) * 100

#def compute_std_dev(df):
#    df["daily_ret"] = df["nav"].pct_change()
#    return df["daily_ret"].std() * np.sqrt(252)

#def compute_sharpe(df, rf=0.05):
#    df["daily_ret"] = df["nav"].pct_change()
#    mean = df["daily_ret"].mean() * 252
#    std = df["daily_ret"].std() * np.sqrt(252)
#    return (mean - rf) / std if std > 0 else np.nan

def create_pdf(results_df, charts):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("helvetica", size=16)
    pdf.cell(200, 10, "Mutual Fund Comparison Report", ln=True, align="C")
    pdf.set_font("helvetica", size=11)
    pdf.ln(5)
    for _, row in results_df.iterrows():
        pdf.multi_cell(
            0, 6,
            f"Fund: {row['Fund']}\n"
            f"NAV: {row['NAV']:.2f}\n"
            f"AUM: {row['AUM']}\n"
            f"CAGR: {row['CAGR']:.2f}%\n"
            f"5Y Avg Rolling Return: {row['RollingReturn5Y']:.2f}%\n"
    #        f"StdDev: {row['StdDev']:.3f}\n"
    #       f"Sharpe: {row['Sharpe']:.2f}\n"
    #        f"Category: {row['Category']}\n"
        )
        pdf.ln(3)
    pdf.add_page()
    pdf.cell(200, 10, "Rolling Return Charts", ln=True)
    for name, img_bytes in charts.items():
        pdf.ln(5)
        pdf.cell(200, 6, name, ln=True)
        pdf.image(img_bytes, w=170)
    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()

# ------------------------- Streamlit UI --------------------------

# ==========================================================
# PAGE SETTINGS
# ==========================================================
st.set_page_config(page_title="Mutual Fund Comparison Tool", layout="wide")

st.markdown("""
    <style>
        .stMultiSelect > label {
            font-size:120%; 
            font-weight:bold; 
            color:blue;
        } 
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Mutual Fund Comparison Tool")
st.write("Select multiple funds from AMFI list and compare metrics including Fund CAGR, 5-year rolling return, AUM, Category Average CAGR, and export to Excel/PDF.")

# Load AMFI list
df_amfi = load_amfi_funds()
fund_names = df_amfi["SchemeName"].tolist()
selected_funds = st.multiselect("**Select Mutual Funds** (Max 5)", fund_names, max_selections=5)
if not selected_funds:
    st.stop()

results = []
category_groups = {}
charts_for_pdf = {}

# ------------------- METRIC CALCULATION -------------------
for fund in selected_funds:
    scheme_code = df_amfi[df_amfi["SchemeName"] == fund]["SchemeCode"].values[0]
    nav_df, category, aum = load_nav_history(scheme_code)
    if nav_df is None or len(nav_df) < 800:
        st.warning(f"Not enough NAV data for {fund}")
        continue
    rolling_5yr = compute_rolling_return(nav_df)
    cagr = compute_cagr(nav_df)
#    std_dev = compute_std_dev(nav_df)
#    sharpe = compute_sharpe(nav_df)
    category_groups.setdefault(category, []).append(cagr)
    results.append({
        "Fund": fund,
        "NAV": nav_df["nav"].iloc[-1],
        "AUM": aum,
        "CAGR": cagr,
        "RollingReturn5Y": rolling_5yr.mean(),
#        "StdDev": std_dev,
#        "Sharpe": sharpe,
#        "Category": category
    })
    # Save rolling chart for PDF
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(rolling_5yr, label=fund)
    ax.set_title(fund, fontsize=10)
    ax.set_ylabel("%")
    ax.grid(True)
    img_buf = io.BytesIO()
    plt.savefig(img_buf, format="png")
    img_buf.seek(0)
    charts_for_pdf[fund] = img_buf
    plt.close(fig)

# ------------------- Expanded Comparison Table --------------------
st.header("📋 Comparison Summary Table")
df_results = pd.DataFrame(results)
st.dataframe(df_results, width='stretch')

# ------------------- Category Averages ---------------------
st.header("📊 Category Average CAGR")
cat_avg = {cat: np.mean(vals) for cat, vals in category_groups.items()}
df_cat_avg = pd.DataFrame(list(cat_avg.items()), columns=["Category", "Avg CAGR (%)"])
st.dataframe(df_cat_avg, width='stretch')

# ------------------- Side-by-Side Rolling Return -------------------
st.header("📉 5-Year Rolling Return")
num_funds = len(selected_funds)
num_cols = min(3, num_funds)  # up to 3 columns
cols = st.columns(num_cols)
col_index = 0
for fund in selected_funds:
    scheme_code = df_amfi[df_amfi["SchemeName"] == fund]["SchemeCode"].values[0]
    nav_df, _, _ = load_nav_history(scheme_code)
    if nav_df is None or len(nav_df) < 800:
        continue
    rolling_5yr = compute_rolling_return(nav_df)
    #fig, ax = plt.subplots(figsize=(4, 3))
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(rolling_5yr, label=fund)
    ax.set_title(fund, fontsize=10)
    ax.set_ylabel("%")
    ax.grid(True)
    cols[col_index].pyplot(fig)
    plt.close(fig)
    col_index = (col_index + 1) % num_cols


# ----------------- Export to Excel -----------------------
st.header("📥 Export to Excel")
excel_buf = io.BytesIO()
with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
    df_results.to_excel(writer, index=False, sheet_name="Summary")
    df_cat_avg.to_excel(writer, index=False, sheet_name="Category Avg")
st.download_button(
    "Download Excel File",
    data=excel_buf.getvalue(),
    file_name="MutualFund_Comparison.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# ----------------- Export to PDF -----------------------
st.header("📄 Download PDF Report")
pdf_data = create_pdf(df_results, charts_for_pdf)
st.download_button(
    label="Download PDF Report",
    data=pdf_data,
    file_name="MF_Comparison_Report.pdf",
    mime="application/pdf"
)

# Footer
st.markdown("---")
st.markdown("**Note:** This tool uses real-time mutual fund data from AMFI. "
           "Data accuracy depends on the source API availability.")
st.markdown("⚠️ **Disclaimer:** This is for informational purposes only and should not be considered as investment advice.")