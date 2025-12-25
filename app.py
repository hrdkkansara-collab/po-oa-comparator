from io import BytesIO
import streamlit as st
import pdfplumber
import pandas as pd
import re

st.set_page_config(page_title="PO vs OA Cloud Comparator", layout="wide")
st.title("📄 PO vs OA – Cloud Comparison Tool")

# -----------------------------
# Vendor Tolerances
# -----------------------------
VENDOR_TOLERANCES = {
    "Yuengchang": {"Thickness": 0.001, "Quantity_pct": 2.0},
    "Posco": {"Thickness": 0.0008, "Quantity_pct": 1.5},
    "Custom": {"Thickness": 0.001, "Quantity_pct": 2.0}
}

# -----------------------------
# PDF Text Extraction
# -----------------------------
def extract_text(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

# -----------------------------
# Line Item Extraction (Simple & Robust)
# -----------------------------
def extract_lines(text):
    rows = []
    for line in text.split("\n"):
        m = re.search(
            r"(\d+)\s+(.+?)\s+([\d\.]+)\"\s*x\s*([\d\.]+)\"\s+([\d,]+)\s*(LBS|KG)\s+\$([\d\.]+)",
            line,
            re.I
        )
        if m:
            rows.append({
                "Line": m.group(1),
                "Material": m.group(2),
                "Thickness": float(m.group(3)),
                "Width": float(m.group(4)),
                "Quantity": float(m.group(5).replace(",", "")),
                "Unit Price": float(m.group(7))
            })
    return pd.DataFrame(rows)

# -----------------------------
# Comparison Logic
# -----------------------------
def compare(po, oa, tol):
    results = []

    for _, p in po.iterrows():
        line = p["Line"]
        o = oa[oa["Line"] == line]

        if o.empty:
            results.append([line, "Line Item", "Present", "Missing", "", "", "❌"])
            continue

        o = o.iloc[0]

        # Quantity comparison
        diff = o["Quantity"] - p["Quantity"]
        pct = (diff / p["Quantity"]) * 100
        status = "✅ OK" if abs(pct) <= tol["Quantity_pct"] else "❌ Over tolerance"

        results.append([
            line, "Quantity (LBS)",
            p["Quantity"], o["Quantity"],
            f"{diff:+,.0f}",
            f"{pct:+.2f}%",
            status
        ])

        # Thickness
        tdiff = o["Thickness"] - p["Thickness"]
        tstatus = "✅ OK" if abs(tdiff) <= tol["Thickness"] else "❌ Out of tolerance"

        results.append([
            line, "Thickness",
            p["Thickness"], o["Thickness"],
            f"{tdiff:+.4f}", "", tstatus
        ])

    return pd.DataFrame(
        results,
        columns=["Line", "Field", "PO Value", "OA Value", "Difference", "% Change", "Status"]
    )

# -----------------------------
# UI
# -----------------------------
vendor = st.selectbox("Select Vendor", VENDOR_TOLERANCES.keys())
tol = VENDOR_TOLERANCES[vendor]

st.subheader("⚙️ Editable Tolerances")

tol["Thickness"] = st.number_input("Thickness ± (in)", value=tol["Thickness"], step=0.0001)
tol["Quantity_pct"] = st.number_input("Quantity ± (%)", value=tol["Quantity_pct"], step=0.1)

col1, col2 = st.columns(2)
with col1:
    po_file = st.file_uploader("Upload PO (PDF)", type="pdf")
with col2:
    oa_file = st.file_uploader("Upload OA (PDF)", type="pdf")

if po_file and oa_file:
    if st.button("🔍 Compare"):
        po_df = extract_lines(extract_text(po_file))
        oa_df = extract_lines(extract_text(oa_file))

        result = compare(po_df, oa_df, tol)

        st.subheader("📊 Comparison Results")
        st.dataframe(result, use_container_width=True)

      excel_buffer = BytesIO()
result.to_excel(excel_buffer, index=False)
excel_buffer.seek(0)

st.download_button(
    label="📥 Download Excel",
    data=excel_buffer,
    file_name="PO_vs_OA_Comparison.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
