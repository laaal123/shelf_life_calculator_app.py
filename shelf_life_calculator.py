

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from fpdf import FPDF
import tempfile
import os
from io import BytesIO

st.set_page_config(layout="wide")
st.title("📈 Shelf-Life Calculator from Stability Data (ICH Based)")

st.markdown("### 📂 Upload CSV File or Enter Data Manually")

uploaded_file = st.file_uploader(
    "Upload CSV with columns: Time, Condition, Parameter, Value",
    type=["csv"]
)

manual_input = st.checkbox("Or Enter Data Manually")

# Initialize dataset
data = pd.DataFrame(columns=["Time", "Condition", "Parameter", "Value"])
manual_spec_limits = {}
results_summary = []
figures = []

if uploaded_file:
    try:
        data = pd.read_csv(uploaded_file)
        st.success("CSV loaded successfully.")
    except Exception as e:
        st.error(f"Error loading CSV: {e}")

elif manual_input:
    with st.form("manual_form"):
        condition = st.selectbox("Stability Condition", ["25C_60RH", "30C_65RH", "40C_75RH"])
        param_name = st.text_input("Parameter Name", "Assay")
        timepoints = st.text_area("Time Points (comma-separated)", "0,1,3,6,9,12")
        values = st.text_area("Values (comma-separated)", "100,98,95,92,90,88")
        spec_limit = st.number_input("Specification Limit", value=85.0, step=0.1)
        submit = st.form_submit_button("Add to Dataset")

        if submit:
            try:
                tpts = [float(t.strip()) for t in timepoints.split(",")]
                vals = [float(v.strip()) for v in values.split(",")]
                if len(tpts) != len(vals):
                    st.error("Time and value counts must match.")
                else:
                    new_data = pd.DataFrame({
                        "Time": tpts,
                        "Condition": condition,
                        "Parameter": param_name,
                        "Value": vals
                    })
                    data = pd.concat([data, new_data], ignore_index=True)
                    manual_spec_limits[(param_name, condition)] = spec_limit
                    st.success("Added successfully.")
            except:
                st.error("Invalid input format.")

# ICH logic function
def estimate_shelf_life_ich(x, stats=False, support_data=False, refrigerated=False, failure_month=None):
    formula = ""
    if failure_month is not None and failure_month <= x:
        formula = f"Failed at {failure_month} months"
        return failure_month, formula
    if stats and support_data:
        if refrigerated:
            formula = "min(1.5 * x, x + 6)  # ICH Case 2"
            return min(1.5 * x, x + 6), formula
        else:
            formula = "min(2 * x, x + 12)  # ICH Case 1"
            return min(2 * x, x + 12), formula
    elif stats or support_data:
        if refrigerated:
            formula = "x + 3  # ICH Case 4"
            return x + 3, formula
        else:
            formula = "min(1.5 * x, x + 6)  # ICH Case 3"
            return min(1.5 * x, x + 6), formula
    else:
        formula = "x  # ICH Case 5"
        return x, formula

if not data.empty:
    st.markdown("### 👁️ Data Preview")
    st.dataframe(data)

    for (condition, param), df_group in data.groupby(["Condition", "Parameter"]):
        st.markdown(f"#### 📊 Regression: {param} under {condition}")
        df = df_group.sort_values("Time")
        X = df["Time"].values.reshape(-1, 1)
        y = df["Value"].values

        model = LinearRegression().fit(X, y)
        pred = model.predict(X)
        slope, intercept = model.coef_[0], model.intercept_
        r2 = r2_score(y, pred)

        threshold = manual_spec_limits.get((param, condition), 85.0)
        if st.checkbox(f"Set spec limit for {param} at {condition}?", key=f"spec_{param}_{condition}"):
            threshold = st.number_input(f"Spec limit for {param}-{condition}", value=threshold, key=f"thresh_{param}_{condition}")

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.scatter(X, y, label="Observed", color="blue")
        ax.plot(X, pred, label=f"Fit (R²={r2:.2f})", color="red")
        ax.axhline(y=threshold, color="green", linestyle="--", label=f"Spec = {threshold}")
        ax.set_title(f"{param} over Time ({condition})")
        ax.set_xlabel("Months")
        ax.set_ylabel("Value")
        ax.grid(True)
        ax.legend()
        st.pyplot(fig)

        tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        fig.savefig(tmpfile.name)
        figures.append((param, condition, tmpfile.name))

        if slope != 0:
            est_months = (threshold - intercept) / slope
            if est_months > 0:
                st.success(f"Estimated Shelf-Life: {est_months:.2f} months")

                support = st.checkbox(f"Supporting data for {param}-{condition}?", key=f"sup_{param}_{condition}")
                cold = st.checkbox(f"Refrigerated product?", key=f"cold_{param}_{condition}")
                failed = st.checkbox(f"Did it fail?", key=f"fail_{param}_{condition}")
                fail_mo = None
                if failed:
                    fail_mo = st.number_input("Failure month", min_value=0.0, max_value=est_months, key=f"fail_month_{param}_{condition}")

                stats_pass = r2 >= 0.95
                ich_months, formula_used = estimate_shelf_life_ich(est_months, stats_pass, support, cold, fail_mo)

                results_summary.append({
                    "Parameter": param,
                    "Condition": condition,
                    "R2": round(r2, 3),
                    "Estimated Shelf Life": round(est_months, 2),
                    "ICH Shelf Life": round(ich_months, 2),
                    "Formula": formula_used
                })

                st.success(f"ICH Shelf-Life = {ich_months:.2f} months using `{formula_used}`")
            else:
                st.warning("Estimated time is negative — already below threshold.")
        else:
            st.error("Flat regression line. Cannot compute shelf life.")

# PDF report
if results_summary:
    if st.button("📂 Download Combined Report as PDF"):
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Stability Summary Report", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", '', 12)

        for res in results_summary:
            for k, v in res.items():
                pdf.cell(0, 8, f"{k}: {v}", ln=True)
            pdf.ln(4)

        for param, cond, path in figures:
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, f"Graph: {param} under {cond}", ln=True)
            pdf.image(path, x=10, y=30, w=180)

        buf = BytesIO()
        pdf.output(buf)
        buf.seek(0)

        st.download_button("📄 Download PDF Report", data=buf, file_name="Stability_Report.pdf", mime="application/pdf")

st.markdown("---")
st.markdown("Built for Pharma Quality Tools | ICH Stability Logic")
