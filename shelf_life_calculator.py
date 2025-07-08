import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

st.set_page_config(layout="wide")
st.title("\U0001F4C8 Shelf-Life Calculator from Stability Data (ICH Based)")

st.markdown("### \U0001F4C2 Upload CSV File or Enter Data Manually")

uploaded_file = st.file_uploader(
    "Upload CSV with columns: Time, Condition, Parameter, Value",
    type=["csv"]
)
manual_input = st.checkbox("Or Enter Data Manually")

# Initialize empty DataFrame
data = pd.DataFrame(columns=["Time", "Condition", "Parameter", "Value"])
# Store spec limits for manual input entries keyed by (param, condition)
manual_spec_limits = {}

if uploaded_file is not None:
    try:
        data = pd.read_csv(uploaded_file)
        st.success("CSV loaded successfully.")
    except Exception as e:
        st.error(f"Error loading CSV: {e}")

elif manual_input:
    st.markdown("### \u270D\ufe0f Manual Input Table")
    with st.form("manual_form"):
        condition = st.selectbox("Stability Condition", ["25C_60RH", "30C_65RH", "40C_75RH"])
        param_name = st.text_input("Parameter Name (e.g., Assay)", "Assay")
        timepoints = st.text_area("Enter Time Points (comma-separated)", "0,1,3,6,9,12")
        values = st.text_area("Enter Values (comma-separated)", "100,98,95,92,90,88")
        spec_limit = st.number_input("Specification Limit for Shelf Life Calculation (cross limit lower or upper)", value=85.0, step=0.1)
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
                    # Save spec limit keyed by (param, condition)
                    manual_spec_limits[(param_name, condition)] = spec_limit
                    st.success("Data and specification limit added successfully.")
            except:
                st.error("Invalid format. Please enter numbers only.")

if not data.empty:
    st.markdown("### \U0001F441\ufe0f Data Preview")
    st.dataframe(data)

    def estimate_shelf_life_ich(x, refrigerated=False, stats=False, support_data=False):
        if stats and support_data:
            y = min(2 * x, x + 12) if not refrigerated else min(1.5 * x, x + 6)
        elif support_data:
            y = min(1.5 * x, x + 6) if not refrigerated else min(x + 3, x + 3)
        elif stats:
            y = min(1.5 * x, x + 6) if not refrigerated else min(x + 3, x + 3)
        else:
            y = x  # No extrapolation
        return y

    for (condition, param), df_group in data.groupby(["Condition", "Parameter"]):
        st.markdown(f"#### \U0001F4CA Regression for: {param} under {condition}")
        df = df_group.sort_values("Time")

        X = df["Time"].values.reshape(-1, 1)
        y = df["Value"].values

        model = LinearRegression()
        model.fit(X, y)
        pred = model.predict(X)
        slope = model.coef_[0]
        intercept = model.intercept_
        r2 = r2_score(y, pred)

        st.markdown("**\U0001F4CF Shelf-Life Estimation**")

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

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.scatter(X, y, label="Observed", color="blue")
        ax.plot(X, pred, label=f"Regression (R²={r2:.3f})", color="red")
        ax.axhline(y=threshold, color="green", linestyle="--", label=f"Spec Limit = {threshold}")
        ax.set_title(f"{param} vs Time ({condition})")
        ax.set_xlabel("Time (Months)")
        ax.set_ylabel("Value")
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)

        if slope != 0:
            est_time = (threshold - intercept) / slope
            if est_time > 0:
                st.success(f"Estimated shelf-life for {param} at {condition}: **{est_time:.2f} months**")

                st.markdown("**\U0001F4D8 ICH Evaluation**")
                support_data = st.checkbox(f"Backed by supporting data for {param} under {condition}?", key=f"support_{param}_{condition}")
                stats = r2 >= 0.95
                st.info(f"Statistical correlation (R²): {r2:.3f} {'✅' if stats else '❌'}")

                if df.shape[0] >= 3 and len(set(df["Time"])) >= 3:
                    st.success("✔ Meets ICH minimum 3 timepoints requirement.")
                else:
                    st.warning("✖ Not enough timepoints for ICH-based extrapolation.")

                is_refrigerated = condition.startswith("5") or "refrig" in condition.lower()
                ich_extrapolated = estimate_shelf_life_ich(est_time, refrigerated=is_refrigerated, stats=stats, support_data=support_data)

                st.info(f"📊 ICH-based extrapolated shelf-life: **{ich_extrapolated:.2f} months**")
            else:
                st.warning("Regression suggests value is already below the threshold.")
        else:
            st.error("Slope is zero; cannot compute shelf-life.")
else:
    st.info("Upload a CSV or enter data manually to begin.")

st.markdown("---")
st.markdown("Built for Stability Analysis | Pharma Quality Tools")

