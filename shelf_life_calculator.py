import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

st.set_page_config(layout="wide")
st.title("📈 Shelf-Life Calculator from Stability Data (ICH Based)")

st.markdown("### 📂 Upload CSV File or Enter Data Manually")

uploaded_file = st.file_uploader("Upload CSV with columns: Time, Condition, Parameter, Value", type=["csv"])
manual_input = st.checkbox("Or Enter Data Manually")

# Initialize DataFrame
data = pd.DataFrame(columns=["Time", "Condition", "Parameter", "Value"])

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
        submit = st.form_submit_button("Add to Dataset")

        if submit:
            try:
                tpts = [float(t.strip()) for t in timepoints.split(",")]
                vals = [float(v.strip()) for v in values.split(",")]
                if len(tpts) != len(vals):
                    st.error("Time and Value counts must match.")
                else:
                    new_data = pd.DataFrame({"Time": tpts, "Condition": condition, "Parameter": param_name, "Value": vals})
                    data = pd.concat([data, new_data], ignore_index=True)
                    st.success("Data added successfully.")
            except:
                st.error("Invalid format. Please enter numbers only.")

# Show data preview
if not data.empty:
    st.markdown("### 👁️ Data Preview")
    st.dataframe(data)

    for (condition, param), df_group in data.groupby(["Condition", "Parameter"]):
        st.markdown(f"#### 📊 Regression for: {param} under {condition}")
        df = df_group.sort_values("Time")

        X = df["Time"].values.reshape(-1, 1)
        y = df["Value"].values

        model = LinearRegression()
        model.fit(X, y)
        pred = model.predict(X)
        slope = model.coef_[0]
        intercept = model.intercept_
        r2 = r2_score(y, pred)

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.scatter(X, y, label="Observed", color="blue")
        ax.plot(X, pred, label=f"Regression (R²={r2:.3f})", color="red")
        ax.set_title(f"{param} vs Time ({condition})")
        ax.set_xlabel("Time (Months)")
        ax.set_ylabel("Value")
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)

        st.markdown("**📏 Shelf-Life Estimation**")

# Add a checkbox for manual threshold input
manual_spec_limit = st.checkbox(
    f"Set specification limit manually for {param} under {condition}?", 
    key=f"manual_spec_limit_{param}_{condition}"
)

if manual_spec_limit:
    threshold = st.number_input(
        f"Enter specification limit for {param} under {condition}",
        value=85.0,
        key=f"thresh_manual_{param}_{condition}"
    )
else:
    threshold = 85.0  # default value

if slope != 0:
    est_time = (threshold - intercept) / slope
    if est_time > 0:
        st.success(f"Estimated shelf-life for {param} at {condition}: **{est_time:.2f} months**")

        st.markdown("**📘 ICH Evaluation**")
        if r2 >= 0.95:
            st.info("The regression model shows strong correlation (R² ≥ 0.95) as per ICH guidelines.")
        else:
            st.warning("The regression model shows weak correlation (R² < 0.95), may not meet ICH criteria.")

        if df.shape[0] >= 3 and len(set(df["Time"])) >= 3:
            st.success("Meets minimum ICH timepoint requirement for shelf-life estimation (≥3 distinct timepoints).")
        else:
            st.warning("Less than 3 timepoints detected — not suitable for ICH shelf-life justification.")

        if condition.startswith("40"):
            st.info("Accelerated data used. Extrapolation allowed if no significant change and supported by long-term data.")
        elif condition.startswith("25") or condition.startswith("30"):
            st.info("Long-term condition. Shelf-life based directly on observed trends.")

    else:
        st.warning("Regression indicates value is already below threshold.")
else:
    st.error("Slope is zero; cannot compute shelf-life.")

         # ICH Decision Tree-based logic (simplified)
                if condition.startswith("40"):
                    st.info("Accelerated data used. Extrapolation allowed if no significant change and supported by long-term data.")
                elif condition.startswith("25") or condition.startswith("30"):
                    st.info("Long-term condition. Shelf-life based directly on observed trends.")

            else:
                st.warning("Regression indicates value is already below threshold.")
        else:
            st.error("Slope is zero; cannot compute shelf-life.")
else:
    st.info("Upload a CSV or enter data manually to begin.")

st.markdown("---")
st.markdown("Built for Stability Analysis | Pharma Quality Tools")

