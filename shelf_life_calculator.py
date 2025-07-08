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

# Initialize empty DataFrame
data = pd.DataFrame(columns=["Time", "Condition", "Parameter", "Value"])
manual_spec_limits = {}
results_summary = []
figures = []

if uploaded_file is not None:
    try:
        data = pd.read_csv(uploaded_file)
        st.success("CSV loaded successfully.")
    except Exception as e:
        st.error(f"Error loading CSV: {e}")

elif manual_input:
    st.markdown("### 📝 Manual Input Table")
    with st.form("manual_form"):
        condition = st.selectbox("Stability Condition", ["25C_60RH", "30C_65RH", "40C_75RH"])
        param_name = st.text_input("Parameter Name (e.g., Assay)", "Assay")
        timepoints = st.text_area("Enter Time Points (comma-separated)", "0,1,3,6,9,12")
        values = st.text_area("Enter Values (comma-separated)", "100,98,95,92,90,88")
        spec_limit = st.number_input("Specification Limit for Shelf Life Calculation", value=85.0, step=0.1)
        submit = st.form_submit_button("Add to Dataset")

        if submit:
            try:
                tpts = [float(t.strip()) for t in timepoints.split(",")]
                vals = [float(v.strip()) for v in values.split(",")]
                if len(tpts) != len(vals):
                    st.error("Time and Value counts must match.")
                else:
                    new_data = pd.DataFrame({
                        "Time": tpts,
                        "Condition": condition,
                        "Parameter": param_name,
                        "Value": vals
                    })
                    data = pd.concat([data, new_data], ignore_index=True)
                    manual_spec_limits[(param_name, condition)] = spec_limit
                    st.success("Data and specification limit added successfully.")
            except:
                st.error("Invalid format. Please enter numbers only.")

# Define ICH shelf-life extrapolation logic
def estimate_shelf_life_ich(x, stats=False, support_data=False, refrigerated=False, failure_month=None):
    if failure_month is not None and failure_month <= x:
        return failure_month
    if stats and support_data:
        return min(2 * x, x + 12) if not refrigerated else min(1.5 * x, x + 6)
    elif stats or support_data:
        return min(1.5 * x, x + 6) if not refrigerated else x + 3
    else:
        return x

if not data.empty:
    st.markdown("### 👁️ Data Preview")
    st.dataframe(data)

    for (condition, param), df_group in data.groupby(["Condition", "Parameter"]):
        st.markdown(f"#### 📊 Regression for: {param} under {condition}")
        df = df_group.sort_values("Time")

        X = df["Time"].values.reshape(-1, 1)
        y_values = df["Value"].values

        model = LinearRegression()
        model.fit(X, y_values)
        pred = model.predict(X)
        slope = model.coef_[0]
        intercept = model.intercept_
        r2 = r2_score(y_values, pred)

        st.markdown("**📏 Shelf-Life Estimation**")
        default_threshold = manual_spec_limits.get((param, condition), 85.0)

        manual_spec_limit = st.checkbox(
            f"Set specification limit manually for {param} under {condition}?",
            key=f"manual_spec_limit_{param}_{condition}"
        )
        if manual_spec_limit:
            threshold = st.number_input(
                f"Enter specification limit for {param} under {condition}",
                value=default_threshold,
                key=f"thresh_manual_{param}_{condition}"
            )
        else:
            threshold = default_threshold

        # Plotting
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.scatter(X, y_values, label="Observed", color="blue")
        ax.plot(X, pred, label=f"Regression (R²={r2:.3f})", color="red")
        ax.axhline(y=threshold, color="green", linestyle="--", label=f"Spec Limit = {threshold}")
        ax.set_title(f"{param} vs Time ({condition})")
        ax.set_xlabel("Time (Months)")
        ax.set_ylabel("Value")
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        fig.savefig(temp_file.name)
        figures.append((param, condition, temp_file.name))

        if slope != 0:
            est_time = (threshold - intercept) / slope
            if est_time > 0:
                st.success(f"Estimated shelf-life for {param} at {condition}: **{est_time:.2f} months**")

                st.markdown("**📘 ICH Evaluation**")

                support_data_flag = st.checkbox(f"Is there supporting data for {param} under {condition}?", key=f"support_{param}_{condition}")
                refrigerated_flag = st.checkbox(f"Is the product stored refrigerated for {param} under {condition}?", key=f"refrig_{param}_{condition}")
                failure_flag = st.checkbox(f"Did the product fail during study for {param} under {condition}?", key=f"fail_{param}_{condition}")
                failure_month = None
                if failure_flag:
                    failure_month = st.number_input(f"Enter failure month for {param} under {condition}", min_value=0.0, max_value=est_time, key=f"failmonth_{param}_{condition}")

                stats_flag = r2 >= 0.95

                ich_shelf = estimate_shelf_life_ich(
                    x=est_time,
                    stats=stats_flag,
                    support_data=support_data_flag,
                    refrigerated=refrigerated_flag,
                    failure_month=failure_month
                )

                result = {
                    "Parameter": param,
                    "Condition": condition,
                    "R2": round(r2, 3),
                    "Estimated Shelf Life": round(est_time, 2),
                    "ICH Shelf Life (max)": round(ich_shelf, 2)
                }

                results_summary.append(result)

                st.info(f"R² = {r2:.2f} {'✅' if stats_flag else '❌'} | Supporting data: {'✅' if support_data_flag else '❌'} | Refrigerated: {'✅' if refrigerated_flag else '❌'}")
                st.success(f"📉 ICH-Extrapolated Shelf-Life: **{ich_shelf:.2f} months**")
            else:
                st.warning("Regression suggests value is already below the threshold.")
        else:
            st.error("Slope is zero; cannot compute shelf-life.")

# PDF export
if results_summary:
    if st.button("📂 Download Combined Report as PDF"):
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Stability Study Summary Report", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", '', 12)

        for res in results_summary:
            for key, value in res.items():
                pdf.cell(0, 8, f"{key}: {value}", ln=True)
            pdf.ln(4)

        for param, condition, img_path in figures:
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, f"Graph for {param} under {condition}", ln=True)
            pdf.image(img_path, x=10, y=30, w=180)

        pdf_buffer = BytesIO()
        pdf.output(pdf_buffer)
        pdf_buffer.seek(0)

        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_buffer,
            file_name="Stability_Report.pdf",
            mime="application/pdf"
        )

st.markdown("---")
st.markdown("Built for Stability Analysis | Pharma Quality Tools")


