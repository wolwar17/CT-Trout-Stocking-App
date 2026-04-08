import streamlit as st
import pandas as pd
import pdfplumber
import requests
from io import BytesIO

st.set_page_config(page_title="CT Fish Stocking Finder", page_icon="🎣")

st.title("🎣 CT Fish Stocking Finder")

# The live PDF URL
PDF_URL = "https://portal.ct.gov/-/media/deep/fishing/weekly_reports/currentstockingreport.pdf?rev=f830018b6088465bb62af3a42587eea0"

@st.cache_data(ttl=3600)
def download_and_parse_pdf(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        all_rows = []
        with pdfplumber.open(BytesIO(response.content)) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    all_rows.extend(table)
        
        if all_rows:
            df = pd.DataFrame(all_rows)
            df = df.dropna(how='all')
            # Clean and Sort immediately upon download
            df = df.iloc[:, :3]
            df.columns = ["Water Body", "Town", "Stocked"]
            df = df[df["Water Body"] != "Water Body"]
            df['Stocked_Date'] = pd.to_datetime(df['Stocked'], errors='coerce')
            df = df.sort_values(by='Stocked_Date', ascending=False)
            return df
        return None
    except Exception as e:
        st.error(f"Technical Error: {e}")
        return None

# --- APP FLOW ---

# 1. Download data first
df = download_and_parse_pdf(PDF_URL)

# 2. Show Search Input
search_term = st.text_input("Enter a Town or Waterbody (e.g., Wolcott or Scoville)")

# 3. Handle Results
if df is not None:
    if search_term:
        # Filter based on search
        mask = df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)
        results = df[mask]
        
        if not results.empty:
            st.success(f"Found {len(results)} matches for '{search_term}'")
            st.dataframe(results[["Water Body", "Town", "Stocked"]], use_container_width=True, hide_index=True)
        else:
            st.info(f"No stockings found for '{search_term}'.")
    else:
        # IF BLANK: Show the 20 most recent
        st.subheader("🗓️ 20 Most Recent Stockings in CT")
        recent_20 = df.head(20)
        st.dataframe(recent_20[["Water Body", "Town", "Stocked"]], use_container_width=True, hide_index=True)
else:
    st.error("Could not load the report. Check your internet connection or the PDF link.")