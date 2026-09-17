import os
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from fastapi_app.core.storage import INVOICES_MEDIA_DIR, init_storage

def generate_invoice_pdf(
    user_name: str,
    plan_name: str,
    price: float,
    start_date: datetime,
    end_date: datetime,
    transaction_id: str,
    user_email: str = None
) -> str:
    """
    Generates a professional subscription invoice PDF using ReportLab.
    Saves the file in media/invoices/ and returns the relative URL path (/media/invoices/<filename>).
    """
    init_storage()

    safe_txn = transaction_id.replace(":", "_").replace("/", "_").replace("\\", "_")
    filename = f"invoice_{safe_txn}.pdf"
    file_path = INVOICES_MEDIA_DIR / filename

    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        name="InvoiceTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#1e293b")
    )
    
    brand_style = ParagraphStyle(
        name="InvoiceBrand",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#4338ca")
    )

    meta_label_style = ParagraphStyle(
        name="MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569")
    )

    meta_val_style = ParagraphStyle(
        name="MetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#0f172a")
    )

    table_header_style = ParagraphStyle(
        name="TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        name="TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1e293b")
    )

    footer_style = ParagraphStyle(
        name="InvoiceFooter",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=12,
        alignment=1, # Center
        textColor=colors.HexColor("#64748b")
    )

    elements = []

    # Header Row
    header_data = [
        [
            Paragraph("<b>BLOG MANAGEMENT SYSTEM</b><br/><font size=9 color='#64748b'>Premium Content & Creator Platform</font>", brand_style),
            Paragraph("<b>INVOICE</b><br/><font size=10 color='#16a34a'><b>STATUS: PAID</b></font>", title_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[4.0 * inch, 3.5 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=15))

    # Meta Details (Customer & Transaction)
    start_str = start_date.strftime("%B %d, %Y") if hasattr(start_date, 'strftime') else str(start_date)
    end_str = end_date.strftime("%B %d, %Y") if hasattr(end_date, 'strftime') else str(end_date)
    issue_str = datetime.now().strftime("%B %d, %Y")

    cust_info = f"""
    <b>Billed To:</b><br/>
    <b>Name:</b> {user_name}<br/>
    <b>Email:</b> {user_email or 'user@blogsystem.local'}<br/>
    <b>Customer Type:</b> Registered Creator
    """

    txn_info = f"""
    <b>Invoice Details:</b><br/>
    <b>Transaction ID:</b> {transaction_id}<br/>
    <b>Issue Date:</b> {issue_str}<br/>
    <b>Billing Period:</b> {start_str} to {end_str}
    """

    meta_data = [
        [Paragraph(cust_info, meta_val_style), Paragraph(txn_info, meta_val_style)]
    ]
    meta_table = Table(meta_data, colWidths=[3.75 * inch, 3.75 * inch])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 20))

    # Plan Items Table
    price_formatted = f"${price:.2f}" if price > 0 else "FREE ($0.00)"

    plan_desc = {
        "Basic": "Basic Access Plan (1 Post, 1 Image/Post, 5 Likes & Comments)",
        "Premium": "Premium Access Plan (2 Posts, 2 Images/Post, 20 Likes & Comments)",
        "Pro": "Pro Access Plan (Unlimited Posts, Images, Likes & Comments)"
    }.get(plan_name, f"{plan_name} Subscription Plan")

    items_data = [
        [
            Paragraph("<b>Plan / Description</b>", table_header_style),
            Paragraph("<b>Period</b>", table_header_style),
            Paragraph("<b>Qty</b>", table_header_style),
            Paragraph("<b>Total Amount</b>", table_header_style)
        ],
        [
            Paragraph(f"<b>{plan_name} Tier</b><br/><font size=8 color='#64748b'>{plan_desc}</font>", table_cell_style),
            Paragraph("30 Days", table_cell_style),
            Paragraph("1", table_cell_style),
            Paragraph(f"<b>{price_formatted}</b>", table_cell_style)
        ]
    ]

    items_table = Table(items_data, colWidths=[3.5 * inch, 1.5 * inch, 0.8 * inch, 1.7 * inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4338ca")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 15))

    # Summary Totals Table
    summary_data = [
        [Paragraph("<b>Subtotal:</b>", meta_label_style), Paragraph(price_formatted, meta_val_style)],
        [Paragraph("<b>Tax / VAT (0%):</b>", meta_label_style), Paragraph("$0.00", meta_val_style)],
        [Paragraph("<b>Total Paid:</b>", meta_label_style), Paragraph(f"<b>{price_formatted}</b>", meta_val_style)]
    ]
    summary_table = Table(summary_data, colWidths=[1.8 * inch, 1.7 * inch])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, -1), (-1, -1), 1.5, colors.HexColor("#4338ca")),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))

    wrapper_data = [
        [Paragraph("", meta_val_style), summary_table]
    ]
    wrapper_table = Table(wrapper_data, colWidths=[4.0 * inch, 3.5 * inch])
    wrapper_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT')
    ]))
    elements.append(wrapper_table)

    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=10))

    # Footer note
    footer_text = """
    Thank you for subscribing to Blog Management System!<br/>
    This is a computer-generated invoice for your records. For questions or billing support, please contact support@blogsystem.local.
    """
    elements.append(Paragraph(footer_text, footer_style))

    doc.build(elements)

    return f"/media/invoices/{filename}"
