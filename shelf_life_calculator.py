import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as PDFImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

def ich_shelf_life_decision(
    x_months: float,
    sig_change_3m_accel: bool,
    sig_change_6m_accel: bool,
    sig_change_intermediate: bool,
    no_change_accel: bool,
    no_change_intermediate: bool,
    data_trend_low_variability: bool,
    long_term_stats_amenable: bool,
    stats_performed: bool,
    supporting_data_available: bool,
    stored_refrigerated: bool,
    stored_frozen: bool
) -> dict:

    result = {
        "Base (X)": x_months,
        "Proposed Shelf Life (Y)": x_months,
        "Decision": "No extrapolation",
        "Notes": ""
    }

    if stored_frozen:
        result["Decision"] = "No extrapolation - freezer storage"
        result["Notes"] = "Use long-term data only"
        return result

    # Extended logic for significant changes
    if sig_change_6m_accel:
        if sig_change_3m_accel:
            result["Decision"] = "No extrapolation"
            result["Notes"] = "Shorter retest period or shelf life may be needed; include data for excursions; statistical analysis if long-term shows variability"
            return result
        elif not stored_refrigerated and sig_change_intermediate:
            result["Decision"] = "No extrapolation"
            result["Notes"] = "Shorter retest period or shelf life may be needed; statistical analysis if long-term data show variability"
            return result
        elif not stored_refrigerated and not sig_change_intermediate:
            if not long_term_stats_amenable:
                if supporting_data_available:
                    result["Proposed Shelf Life (Y)"] = x_months + 3
                    result["Decision"] = "Up to +3 M"
                    result["Notes"] = "Based on relevant supporting data"
                else:
                    result["Decision"] = "No extrapolation"
                    result["Notes"] = "Insufficient statistical and supporting data"
                return result
            elif long_term_stats_amenable and stats_performed and supporting_data_available:
                result["Proposed Shelf Life (Y)"] = min(x_months * 1.5, x_months + 6)
                result["Decision"] = "Up to 1.5x (max +6 M)"
                result["Notes"] = "Backed by statistical analysis and supporting data"
                return result

    # New logic for no significant change at accelerated and low variability
    if not sig_change_6m_accel and long_term_stats_amenable:
        if data_trend_low_variability and no_change_accel:
            if stored_refrigerated:
                result["Proposed Shelf Life (Y)"] = min(x_months * 1.5, x_months + 6)
                result["Decision"] = "Up to 1.5x (max +6 M)"
                result["Notes"] = "Low variability; statistical analysis unnecessary"
            else:
                result["Proposed Shelf Life (Y)"] = min(x_months * 2, x_months + 12)
                result["Decision"] = "Up to 2x (max +12 M)"
                result["Notes"] = "Low variability; statistical analysis unnecessary"
            return result
        elif not data_trend_low_variability:
            if long_term_stats_amenable and stats_performed and supporting_data_available:
                if stored_refrigerated:
                    result["Proposed Shelf Life (Y)"] = min(x_months * 1.5, x_months + 6)
                    result["Decision"] = "Up to 1.5x (max +6 M)"
                else:
                    result["Proposed Shelf Life (Y)"] = min(x_months * 2, x_months + 12)
                    result["Decision"] = "Up to 2x (max +12 M)"
                result["Notes"] = "Statistical analysis and supporting data available"
                return result
            elif supporting_data_available:
                if stored_refrigerated:
                    result["Proposed Shelf Life (Y)"] = x_months + 3
                    result["Decision"] = "Up to +3 M"
                else:
                    result["Proposed Shelf Life (Y)"] = min(x_months * 1.5, x_months + 6)
                    result["Decision"] = "Up to 1.5x (max +6 M)"
                result["Notes"] = "Supported by relevant data despite lack of statistical analysis"
                return result

    return result

# --- Streamlit UI Integration ---
st.set_page_config(layout="wide")
st.title("📈 ICH Shelf-Life Estimation App")

st.markdown("### 🧪 Observations")
sig_3m = st.checkbox("⚠️ Significant Change at 3M Accelerated", value=False)
sig_6m = st.checkbox("⚠️ Significant Change at 6M Accelerated", value=False)
no_int = st.checkbox("No Change at Intermediate", value=False)
sig_int = st.checkbox("⚠️ Significant Change at Intermediate (30°C, 6M)", value=False)
refrig = st.checkbox("❄️ Stored Refrigerated", value=False)
frozen = st.checkbox("❄️ Stored Frozen", value=False)
support = st.checkbox("📄 Supporting Data Available", value=False)
stats_performed = st.checkbox("📊 Stats Performed with R² ≥ 0.95", value=False)
low_variability = st.checkbox("📉 Low Variability Trend", value=False)
long_term_stats_amenable = st.checkbox("📈 Long-Term Trend Amenable to Stats", value=False)

st.markdown("### 🧮 Stability Data Entry")
spec_limit = st.number_input("Specification Limit", value=85.0)
failure_dir = st.radio("Parameter fails by:", ["Decreasing", "Increasing"])

month_labels = ["0M", "1M", "3M", "6M", "9M", "12M", "18M", "24M", "36M", "48M"]
month_times = [0, 1, 3, 6, 9, 12, 18, 24, 36, 48]
time_values, value_inputs = [], []
for i, label in enumerate(month_labels):
    val = st.number_input(f"{label} Value", value=0.0, step=0.1, key=f"month_{i}")
    if val > 0:
        time_values.append(month_times[i])
        value_inputs.append(val)

if st.button("📊 Calculate Shelf-Life"):
    if len(time_values) < 3:
        st.error("At least 3 valid time points required.")
    else:
        df = pd.DataFrame({"Time": time_values, "Value": value_inputs})
        X = df["Time"].values.reshape(-1, 1)
        y = df["Value"].values
        model = LinearRegression().fit(X, y)
        slope = model.coef_[0]
        intercept = model.intercept_
        r2 = r2_score(y, model.predict(X))

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.scatter(X, y, color='blue')
        ax.plot(X, model.predict(X), color='red', label=f'R²={r2:.2f}')
        ax.axhline(y=spec_limit, color='green', linestyle='--')
        ax.set_title("Regression Analysis")
        ax.legend()
        st.pyplot(fig)

        est_shelf_life = (spec_limit - intercept) / slope if slope != 0 else None
        if est_shelf_life and est_shelf_life > 0:
            st.success(f"Estimated Shelf-Life: {est_shelf_life:.2f} months")
        else:
            st.warning("Regression below spec or slope is zero.")

        x_base = max([t for t, v in zip(time_values, value_inputs) if (v >= spec_limit if failure_dir == "Decreasing" else v <= spec_limit)], default=0)

        ich_result = ich_shelf_life_decision(
            x_months=x_base,
            sig_change_3m_accel=sig_3m,
            sig_change_6m_accel=sig_6m,
            sig_change_intermediate=sig_int,
            no_change_accel=not (sig_3m or sig_6m),
            no_change_intermediate=no_int,
            data_trend_low_variability=low_variability,
            long_term_stats_amenable=long_term_stats_amenable,
            stats_performed=(r2 >= 0.95 if stats_performed else False),
            supporting_data_available=support,
            stored_refrigerated=refrig,
            stored_frozen=frozen
        )

        ich_result["Regression Shelf Life (Y)"] = round(est_shelf_life, 2) if est_shelf_life else "N/A"
        ich_result["R²"] = f"{r2:.2f}"

        st.subheader("📋 ICH Decision Summary")
        for k, v in ich_result.items():
            st.write(f"**{k}**: {v}")

        if st.button("📄 Generate PDF Report"):
            try:
                pdf_output = io.BytesIO()
                doc = SimpleDocTemplate(pdf_output, pagesize=A4)
                styles = getSampleStyleSheet()
                story = [
                    Paragraph("ICH Stability Shelf-Life Report", styles['Title']),
                    Spacer(1, 12),
                    Paragraph("ICH Logic Summary", styles['Heading2'])
                ]

                table_data = [["Key", "Value"]] + [[k, str(v)] for k, v in ich_result.items()]
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ]))
                story.append(table)
                story.append(Spacer(1, 12))

                fig_buf = io.BytesIO()
                canvas = FigureCanvas(fig)
                canvas.print_png(fig_buf)
                fig_buf.seek(0)
                story.append(Paragraph("Regression Plot", styles['Heading2']))
                story.append(PDFImage(fig_buf, width=6 * inch, height=3 * inch))

                doc.build(story)
                pdf_output.seek(0)

                st.download_button(
                    label="📄 Download ICH Shelf-Life Report (PDF)",
                    data=pdf_output,
                    file_name="ICH_Shelf_Life_Report.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"PDF generation failed: {str(e)}")


