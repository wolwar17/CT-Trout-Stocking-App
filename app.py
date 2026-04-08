import streamlit as st
import pandas as pd
import pdfplumber
import requests
from io import BytesIO

# --- APP CONFIGURATION ---
st.set_page_config(page_title="CT Fish Stocking Finder", page_icon="🎣")

st.title("🎣 CT Fish Stocking Finder")

# The live PDF URL
PDF_URL = "https://portal.ct.gov/-/media/deep/fishing/weekly_reports/currentstockingreport.pdf?rev=f830018b6088465bb62af3a42587eea0"

@st.cache_data(ttl=3600)
def download_and_parse_pdf(url):
    try:
        response = requests.get(url, timeout=15)
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
            
            # 1. Keep only first 3 columns
            df = df.iloc[:, :3]
            df.columns = ["Water Body", "Town", "Stocked"]
            
            # 2. Filter out header rows
            df = df[df["Water Body"] != "Water Body"]
            
            # 3. Handle multiple dates (e.g., "3/18, 4/7")
            # Grabs the LAST date string after the comma
            df['Sort_Date_String'] = df['Stocked'].str.split(',').str[-1].str.strip()
            
            # 4. Convert to real date for sorting
            df['Stocked_Date'] = pd.to_datetime(df['Sort_Date_String'], errors='coerce')
            
            # 5. MULTI-SORT: Towns A-Z, then Dates Newest to Oldest
            df = df.sort_values(
                by=['Town', 'Stocked_Date'], 
                ascending=[True, False]
            )
            
            return df
        return None
    except Exception as e:
        st.error(f"Technical Error: {e}")
        return None

# --- MAIN APP FLOW ---

df = download_and_parse_pdf(PDF_URL)

# .strip() handles the "Middletown " (with a space) problem
search_term = st.text_input("Search by Town or Body of Water (e.g., Wolcott or Southbury)").strip()

if df is not None:
    display_df = df[["Water Body", "Town", "Stocked"]]

    if search_term:
        # Search across all columns
        mask = df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)
        results = display_df[mask]
        
        if not results.empty:
            st.success(f"Showing {len(results)} matches for '{search_term}'")
            st.dataframe(results, use_container_width=True, hide_index=True)
        else:
            st.info(f"No results found for '{search_term}'. (Try checking your spelling!)")
    else:
        st.subheader("🗓️ 20 Most Recent Stockings in CT")
        # Ensure we show absolute newest first when no search is present
        recent_20 = df.sort_values(by='Stocked_Date', ascending=False).head(20)
        st.dataframe(recent_20[["Water Body", "Town", "Stocked"]], use_container_width=True, hide_index=True)

else:
    st.error("The app couldn't retrieve the report.")

st.divider()
st.caption("Tip: This app ignores accidental spaces at the end of your search!")
