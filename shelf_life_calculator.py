import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from fpdf import FPDF
import tempfile

# ICH shelf life logic function
def ich_shelf_life_estimation(
    x_months: float,
    sig_change_acc: bool,
    sig_change_int: bool,
    stored_refrigerated: bool,
    stats_supported: bool,
    support_data_available: bool
) -> dict:
    result = {
        "Base Duration (X)": x_months,
        "Regression Shelf Life (Y)": None,
        "Proposed Shelf Life": x_months,
        "Decision": "No extrapolation",
        "Notes": ""
    }

    # Logic based on ICH decision tree
    if sig_change_acc:
        if stored_refrigerated:
            result["Proposed Shelf Life"] = x_months + 3
            result["Decision"] = "Extrapolation allowed for refrigerated product"
            result["Notes"] = "Significant change at accelerated, refrigerated storage → +3M"
        elif sig_change_int:
            result["Decision"] = "No extrapolation"
            result["Notes"] = "Significant change at intermediate prevents extrapolation"
        else:
            if stats_supported or support_data_available:
                result["Proposed Shelf Life"] = x_months + 3
                result["Decision"] = "Limited extrapolation with support"
                result["Notes"] = "Statistical support or additional data → +3M"
            else:
                result["Notes"] = "No support for extrapolation"
    else:
        if sig_change_int:
            result["Decision"] = "No extrapolation"
            result["Notes"] = "Significant change at intermediate prevents extrapolation"
        else:
            if stats_supported and support_data_available:
                result["Proposed Shelf Life"] = x_months + 6
                result["Decision"] = "Maximum extrapolation with full support"
                result["Notes"] = "Statistical and data support → +6M"
            elif stats_supported or support_data_available:
                result["Proposed Shelf Life"] = x_months + 3
                result["Decision"] = "Limited extrapolation with partial support"
                result["Notes"] = "One support condition met → +3M"
            else:
                result["Notes"] = "No extrapolation allowed (no support)"

    return result

# Streamlit UI
st.set_page_config(layout="wide")
st.title("📈 Shelf-Life Estimation with ICH Extrapolation")

st.markdown("### ✍️ Input Manual Data (25°C/60%RH)")
param = st.text_input("Parameter Name", "Assay")
spec_limit = st.number_input("Specification Limit", value=85.0)
initial = st.number_input("Initial Value", value=100.0)
m1 = st.number_input("1 Month", value=99.0)
m3 = st.number_input("3 Months", value=97.0)
m6 = st.number_input("6 Months", value=94.0)
m9 = st.number_input("9 Months", value=92.0)
m12 = st.number_input("12 Months", value=89.0)
m18 = st.number_input("18 Months", value=87.0)
m24 = st.number_input("24 Months", value=85.0)
m36 = st.number_input("36 Months", value=83.0)
m48 = st.number_input("48 Months", value=80.0)

values = [initial, m1, m3, m6, m9, m12, m18, m24, m36, m48]
times = [0, 1, 3, 6, 9, 12, 18, 24, 36, 48]

if st.button("📊 Calculate Shelf-Life"):
    df = pd.DataFrame({"Time": times, "Value": values})
    X = df["Time"].values.reshape(-1, 1)
    y = df["Value"].values
    model = LinearRegression()
    model.fit(X, y)
    pred = model.predict(X)
    slope = model.coef_[0]
    intercept = model.intercept_
    r2 = r2_score(y, pred)

    # Plot
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(X, y, color='blue', label='Observed')
    ax.plot(X, pred, color='red', label=f'Regression (R²={r2:.2f})')
    ax.axhline(y=spec_limit, color='green', linestyle='--', label=f'Spec Limit = {spec_limit}')
    ax.set_xlabel("Time (Months)")
    ax.set_ylabel("Value")
    ax.legend()
    ax.grid(True)
    st.pyplot(fig)

    if slope != 0:
        est_shelf_life = (spec_limit - intercept) / slope
        st.success(f"📌 Estimated Shelf-Life (regression): **{est_shelf_life:.2f} months**")
    else:
        st.warning("⚠️ Cannot calculate shelf-life: slope is zero.")
        est_shelf_life = None

    # ICH Criteria
    st.markdown("### 🧪 ICH Extrapolation Conditions")
    sig_acc = st.checkbox("Significant change at 3M Accelerated?", value=False)
    sig_int = st.checkbox("Significant change at 6M Intermediate?", value=False)
    refrig = st.checkbox("Stored refrigerated?", value=False)
    support = st.checkbox("Supporting data available?", value=False)
    stats = r2 >= 0.95

    x_max = max([t for t, v in zip(times, values) if v > 0])
    ich_result = ich_shelf_life_estimation(
        x_months=x_max,
        sig_change_acc=sig_acc,
        sig_change_int=sig_int,
        stored_refrigerated=refrig,
        stats_supported=stats,
        support_data_available=support
    )
    ich_result["Regression Shelf Life (Y)"] = round(est_shelf_life, 2) if est_shelf_life else "N/A"

    st.markdown("### 📄 ICH Decision Result")
    for k, v in ich_result.items():
        st.write(f"**{k}**: {v}")

    # PDF Export
    if st.button("📤 Download PDF Report"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Shelf-Life Estimation Report", ln=1, align="C")
        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Parameter: {param}", ln=1)
        pdf.cell(200, 10, txt=f"R²: {r2:.2f}", ln=1)
        if est_shelf_life:
            pdf.cell(200, 10, txt=f"Estimated Shelf-Life (Y): {est_shelf_life:.2f} months", ln=1)
        pdf.ln(5)
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(200, 10, txt="ICH Shelf-Life Decision", ln=1)
        pdf.set_font("Arial", size=12)
        for k, v in ich_result.items():
            pdf.cell(200, 10, txt=f"{k}: {v}", ln=1)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            pdf.output(f.name)
            st.download_button(
                label="📄 Download Report",
                data=open(f.name, "rb").read(),
                file_name="ICH_Shelf_Life_Report.pdf",
                mime="application/pdf"
            )



st.markdown("---")
st.markdown("Built for Pharma Quality Tools | ICH Stability Logic")
