from fpdf import FPDF
from datetime import datetime
import os

def clean_text(text):
    """Removes characters the PDF font can't display, keeps things safe."""
    text = str(text)
    return text.encode("latin-1", "replace").decode("latin-1")

def generate_medicine_summary_pdf(df, output_path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    usable_width = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_x(pdf.l_margin)
    pdf.cell(usable_width, 10, "Medicine Summary Sheet", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_x(pdf.l_margin)
    pdf.cell(usable_width, 8, f"Generated on: {datetime.now().strftime('%d %B %Y')}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(usable_width, 5, clean_text("This is a personal organization summary, not medical advice. Always confirm details with your doctor or pharmacist."))
    pdf.ln(4)

    for _, row in df.iterrows():
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(usable_width, 7, clean_text(f"{row['medicine_name']}  ({row['time_of_day']})"))

        pdf.set_x(pdf.l_margin)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(usable_width, 6, clean_text(f"Instruction: {row['user_provided_instruction']}"))

        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(usable_width, 6, clean_text(f"Start date: {row['start_date']}   |   Refill date: {row['refill_date']}"))

        if str(row['notes']).strip() and str(row['notes']) != "nan":
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(usable_width, 6, clean_text(f"Notes: {row['notes']}"))

        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(usable_width, 6, clean_text(f"Doctor/Pharmacist: {row['doctor_pharmacist_contact']}"))
        pdf.ln(4)

    pdf.output(output_path)
    return output_path