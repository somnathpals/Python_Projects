import streamlit as st
import pandas as pd
import numpy as np
import requests
import matplotlib.pyplot as plt
from fpdf import FPDF
import io
import plotly.graph_objects as go

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

#def compute_rolling_return(df, years=5):
#    days = years * 365
#    df = df.set_index("date")
#    df["rolling"] = df["nav"].pct_change(days) * 100
#    return df["rolling"].dropna()

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

def create_pdf(results_df, charts, combined_chart_buf):
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
            f"Annualized CAGR: {row['Annualized CAGR']:.2f}%\n"
            f"5Y Rolling CAGR: {row['Rolling CAGR 5Y']:.2f}%\n"
        )
        pdf.ln(3)

#    # Individual fund charts
#    pdf.add_page()
#    pdf.cell(200, 10, "Rolling Return Charts", ln=True)
#    for name, img_bytes in charts.items():
#        pdf.ln(5)
#        pdf.cell(200, 6, name, ln=True)
#        pdf.image(img_bytes, w=170)

    # Combined rolling return chart
    pdf.add_page()
    pdf.cell(200, 10, "Combined 5-Year Rolling CAGR", ln=True)
    pdf.image(combined_chart_buf, w=170)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()

# ------------------------- Streamlit UI --------------------------

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
st.write("Select multiple funds from AMFI list and compare metrics including Annualized CAGR, 5-year Rolling CAGR, AUM, Category Average Annualized CAGR, and export to Excel/PDF.")

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
    nav_df, category, aum = load_nav_history(scheme_code)
    if nav_df is None or len(nav_df) < 800:
        st.warning(f"Not enough NAV data for {fund}")
        continue
    rolling_5yr = compute_rolling_cagr(nav_df)
    rolling_returns_dict[fund] = rolling_5yr
    cagr = compute_cagr(nav_df)
    category_groups.setdefault(category, []).append(cagr)
    results.append({
        "Fund": fund,
        "NAV": nav_df["nav"].iloc[-1],
        "AUM": aum,
        "Annualized CAGR": cagr,
        "5Y Rolling CAGR": rolling_5yr.mean(),
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
st.header("📊 Category Average Annualized CAGR")
cat_avg = {cat: np.mean(vals) for cat, vals in category_groups.items()}
df_cat_avg = pd.DataFrame(list(cat_avg.items()), columns=["Category", "Avg CAGR (%)"])
st.dataframe(df_cat_avg, width='stretch')

# ------------------- Combined 5-Year Rolling Return Chart (Interactive) -------------------
st.header("📉 5-Year Rolling CAGR (Interactive Combined Chart)")

fig_plotly = go.Figure()
for fund, rolling_5yr in rolling_returns_dict.items():
    fig_plotly.add_trace(go.Scatter(
        x=rolling_5yr.index,
        y=rolling_5yr.values,
        mode='lines',
        name=fund,
        hovertemplate='Date: %{x|%d-%b-%Y}<br>Rolling Return: %{y:.2f}%<extra></extra>'
    ))

fig_plotly.update_layout(
    title="5-Year Rolling CAGR Comparison",
    xaxis_title="Date",
    yaxis_title="Rolling Return (%)",
    hovermode="x unified",
    template="plotly_white",
    height=500
)

st.plotly_chart(fig_plotly, width='stretch')

# Save combined chart for PDF (Matplotlib static)
fig, ax = plt.subplots(figsize=(10, 5))
for fund, rolling_5yr in rolling_returns_dict.items():
    ax.plot(rolling_5yr.index, rolling_5yr.values, label=fund)
ax.set_title("5-Year Rolling CAGR Comparison")
ax.set_ylabel("Rolling Return (%)")
ax.grid(True)   
ax.legend()
combined_chart_buf = io.BytesIO()
plt.savefig(combined_chart_buf, format="png")
combined_chart_buf.seek(0)
plt.close(fig)

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
pdf_data = create_pdf(df_results, charts_for_pdf, combined_chart_buf)
st.download_button(
    label="Download PDF Report",
    data=pdf_data,
    file_name="MF_Comparison_Report.pdf",
    mime="application/pdf"
)
