import pdfplumber
import pandas as pd
from deep_translator import GoogleTranslator

def pdf_to_dataframe_translate(pdf_file, target_lang='en') -> pd.DataFrame:
    """
    Extract tables from PDF, translate content to English, and return as DataFrame.
    Cleans data to handle nested lists and non-string cells.
    """
    all_rows = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    # Flatten each cell to string before translation
                    clean_row = []
                    for cell in row:
                        if isinstance(cell, list):
                            cell = ' '.join([str(c) for c in cell])
                        elif cell is None:
                            cell = ''
                        else:
                            cell = str(cell)
                        # Translate
                        translated_cell = GoogleTranslator(source='auto', target=target_lang).translate(cell)
                        clean_row.append(translated_cell)
                    all_rows.append(clean_row)

    # Convert to DataFrame
    df = pd.DataFrame(all_rows)
    # Use first row as header
    df.columns = df.iloc[0]
    df = df[1:].reset_index(drop=True)

    # Clean numeric columns safely
    for col in df.columns:
        # Convert lists to strings, strip spaces
        df[col] = df[col].apply(lambda x: ' '.join(x) if isinstance(x, list) else x)
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip()
        # Convert to numeric if possible
        df[col] = pd.to_numeric(df[col], errors='ignore')

    return df
