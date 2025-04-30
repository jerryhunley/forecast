import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta

# Set custom theme colors based on 1nHealth brand guidelines
st.set_page_config(page_title="Recruitment Forecast Dashboard", layout="wide")
st.markdown("""
    <style>
        :root {
            --primary-color: #53CA97;  /* Mint */
            --secondary-color: #7991C6;  /* Vista Blue */
            --text-color: #1B2222;  /* Eerie Black */
            --background-color: #F8F8F8;  /* Seasalt */
        }
        html, body, [class*="css"]  {
            background-color: var(--background-color);
            color: var(--text-color);
            font-family: "Manrope", sans-serif;
        }
        .stButton>button {
            background-color: var(--primary-color);
            color: white;
        }
        .stSlider>div>div>div[role=slider] {
            background-color: var(--secondary-color);
        }
        .stTextInput>div>input, .stNumberInput>div>input {
            border: 1px solid var(--primary-color);
        }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Clinical Trial Recruitment Forecasting Tool")

st.markdown("""
This app estimates study end dates, analyzes funnel trends, and calculates site-level cost efficiency.
Upload your referral data, ad spend by DMA, and site list to begin.
""")

# --- Upload Section ---
referral_file = st.file_uploader("📥 Upload Referral Data (CSV)", type="csv")
spend_file = st.file_uploader("📥 Upload Ad Spend Data (CSV)", type="csv")
site_file = st.file_uploader("📥 Upload Site Master List (CSV)", type="csv")

if referral_file and spend_file and site_file:
    referrals = pd.read_csv(referral_file)
    spend = pd.read_csv(spend_file)
    sites = pd.read_csv(site_file)

    # --- Clean and Merge Data ---
    st.subheader("1️⃣ Funnel Overview")

    referrals['Signed ICF'] = referrals['Signed ICF Date'].notna().astype(int)
    funnel_summary = referrals.groupby('Site Number').agg(
        Referrals=('Signed ICF Date', 'count'),
        ICFs=('Signed ICF', 'sum')
    ).reset_index()

    # Merge with site info
    sites['DMA Key'] = sites['City'].str.lower().str.strip() + ", " + sites['State'].str.lower().str.strip()
    spend['DMA Key'] = spend['DMA region'].str.lower().str.strip()
    dma_spend = spend.groupby('DMA Key')['Amount spent (USD)'].sum().reset_index(name='DMA Spend')

    merged = sites.merge(dma_spend, on='DMA Key', how='left')
    merged = merged.merge(funnel_summary, on='Site Number', how='left')
    merged[['Referrals', 'ICFs']] = merged[['Referrals', 'ICFs']].fillna(0)

    # Estimate referral share and prorate spend
    dma_totals = merged.groupby('DMA Key')['Referrals'].sum().reset_index(name='DMA Ref Total')
    merged = merged.merge(dma_totals, on='DMA Key', how='left')
    merged['Referral Share'] = merged['Referrals'] / merged['DMA Ref Total']
    merged['Est. Site Spend'] = merged['Referral Share'] * merged['DMA Spend']
    merged['CPR'] = merged['Est. Site Spend'] / merged['Referrals'].replace(0, np.nan)
    merged['CPICF'] = merged['Est. Site Spend'] / merged['ICFs'].replace(0, np.nan)

    st.dataframe(merged[['Site Number', 'Site', 'City', 'State', 'Referrals', 'ICFs',
                         'Est. Site Spend', 'CPR', 'CPICF']].sort_values(by='CPICF'))

    # --- Forecast Section ---
    st.subheader("2️⃣ ICF Forecasting")
    icfs_needed = st.number_input("How many additional ICFs do you need?", min_value=1, value=50)
    cpql = st.number_input("Current Cost per Qualified Lead (CPQL)", min_value=0.0, value=60.0)
    conversion_rate = st.slider("Estimated Referral → ICF Rate", min_value=0.005, max_value=0.10, value=0.04)
    weekly_referrals = st.slider("Avg Weekly Referrals (Top Sites Focused)", min_value=10, max_value=1000, value=260)

    needed_referrals = int(icfs_needed / conversion_rate)
    weeks_to_goal = needed_referrals / weekly_referrals
    days_to_goal = int(weeks_to_goal * 7 + 63)  # Add lag

    st.markdown(f"""
    ### 📅 Projection Results:
    - Required Referrals: **{needed_referrals}**
    - Estimated Weeks to Fill Funnel: **{weeks_to_goal:.1f}**
    - **Estimated Study End (Milestone) in ~{days_to_goal} days**
    """)

    st.success("Model complete. Adjust inputs to simulate different scenarios.")

else:
    st.warning("⬆️ Please upload all 3 required files to begin.")
