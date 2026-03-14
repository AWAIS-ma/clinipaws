"""
Utility functions for generating bilingual (English + Urdu) PDF reports.

Urdu rendering pipeline:
  1. arabic_reshaper  - reshapes individual Arabic/Urdu characters into
                        their contextual (initial/medial/final/isolated) forms.
  2. python-bidi      - applies the Unicode Bidi Algorithm so right-to-left
                        text is stored in visual (display) order.
  3. NotoNastaliqUrdu - an embedded TTF font that contains the Nastaliq glyphs.

Without steps 1-2 the glyphs appear as isolated marks scattered left-to-right.
"""
import os
import re
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---------------------------------------------------------------------------
# Optional bidi / reshaping libraries
# ---------------------------------------------------------------------------
try:
    import arabic_reshaper
    from bidi.algorithm import get_display as bidi_display
    _BIDI_AVAILABLE = True
except ImportError:
    _BIDI_AVAILABLE = False


# ---------------------------------------------------------------------------
# Font registration
# ---------------------------------------------------------------------------
_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
_URDU_FONT_PATH = os.path.join(_FONT_DIR, "NotoNaskhArabic-Regular.ttf")
_URDU_FONT_NAME = "NotoNaskhArabic"

_font_registered = False


def _ensure_urdu_font() -> bool:
    """Register the Urdu TTF font with ReportLab (idempotent). Returns True on success."""
    global _font_registered
    if _font_registered:
        return True
    if os.path.exists(_URDU_FONT_PATH):
        try:
            pdfmetrics.registerFont(TTFont(_URDU_FONT_NAME, _URDU_FONT_PATH))
            _font_registered = True
            return True
        except Exception:
            pass
    return False


# ---------------------------------------------------------------------------
# Urdu text pre-processing
# ---------------------------------------------------------------------------

def _has_arabic_script(text: str) -> bool:
    """Return True if *text* contains any Arabic/Urdu Unicode codepoints."""
    for ch in text:
        cp = ord(ch)
        # Arabic block U+0600-U+06FF, Arabic Presentation Forms U+FB50-U+FDFF, U+FE70-U+FEFF
        if 0x0600 <= cp <= 0x06FF or 0xFB50 <= cp <= 0xFDFF or 0xFE70 <= cp <= 0xFEFF:
            return True
    return False


# Initialize specific Urdu reshaper
_ar_reshaper = None
if _BIDI_AVAILABLE:
    _ar_reshaper = arabic_reshaper.ArabicReshaper(
        configuration={
            'language': 'Urdu'
        }
    )

def _reshape_urdu(text: str) -> str:
    """
    Apply Arabic reshaping + RTL bidi reordering to *text*.

    Works on the entire string (mixed English/Urdu).  English runs are left
    untouched by arabic_reshaper; bidi_display reverses only the RTL portions.
    """
    if not _BIDI_AVAILABLE or not _has_arabic_script(text):
        return text
    reshaped = _ar_reshaper.reshape(text)
    return bidi_display(reshaped)


# ---------------------------------------------------------------------------
# HTML / Markdown helpers
# ---------------------------------------------------------------------------

def _md_to_html(text: str) -> str:
    """
    Convert lightweight Markdown to ReportLab-compatible XML/HTML:
      **bold**  →  <b>bold</b>
      newlines  →  <br/>

    Preserves all content (English and Urdu).
    """
    if not text:
        return ""
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = text.replace("\n", "<br/>")
    return text


def _preprocess_line(line: str) -> str:
    """
    Reshape a single plain-text line that may contain Urdu and wrap Urdu in font tags.
    """
    if not _BIDI_AVAILABLE:
        return line
        
    # Pattern to match Urdu/Arabic words and spaces between them
    # \u0600-\u06FF is Arabic block, \u0750-\u077F is Arabic Supplement
    # \uFB50-\uFDFF is Presentation Forms A, \uFE70-\uFEFF is Presentation Forms B
    pattern = re.compile(r'([\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF\s]+)')
    
    parts = pattern.split(line)
    result = []
    
    for part in parts:
        if not part:
            continue
        if re.search(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]', part):
            reshaped = _ar_reshaper.reshape(part)
            bidi_text = bidi_display(reshaped)
            result.append(f'<font name="{_URDU_FONT_NAME}">{bidi_text}</font>')
        else:
            result.append(part)
            
    return "".join(result)


def _preprocess_html(html: str) -> str:
    """
    Reshape Urdu inside an HTML-tagged string produced by _md_to_html.
    Wraps Urdu sections in font tags so mixed English/Urdu works properly.
    """
    if not _BIDI_AVAILABLE:
        return html
    parts = re.split(r"(<[^>]+>)", html)
    result = []
    
    # Same pattern for Urdu text
    pattern = re.compile(r'([\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF\s]+)')
    
    for part in parts:
        if part.startswith("<"):
            result.append(part)          # keep tags verbatim
        else:
            # Process the text segment
            subparts = pattern.split(part)
            for subpart in subparts:
                if not subpart:
                    continue
                if re.search(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]', subpart):
                    reshaped = _ar_reshaper.reshape(subpart)
                    bidi_text = bidi_display(reshaped)
                    result.append(f'<font name="{_URDU_FONT_NAME}">{bidi_text}</font>')
                else:
                    result.append(subpart)
                    
    return "".join(result)


def _safe_paragraph(html: str, style) -> Paragraph:
    """
    Build a Paragraph from an HTML string.  Falls back to plain text if
    ReportLab's XML parser cannot handle the content.
    """
    try:
        return Paragraph(html, style)
    except Exception:
        plain = re.sub(r"<[^>]+>", "", html)
        try:
            return Paragraph(plain, style)
        except Exception:
            return Paragraph("(Content could not be rendered)", style)


# ---------------------------------------------------------------------------
# Style factories
# ---------------------------------------------------------------------------

def _build_styles() -> dict:
    """
    Return a dict of ParagraphStyle objects.
    We use Helvetica as the base for English and use inline tags for Urdu.
    """
    _ensure_urdu_font()
    
    font = "Helvetica"
    bold_font = "Helvetica-Bold"

    base = getSampleStyleSheet()

    return dict(
        title=ParagraphStyle(
            "CustomTitle",
            parent=base["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#0066cc"),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=bold_font,
        ),
        heading=ParagraphStyle(
            "CustomHeading",
            parent=base["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#333333"),
            spaceAfter=12,
            spaceBefore=12,
            fontName=bold_font,
        ),
        sub_heading=ParagraphStyle(
            "CustomSubHeading",
            parent=base["Heading3"],
            fontSize=13,
            alignment=TA_CENTER,
            fontName=font,
        ),
        normal=ParagraphStyle(
            "CustomNormal",
            parent=base["Normal"],
            fontSize=11,
            spaceAfter=12,
            leading=18,
            alignment=TA_JUSTIFY,
            fontName="Helvetica",  # Default to Helvetica, inline tags will handle Urdu
        ),
        footer=ParagraphStyle(
            "Footer",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_CENTER,
            fontName="Helvetica",
        ),
        urdu_font=font,
        urdu_font_bold=bold_font,
    )


# ---------------------------------------------------------------------------
# Table style helpers
# ---------------------------------------------------------------------------

def _info_table_style(font: str, bold_font: str) -> TableStyle:
    return TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
        ("TEXTCOLOR",     (0, 0), (-1, -1), colors.black),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME",      (0, 0), (0, -1), bold_font),
        ("FONTNAME",      (1, 0), (1, -1), font),
        ("FONTSIZE",      (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.grey),
    ])


def _symptoms_table_style(font: str, bold_font: str) -> TableStyle:
    return TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), colors.HexColor("#e8f4f8")),
        ("TEXTCOLOR",     (0, 0), (-1, -1), colors.black),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME",      (0, 0), (0, -1), bold_font),
        ("FONTNAME",      (1, 0), (1, -1), font),
        ("FONTSIZE",      (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.grey),
    ])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_symptom_report_pdf(report):
    """
    Generate a bilingual (English + Urdu) PDF for a symptom-based report.

    Args:
        report: Report model instance

    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.5 * inch, bottomMargin=0.5 * inch,
    )
    story = []
    st = _build_styles()
    font = st["urdu_font"]
    bold_font = st["urdu_font_bold"]

    # ---- Title ----------------------------------------------------------
    story.append(Paragraph("Livestock Disease Prediction Report", st["title"]))
    story.append(Paragraph("Symptom-Based Analysis", st["sub_heading"]))
    story.append(Spacer(1, 0.3 * inch))

    # ---- Report info table ----------------------------------------------
    report_table = Table(
        [
            ["Report ID:",     f"#{report.id}"],
            ["Animal Type:",   report.get_animal_display()],
            ["Date Generated:", report.created_at.strftime("%B %d, %Y at %I:%M %p")],
            ["Created By:",    report.created_by.username],
        ],
        colWidths=[2 * inch, 4 * inch],
    )
    report_table.setStyle(_info_table_style(font, bold_font))
    story.append(report_table)
    story.append(Spacer(1, 0.3 * inch))

    # ---- Predicted disease ----------------------------------------------
    story.append(Paragraph("Predicted Disease", st["heading"]))
    disease_html = (
        f"<b><font size='14' color='#cc0000'>"
        f"{report.predicted_disease}</font></b>"
    )
    story.append(_safe_paragraph(disease_html, st["normal"]))
    story.append(Spacer(1, 0.2 * inch))

    # ---- Observed symptoms table ----------------------------------------
    story.append(Paragraph("Observed Symptoms", st["heading"]))
    symptoms_table = Table(
        [
            ["Symptom 1:", report.symptom1],
            ["Symptom 2:", report.symptom2],
            ["Symptom 3:", report.symptom3],
        ],
        colWidths=[2 * inch, 4 * inch],
    )
    symptoms_table.setStyle(_symptoms_table_style(font, bold_font))
    story.append(symptoms_table)
    story.append(Spacer(1, 0.3 * inch))

    # ---- Detailed analysis (full bilingual text) ------------------------
    story.append(
        Paragraph("Detailed Analysis / \u062a\u0641\u0635\u06cc\u0644\u06cc \u062a\u062c\u0632\u06cc\u06c1", st["heading"])
    )
    if report.description:
        raw_html = _md_to_html(report.description)
        processed_html = _preprocess_html(raw_html)
        story.append(_safe_paragraph(processed_html, st["normal"]))
    story.append(Spacer(1, 0.3 * inch))

    # ---- Authentication status ------------------------------------------
    if report.authenticated_by.exists():
        story.append(Paragraph("Authentication Status", st["heading"]))
        auth_data = [["Authenticated By (Doctor)"]]
        for doctor in report.authenticated_by.all():
            auth_data.append([doctor.username])
            
        auth_table = Table(auth_data, colWidths=[6 * inch])
        auth_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), bold_font),
            ("FONTNAME", (0, 1), (-1, -1), font),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(auth_table)
        story.append(Spacer(1, 0.2 * inch))

    # ---- Comments -------------------------------------------------------
    if report.comments.exists():
        story.append(Paragraph("Doctor Comments", st["heading"]))
        comments_data = [["Doctor", "Date", "Comment"]]
        for comment in report.comments.order_by('created_at'):
            comments_data.append([
                comment.doctor.username,
                comment.created_at.strftime('%B %d, %Y'),
                Paragraph(comment.text, st["normal"])
            ])
            
        comments_table = Table(comments_data, colWidths=[1.5 * inch, 1.5 * inch, 3.5 * inch])
        comments_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f4f8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 0), (-1, 0), bold_font),
            ("FONTNAME", (0, 1), (-1, -1), font),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(comments_table)
        story.append(Spacer(1, 0.1 * inch))

    # ---- Footer ---------------------------------------------------------
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph("Generated by Livestock Disease Prediction System", st["footer"]))
    story.append(
        Paragraph(
            f"Report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            st["footer"],
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_image_report_pdf(image_report):
    """
    Generate a bilingual (English + Urdu) PDF for an image-based report.

    Args:
        image_report: ImageReport model instance

    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.5 * inch, bottomMargin=0.5 * inch,
    )
    story = []
    st = _build_styles()
    font = st["urdu_font"]
    bold_font = st["urdu_font_bold"]

    # ---- Title ----------------------------------------------------------
    story.append(Paragraph("Livestock Disease Prediction Report", st["title"]))
    story.append(Paragraph("Image-Based Analysis", st["sub_heading"]))
    story.append(Spacer(1, 0.3 * inch))

    # ---- Report info table ----------------------------------------------
    report_table = Table(
        [
            ["Report ID:",     f"#{image_report.id}"],
            ["Animal Type:",   image_report.get_animal_display()],
            ["Date Generated:", image_report.created_at.strftime("%B %d, %Y at %I:%M %p")],
            ["Created By:",    image_report.created_by.username],
        ],
        colWidths=[2 * inch, 4 * inch],
    )
    report_table.setStyle(_info_table_style(font, bold_font))
    story.append(report_table)
    story.append(Spacer(1, 0.3 * inch))

    # ---- Predicted disease & confidence ---------------------------------
    story.append(Paragraph("Predicted Disease", st["heading"]))
    disease_color = "#cc0000" if image_report.detected else "#00cc00"
    disease_html = (
        f"<b><font size='14' color='{disease_color}'>"
        f"{image_report.predicted_disease}</font></b>"
    )
    story.append(_safe_paragraph(disease_html, st["normal"]))
    story.append(
        _safe_paragraph(
            f"<b>Detection Confidence:</b> {image_report.confidence:.1f}%",
            st["normal"],
        )
    )
    story.append(Spacer(1, 0.2 * inch))

    # ---- Analyzed image -------------------------------------------------
    story.append(Paragraph("Images Analysis", st["heading"]))
    images_row = []
    
    # original image
    has_original = False
    try:
        if image_report.original_image and os.path.exists(image_report.original_image.path):
            img_path = image_report.original_image.path
            img_element = Image(img_path, width=3 * inch, height=2.25 * inch, kind="proportional")
            images_row.append([Paragraph("Original Image", st["sub_heading"]), img_element])
            has_original = True
    except Exception:
        pass

    # annotated image
    try:
        if image_report.annotated_image and os.path.exists(image_report.annotated_image.path):
            img_path = image_report.annotated_image.path
            img_element = Image(img_path, width=3 * inch, height=2.25 * inch, kind="proportional")
            images_row.append([Paragraph("Analyzed Image", st["sub_heading"]), img_element])
        else:
            if not has_original:
                story.append(_safe_paragraph("<i>Images could not be included in PDF</i>", st["normal"]))
    except Exception:
        if not has_original:
            story.append(_safe_paragraph("<i>Images could not be included in PDF</i>", st["normal"]))
            
    if images_row:
        # Transpose row elements to grid and create a table
        heads = [item[0] for item in images_row]
        imgs = [item[1] for item in images_row]
        img_table = Table([heads, imgs], colWidths=[3.5 * inch] * len(images_row))
        img_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,0), 10),
        ]))
        story.append(img_table)
        story.append(Spacer(1, 0.2 * inch))

    # ---- Detailed analysis (full bilingual text) ------------------------
    if image_report.description:
        full_html = _md_to_html(image_report.description)
        
        # Split English and Urdu
        # We assume English content has no Arabic chars and Urdu content does.
        # We can split by paragraphs/lines.
        lines = full_html.split('<br/>')
        english_lines = []
        urdu_lines = []
        
        for line in lines:
            if not line.strip():
                continue
            if re.search(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]', line):
                urdu_lines.append(line)
            else:
                english_lines.append(line)
        
        english_html = "<br/>".join(english_lines)
        urdu_html = "<br/>".join(urdu_lines)
        urdu_processed = _preprocess_html(urdu_html)

        if english_lines:
            story.append(Paragraph("Detailed Analysis", st["heading"]))
            story.append(_safe_paragraph(english_html, st["normal"]))
            story.append(Spacer(1, 0.2 * inch))
            
        if urdu_lines:
            story.append(Paragraph("تفصیلی تجزیہ", st["heading"]))
            # Important: apply TA_RIGHT or TA_JUSTIFY for Urdu block if preferred, default normal is fine.
            story.append(_safe_paragraph(urdu_processed, st["normal"]))
            story.append(Spacer(1, 0.3 * inch))

    # ---- Authentication status ------------------------------------------
    if image_report.authenticated_by.exists():
        story.append(Paragraph("Authentication Status", st["heading"]))
        auth_data = [["Authenticated By (Doctor)"]]
        for doctor in image_report.authenticated_by.all():
            auth_data.append([doctor.username])
            
        auth_table = Table(auth_data, colWidths=[6 * inch])
        auth_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), bold_font),
            ("FONTNAME", (0, 1), (-1, -1), font),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(auth_table)
        story.append(Spacer(1, 0.2 * inch))

    # ---- Comments -------------------------------------------------------
    if image_report.comments.exists():
        story.append(Paragraph("Doctor Comments", st["heading"]))
        comments_data = [["Doctor", "Date", "Comment"]]
        for comment in image_report.comments.order_by('created_at'):
            comments_data.append([
                comment.doctor.username,
                comment.created_at.strftime('%B %d, %Y'),
                Paragraph(comment.text, st["normal"])
            ])
            
        comments_table = Table(comments_data, colWidths=[1.5 * inch, 1.5 * inch, 3.5 * inch])
        comments_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f4f8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 0), (-1, 0), bold_font),
            ("FONTNAME", (0, 1), (-1, -1), font),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(comments_table)
        story.append(Spacer(1, 0.1 * inch))

    # ---- Footer ---------------------------------------------------------
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph("Generated by Livestock Disease Prediction System", st["footer"]))
    story.append(
        Paragraph(
            f"Report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            st["footer"],
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer
