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

    def estimate_shelf_life_ich(acc_stable: bool,
                                int_stable: bool,
                                long_term_behavior: str,
                                stats_done: bool,
                                long_term_months: int,
                                is_refrigerated: bool = False):
        if not acc_stable:
            return long_term_months  # No extrapolation

        if not int_stable:
            return long_term_months  # Intermediate condition fails

        if long_term_behavior == 'no_change':
            max_extrapolation = 12
        elif long_term_behavior == 'change_with_stats' and stats_done:
            max_extrapolation = 12
        else:
            max_extrapolation = 3

        if is_refrigerated:
            max_extrapolation = min(max_extrapolation, 6)

        return min(long_term_months + max_extrapolation, 2 * long_term_months)

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
                if r2 >= 0.95:
                    st.info("The regression model shows strong correlation (R² ≥ 0.95) as per ICH guidelines.")
                    stats_done = True
                else:
                    st.warning("The regression model shows weak correlation (R² < 0.95), may not meet ICH criteria.")
                    stats_done = False

                if df.shape[0] >= 3 and len(set(df["Time"])) >= 3:
                    st.success("Meets minimum ICH timepoint requirement for shelf-life estimation (≥3 distinct timepoints).")
                else:
                    st.warning("Less than 3 timepoints detected — not suitable for ICH shelf-life justification.")

                long_term_behavior = 'change_with_stats' if stats_done else 'change_no_stats'

                if condition.startswith("40"):
                    ich_shelf = estimate_shelf_life_ich(
                        acc_stable=True,
                        int_stable=True,
                        long_term_behavior=long_term_behavior,
                        stats_done=stats_done,
                        long_term_months=int(max(df["Time"])),
                        is_refrigerated=False
                    )
                    st.info(f"ICH-based extrapolated shelf-life: **{ich_shelf:.2f} months**")
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
