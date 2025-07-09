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

# Updated ICH Shelf-Life Estimation Logic (Full Decision Tree based)
def ich_shelf_life_estimation(
    x_months: float,
    no_sig_change_3m_acc: bool,
    no_sig_change_6m_acc: bool,
    sig_change_3m_acc: bool,
    sig_change_6m_acc: bool,
    sig_change_int: bool,
    stored_refrigerated: bool,
    stats_supported: bool,
    support_data_available: bool
) -> dict:
    result = {
        "Base (X)": x_months,
        "Proposed Shelf Life (Y)": x_months,
        "Decision": "No extrapolation",
        "Notes": ""
    }

    if sig_change_3m_acc or sig_change_6m_acc:
        if stored_refrigerated:
            result["Proposed Shelf Life (Y)"] = x_months + 3
            result["Decision"] = "Limited extrapolation for refrigerated product"
            result["Notes"] = "Significant change at accelerated; refrigerated allows +3M"
        elif sig_change_int:
            result["Proposed Shelf Life (Y)"] = x_months
            result["Decision"] = "No extrapolation"
            result["Notes"] = "Significant change at intermediate prevents extrapolation"
        else:
            if stats_supported and support_data_available:
                result["Proposed Shelf Life (Y)"] = min(x_months * 1.5, x_months + 6)
                result["Decision"] = "Extrapolation allowed with stats and support"
                result["Notes"] = "Statistical and support data allow extrapolation"
            elif stats_supported or support_data_available:
                result["Proposed Shelf Life (Y)"] = x_months + 3
                result["Decision"] = "Limited extrapolation with partial support"
                result["Notes"] = "Stats or support data allow +3M"
            else:
                result["Proposed Shelf Life (Y)"] = x_months
                result["Notes"] = "No extrapolation allowed"
    else:
        # No significant change at 3M or 6M Accelerated
        if sig_change_int:
            result["Proposed Shelf Life (Y)"] = x_months
            result["Decision"] = "No extrapolation"
            result["Notes"] = "Intermediate change prevents extrapolation"
        else:
            if stats_supported and support_data_available:
                result["Proposed Shelf Life (Y)"] = min(x_months * 2, x_months + 12)
                result["Decision"] = "Max extrapolation with full support"
                result["Notes"] = "Statistical and supporting data support +12M"
            elif stats_supported or support_data_available:
                result["Proposed Shelf Life (Y)"] = min(x_months * 1.5, x_months + 6)
                result["Decision"] = "Partial extrapolation"
                result["Notes"] = "Partial support or stats allows +6M"
            else:
                result["Proposed Shelf Life (Y)"] = x_months + 3
                result["Decision"] = "Minimal extrapolation"
                result["Notes"] = "No significant change but minimal support => +3M"

    return result

# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("📈 ICH Shelf-Life Estimation App (Fully Aligned with Appendix A)")

st.markdown("### 🧪 Stability Study Observations")
no_sig_3m = st.checkbox("✅ No Significant Change at 3M Accelerated", value=True)
no_sig_6m = st.checkbox("✅ No Significant Change at 6M Accelerated", value=True)
sig_3m = st.checkbox("⚠️ Significant Change at 3M Accelerated", value=False)
sig_6m = st.checkbox("⚠️ Significant Change at 6M Accelerated", value=False)
sig_int = st.checkbox("⚠️ Significant Change at Intermediate (6M, 30°C)", value=False)
refrig = st.checkbox("❄️ Stored Refrigerated", value=False)
support = st.checkbox("📄 Supporting Data Available", value=False)

st.markdown("### 🧮 Manual Input Data for 25°C/60%RH")
param = st.text_input("Parameter Name", "Assay")
spec_limit = st.number_input("Specification Limit", value=85.0)
failure_direction = st.radio("Does parameter fail by:", ["Decreasing", "Increasing"])

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
        st.error("At least 3 valid time points are required.")
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

        if slope != 0:
            est_shelf_life = (spec_limit - intercept) / slope
            if est_shelf_life > 0:
                st.success(f"Estimated Shelf-Life: {est_shelf_life:.2f} months")
            else:
                st.warning("Regression line already below spec.")
        else:
            est_shelf_life = None
            st.warning("Slope is zero. Shelf-life undetermined.")

        x_base = max([t for t, v in zip(time_values, value_inputs) if (v >= spec_limit if failure_direction == "Decreasing" else v <= spec_limit)], default=0)
        stats_ok = r2 >= 0.95

        ich_result = ich_shelf_life_estimation(
            x_months=x_base,
            no_sig_change_3m_acc=no_sig_3m,
            no_sig_change_6m_acc=no_sig_6m,
            sig_change_3m_acc=sig_3m,
            sig_change_6m_acc=sig_6m,
            sig_change_int=sig_int,
            stored_refrigerated=refrig,
            stats_supported=stats_ok,
            support_data_available=support
        )
        ich_result["Regression Shelf Life (Y)"] = round(est_shelf_life, 2) if est_shelf_life else "N/A"

        st.subheader("📋 ICH Decision Summary")
        for k, v in ich_result.items():
            st.write(f"**{k}**: {v}")

        st.markdown("### 📦 Product Metadata")
        pname = st.text_input("Product Name", "Sample Product")
        bnum = st.text_input("Batch Number", "BN001")
        bsize = st.text_input("Batch Size", "10,000 Tablets")
        ppack = st.text_input("Packaging", "Alu-Alu")

        if st.button("📄 Generate PDF Report"):
            try:
                pdf_output = io.BytesIO()
                doc = SimpleDocTemplate(pdf_output, pagesize=A4)
                styles = getSampleStyleSheet()
                story = [
                    Paragraph("ICH Stability Shelf-Life Report", styles['Title']),
                    Spacer(1, 12),
                    Paragraph(f"<b>Product:</b> {pname}", styles['Normal']),
                    Paragraph(f"<b>Batch No:</b> {bnum}", styles['Normal']),
                    Paragraph(f"<b>Batch Size:</b> {bsize}", styles['Normal']),
                    Paragraph(f"<b>Packaging:</b> {ppack}", styles['Normal']),
                    Spacer(1, 12),
                    Paragraph("ICH Logic Summary", styles['Heading2'])
                ]

                table_data = [["Key", "Value"]] + [[k, str(v)] for k, v in ich_result.items()] + [["R²", f"{r2:.2f}"]]
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

