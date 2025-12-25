import streamlit as st
import pandas as pd
import pdfplumber
from io import BytesIO
from deep_translator import GoogleTranslator

# ---------------------- PDF Parsing + Translation ----------------------
def pdf_to_dataframe_translate(pdf_file, target_lang='en') -> pd.DataFrame:
    """
    Extract tables from PDF, translate content to English, return as DataFrame.
    Handles nested lists, None cells, empty tables, and safely converts numeric columns.
    """
    all_rows = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                for row in table:
                    clean_row = []
                    for cell in row:
                        if isinstance(cell, list):
                            cell = ' '.join([str(c) for c in cell])
                        elif cell is None:
                            cell = ''
                        else:
                            cell = str(cell)
                        translated_cell = GoogleTranslator(source='auto', target=target_lang).translate(cell)
                        clean_row.append(translated_cell)
                    all_rows.append(clean_row)

    if not all_rows:
        return pd.DataFrame()  # return empty DataFrame if no table found

    df = pd.DataFrame(all_rows)

    # Use first row as header if more than one row
    if len(df) > 1:
        df.columns = df.iloc[0]
        df = df[1:].reset_index(drop=True)
    else:
        df.columns = [f"Column_{i}" for i in range(len(df.columns))]

    # Safely clean numeric columns
    for col in df.columns:
        if col not in df:
            continue
        df[col] = df[col].apply(lambda x: ' '.join(x) if isinstance(x, list) else x)
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip()
        df[col] = pd.to_numeric(df[col], errors='ignore')

    return df

# ---------------------- Comparison with Tolerance ----------------------
def compare_po_oa(po_df: pd.DataFrame, oa_df: pd.DataFrame, tolerances: dict) -> pd.DataFrame:
    merged = pd.merge(po_df, oa_df, on='Item', suffixes=('_PO', '_OA'), how='outer')
    comparison_results = merged.copy()

    for col in po_df.columns:
        if col in tolerances and pd.api.types.is_numeric_dtype(po_df[col]):
            po_col = f"{col}_PO"
            oa_col = f"{col}_OA"
            comparison_results[f"{col}_Diff"] = comparison_results[oa_col] - comparison_results[po_col]
            comparison_results[f"{col}_%Diff"] = (comparison_results[f"{col}_Diff"] / comparison_results[po_col]) * 100
            comparison_results[f"{col}_Within_Tolerance"] = comparison_results[f"{col}_%Diff"].abs() <= tolerances[col]

    return comparison_results

# ---------------------- Export to Excel ----------------------
def export_to_excel(df: pd.DataFrame) -> BytesIO:
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    return excel_buffer

# ---------------------- Streamlit UI ----------------------
st.title("Cloud PO vs OA Comparator with PDF Translation & Tolerance")

# File uploads
po_file = st.file_uploader("Upload Purchase Order (PDF/Excel/CSV)", type=["pdf","xlsx","csv"])
oa_file = st.file_uploader("Upload Order Acknowledgement (PDF/Excel/CSV)", type=["pdf","xlsx","csv"])

st.sidebar.header("Tolerance Settings (%)")
tolerances = {}

# Read PO
if po_file:
    if po_file.name.endswith(".pdf"):
        po_df = pdf_to_dataframe_translate(po_file)
    elif po_file.name.endswith(".xlsx"):
        po_df = pd.read_excel(po_file)
    else:
        po_df = pd.read_csv(po_file)

    numeric_cols = po_df.select_dtypes(include='number').columns.tolist()
    for col in numeric_cols:
        tolerances[col] = st.sidebar.number_input(f"Tolerance for {col} (%)", value=5.0, step=0.1)

# Read OA
if oa_file:
    if oa_file.name.endswith(".pdf"):
        oa_df = pdf_to_dataframe_translate(oa_file)
    elif oa_file.name.endswith(".xlsx"):
        oa_df = pd.read_excel(oa_file)
    else:
        oa_df = pd.read_csv(oa_file)

# Run comparison
if po_file and oa_file:
    result = compare_po_oa(po_df, oa_df, tolerances)
    
    st.subheader("Comparison Result")
    st.dataframe(result)

    # Download Excel
    excel_file = export_to_excel(result)
    st.download_button(
        label="Download Comparison as Excel",
        data=excel_file,
        file_name="PO_OA_Comparison.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Please upload both PO and OA files to run comparison.")
