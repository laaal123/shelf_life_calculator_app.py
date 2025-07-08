Link: https://shelflifecalculatorapppy-murlxrmbnpu36bqfsktskr.streamlit.app/

🔍 1. Input Stability Data
You can input data in two ways:

📂 Upload CSV File with columns:

Time (months)

Condition (e.g., 25C_60RH)

Parameter (e.g., Assay, Dissolution)

Value (e.g., 98.5)

✍️ Enter Data Manually by selecting condition, entering parameter, timepoints, and values.

📊 2. Visualize and Analyze
For each condition and parameter:

Plots regression chart (trend line) of parameter vs. time

Computes:

Regression equation

R² (coefficient of determination) – indicates trend fit

Shows visual trends for assay loss, impurity growth, etc.

📏 3. Estimate Shelf-Life
You input the specification limit (e.g., 85%)

App calculates the estimated shelf-life using regression:

shelf-life
=
Spec Limit
−
Intercept
Slope
shelf-life= 
Slope
Spec Limit−Intercept
​
 
📘 4. ICH-Based Interpretation
Based on ICH Q1E Guidelines, the app:

Checks if ≥3 timepoints exist (required by ICH)

Assesses R² ≥ 0.95 (indicates a reliable model)

Flags accelerated conditions (40C_75RH) and applies extrapolation rules

For long-term (25C_60RH, 30C_65RH), uses direct estimation

Informs whether the conditions/data qualify for shelf-life justification

✅ Use Cases
Estimate expiry/retest period for drug products

Determine if accelerated studies support extrapolation

Support regulatory submissions with statistical evidence

Help formulation or QA teams make data-driven shelf-life decisions
