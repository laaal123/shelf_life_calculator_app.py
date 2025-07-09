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

# ICH shelf life logic function with "no_sig_change_acc" param
def ich_shelf_life_estimation(
    x_months: float,
    no_sig_change_acc: bool,
    sig_change_acc: bool,
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

    if sig_change_acc:
        # Significant change at accelerated condition
        if stored_refrigerated:
            result["Proposed Shelf Life (Y)"] = x_months + 3
            result["Decision"] = "Limited extrapolation for refrigerated product"
            result["Notes"] = "Significant change at accelerated; refrigerated storage allows +3M"
        elif sig_change_int:
            result["Proposed Shelf Life (Y)"] = x_months
            result["Decision"] = "No extrapolation"
            result["Notes"] = "Significant change at intermediate prevents extrapolation"
        else:
            if stats_supported or support_data_available:
                result["Proposed Shelf Life (Y)"] = x_months + 3
                result["Decision"] = "Extrapolation allowed with support"
                result["Notes"] = "Support data or R2 allows +3M"
            else:
                result["Proposed Shelf Life (Y)"] = x_months
                result["Notes"] = "Insufficient statistical support"
    else:
        # No significant change at accelerated
        if sig_change_int:
            result["Proposed Shelf Life (Y)"] = x_months
            result["Decision"] = "No extrapolation"
            result["Notes"] = "Significant change at intermediate prevents extrapolation"
        else:
            # No significant changes at accelerated or intermediate
            if stats_supported and support_data_available and no_sig_change_acc:
                # Full support & no sig change at accelerated: +12 months allowed (Appendix A)
                result["Proposed Shelf Life (Y)"] = x_months + 12
                result["Decision"] = "Max extrapolation with full support (Appendix A)"
                result["Notes"] = "Full statistical and supporting data allows +12M extrapolation"
            elif stats_supported or support_data_available:
                # Partial support: +6 months
                result["Proposed Shelf Life (Y)"] = x_months + 6
                result["Decision"] = "Partial extrapolation with support"
                result["Notes"] = "Partial support allows +6M extrapolation"
            else:
                # Minimal support: +3 months
                result["Proposed Shelf Life (Y)"] = x_months + 3
                result["Decision"] = "Limited extrapolation with minimal support"
                result["Notes"] = "Minimal support allows +3M extrapolation"

    return result

# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("📈 Manual Shelf-Life Estimation & ICH Decision")

# --- All inputs shown immediately ---
st.markdown("### 🧪 Pre-Input ICH Extrapolation Conditions")
no_sig_acc = st.checkbox("No significant change at 3M Accelerated?", value=True)
sig_acc = st.checkbox("Significant change at 3M Accelerated?", value=False)
sig_int = st.checkbox("Significant change at 6M Intermediate?", value=False)
refrig = st.checkbox("Stored refrigerated?", value=False)
support = st.checkbox("Supporting data available?", value=False)

st.markdown("### ✍️ Input Manual Data (25°C/60%RH)")
param = st.text_input("Parameter Name", "Assay")
spec_limit = st.number_input("Specification Limit", value=85.0)
failure_direction = st.radio("Does the parameter fail by increasing or decreasing?", ["Decreasing", "Increasing"])

month_labels = ["0M", "1M", "3M", "6M", "9M", "12M", "18M", "24M", "36M", "48M"]
month_times = [0, 1, 3, 6, 9, 12, 18, 24, 36, 48]
time_values = []
value_inputs = []

for i, label in enumerate(month_labels):
    val = st.number_input(f"{label} Value", value=0.0, step=0.1, key=f"month_{i}")
    if val > 0:
        time_values.append(month_times[i])
        value_inputs.append(val)

st.markdown("### 📦 Product Information for Report")
product_name = st.text_input("Product Name", "Example Product")
batch_number = st.text_input("Batch Number", "BN-001")
batch_size = st.text_input("Batch Size", "10000 Tablets")
packaging_mode = st.text_input("Packaging Mode", "Blister Pack")

# --- Calculation and result display ---
if st.button("📊 Calculate Shelf-Life"):
    if len(time_values) < 3:
        st.error("At least 3 valid time points are required for regression.")
    else:
        df = pd.DataFrame({"Time": time_values, "Value": value_inputs})
        X = df["Time"].values.reshape(-1, 1)
        y = df["Value"].values
        model = LinearRegression()
        model.fit(X, y)
        pred = model.predict(X)
        slope = model.coef_[0]
        intercept = model.intercept_
        r2 = r2_score(y, pred)

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
            if est_shelf_life > 0:
                st.success(f"Estimated Shelf-Life: {est_shelf_life:.2f} months")
            else:
                st.warning("Regression indicates spec limit already breached.")
        else:
            est_shelf_life = None
            st.warning("Cannot calculate shelf-life: slope is zero.")

        st.markdown("### 🧮 ICH Logic Result")

        if failure_direction == "Decreasing":
            passing_times = [t for t, v in zip(time_values, value_inputs) if v >= spec_limit]
        else:
            passing_times = [t for t, v in zip(time_values, value_inputs) if v <= spec_limit]

        x_base = max(passing_times) if passing_times else 0
        stats = r2 >= 0.95

        ich_result = ich_shelf_life_estimation(
            x_months=x_base,
            no_sig_change_acc=no_sig_acc,
            sig_change_acc=sig_acc,
            sig_change_int=sig_int,
            stored_refrigerated=refrig,
            stats_supported=stats,
            support_data_available=support
        )
        ich_result["Regression Shelf Life (Y)"] = round(est_shelf_life, 2) if est_shelf_life else "N/A"

        for k, v in ich_result.items():
            st.write(f"**{k}**: {v}")

        # Store fig and results in session state to allow PDF generation later
        st.session_state["last_fig"] = fig
        st.session_state["ich_result"] = ich_result
        st.session_state["r2"] = r2
        st.session_state["est_shelf_life"] = est_shelf_life

# --- PDF generation ---
if st.button("📄 Generate and Download PDF Report"):
    try:
        if "last_fig" not in st.session_state or "ich_result" not in st.session_state:
            st.error("Please run the shelf-life calculation first.")
        else:
            pdf_output = io.BytesIO()
            doc = SimpleDocTemplate(pdf_output, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []

            story.append(Paragraph("Stability Study Report", styles['Title']))
            story.append(Spacer(1, 12))
            story.append(Paragraph(f"<b>Product Name:</b> {product_name}", styles['Normal']))
            story.append(Paragraph(f"<b>Batch Number:</b> {batch_number}", styles['Normal']))
            story.append(Paragraph(f"<b>Batch Size:</b> {batch_size}", styles['Normal']))
            story.append(Paragraph(f"<b>Packaging Mode:</b> {packaging_mode}", styles['Normal']))
            story.append(Spacer(1, 12))

            story.append(Paragraph(f"<b>ICH Shelf-Life Estimation Summary:</b>", styles['Heading2']))
            shelf_life_table_data = [["Key", "Value"]] + [[k, str(v)] for k, v in st.session_state["ich_result"].items()]
            shelf_life_table_data.append(["R²", f"{st.session_state['r2']:.2f}"])
            if st.session_state["est_shelf_life"]:
                shelf_life_table_data.append(["Estimated Shelf Life", f"{st.session_state['est_shelf_life']:.2f} months"])

            table = Table(shelf_life_table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ]))
            story.append(table)
            story.append(Spacer(1, 12))

            fig_buf = io.BytesIO()
            canvas = FigureCanvas(st.session_state["last_fig"])
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

st.markdown("---")
st.markdown("Built for Pharma Quality Tools | ICH Stability Logic")


