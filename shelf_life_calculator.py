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

# Initialize session state defaults
if "ich_result" not in st.session_state:
    st.session_state["ich_result"] = {}

# Product Info
st.sidebar.markdown("### ✏️ Product Information")
product_name = st.sidebar.text_input("Product Name", "Sample Drug")
batch_number = st.sidebar.text_input("Batch Number", "B12345")
batch_size = st.sidebar.text_input("Batch Size", "10000 tablets")
packaging_mode = st.sidebar.text_input("Packaging Mode", "HDPE Bottle")

def determine_shelf_life(
    stored_frozen: bool,
    sig_change_6m_accel: bool,
    sig_change_3m_accel: bool,
    stored_refrigerated: bool,
    sig_change_intermediate: bool,
    long_term_stats_amenable: bool,
    stats_performed: bool,
    supporting_data_available: bool,
    data_trend_low_variability: bool,
    no_change_accel: bool,
    x_months: int
):
    result = {}

    if stored_frozen:
        result["Decision"] = "No extrapolation - freezer storage"
        result["Notes"] = "Use long-term data only"
        return result

    if sig_change_6m_accel:
        if sig_change_3m_accel:
            result["Decision"] = "No extrapolation"
            result["Notes"] = ("Shorter retest period or shelf life may be needed; include data for excursions; "
                                "statistical analysis if long-term shows variability")
            return result

        elif not stored_refrigerated and sig_change_intermediate:
            result["Decision"] = "No extrapolation"
            result["Notes"] = ("Shorter retest period or shelf life may be needed; statistical analysis if long-term data "
                                "show variability")
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

# Streamlit UI
st.set_page_config(layout="wide")
st.title("\U0001F4C8 ICH Shelf-Life Extrapolation Tool")

stored_frozen = st.checkbox("\u2744\ufe0f Stored Frozen")
sig_change_6m_accel = st.checkbox("\u26a0\ufe0f Significant Change at 6M Accelerated")
sig_change_3m_accel = st.checkbox("\u26a0\ufe0f Significant Change at 3M Accelerated")
stored_refrigerated = st.checkbox("\u2744\ufe0f Stored Refrigerated")
sig_change_intermediate = st.checkbox("\u26a0\ufe0f Significant Change at Intermediate")
long_term_stats_amenable = st.checkbox("\U0001F4C8 Long-term Stats Amenable")
stats_performed = st.checkbox("\U0001F4CA Stats Performed")
supporting_data_available = st.checkbox("\U0001F4C4 Supporting Data Available")
data_trend_low_variability = st.checkbox("\U0001F4C9 Data Trend Low Variability")
no_change_accel = st.checkbox("No Change in Accelerated")

x_months = st.number_input("Initial Shelf Life (months)", min_value=1, step=1)

st.markdown("### \U0001F9EE Stability Data Entry")
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

if st.button("\U0001F4CA Calculate Shelf-Life"):
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
        x_base = max([t for t, v in zip(time_values, value_inputs) if (v >= spec_limit if failure_dir == "Decreasing" else v <= spec_limit)], default=0)


if st.button("\U0001F4CA Evaluate Shelf Life"):
    result = determine_shelf_life(
        stored_frozen,
        sig_change_6m_accel,
        sig_change_3m_accel,
        stored_refrigerated,
        sig_change_intermediate,
        long_term_stats_amenable,
        stats_performed,
        supporting_data_available,
        data_trend_low_variability,
        no_change_accel,
        x_months
    )

    result["Product Name"] = product_name
    result["Batch Number"] = batch_number
    result["Batch Size"] = batch_size
    result["Packaging Mode"] = packaging_mode

    st.session_state["ich_result"] = result

    st.subheader("\U0001F4CB ICH Decision Summary")
    for k, v in result.items():
        st.write(f"**{k}**: {v}")



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
