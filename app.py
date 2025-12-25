import streamlit as st
import pandas as pd
import pdfplumber
from io import BytesIO
from deep_translator import GoogleTranslator

# --- Function to extract tables from PDF and translate ---
def pdf_to_dataframe_translate(pdf_file, target_lang='en') -> pd.DataFrame:
    """
    Extract tables from PDF, translate content to English if needed, and return as DataFrame.
    """
    all_rows = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    # Translate each cell to English
                    translated_row = [GoogleTranslator(source='auto', target=target_lang).translate(str(cell)) for cell in row]
                    all_rows.append(translated_row)

    # Convert to DataFrame
    df = pd.DataFrame(all_rows)
    # Assume first row is header
    df.columns = df.iloc[0]
    df = df[1:].reset_index(drop=True)

    # Convert numeric columns automatically
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='ignore')
    return df
