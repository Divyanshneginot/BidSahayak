#!/usr/bin/env python3
"""Regenerate sample_tenders/up_jal_nigam_hindi.pdf with an embedded Devanagari font.

Why: the original fixture was produced by reportlab's default Helvetica, which has no
Devanagari glyphs, so every Hindi character landed in the PDF as a tofu box (U+25A0).
The text layer was therefore not machine-readable and the fixture could not test the
Hindi path it exists to test. Same content, same page count, real glyphs.

Run: python scripts/regenerate_hindi_fixture.py  (requires reportlab + the bundled font)
"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

FONT = ".fonts/NotoSansDevanagari.ttf"
OUT = "sample_tenders/up_jal_nigam_hindi.pdf"

TITLE = "उत्तर प्रदेश जल निगम (ग्रामीण) - निविदा आमंत्रण सूचना"
DEPT = "नमामि गंगे एवं ग्रामीण जलापूर्ति विभाग, उत्तर प्रदेश"
CONTENT = [
    ("निविदा सूचना संख्या: 18/ज.नि./2026",
     "ग्राम पेयजल योजना अंतर्गत ओवरहेड टैंक एवं वितरण प्रणाली निर्माण कार्य। अनुमानित लागत: ₹45,00,000।"),
    ("बयाना राशि एवं महत्वपूर्ण तिथियां",
     "बयाना राशि (EMD): ₹50,000 राष्ट्रीयकृत बैंक की एफडीआर/बैंक गारंटी के रूप में। "
     "निविदा प्रस्तुत करने की अंतिम तिथि: 21-10-2026।"),
    ("पात्रता एवं वार्षिक कारोबार",
     "बोलीदाता का पिछले 3 वित्तीय वर्षों में न्यूनतम औसत वार्षिक कारोबार ₹25,00,000 होना अनिवार्य है।"),
    ("एमएसएमई छूट प्रावधान",
     "सूक्ष्म एवं लघु उद्यमों (MSEs) को जीएफआर नियम 170 के अनुसार बयाना राशि से पूर्ण छूट प्रदान की जाएगी।"),
]
PAGES = 14


def main() -> None:
    if not os.path.exists(FONT):
        raise SystemExit(f"missing font: {FONT}")
    pdfmetrics.registerFont(TTFont("NotoDevanagari", FONT))
    title_style = ParagraphStyle("T", fontName="NotoDevanagari", fontSize=14, leading=20,
                                 alignment=1, textColor=colors.navy)
    h2 = ParagraphStyle("H2", fontName="NotoDevanagari", fontSize=11, leading=16, textColor=colors.black)
    body = ParagraphStyle("B", fontName="NotoDevanagari", fontSize=9, leading=14)
    en = ParagraphStyle("EN", fontName="Helvetica", fontSize=9, leading=14)

    doc = SimpleDocTemplate(OUT, pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    story = [Paragraph(TITLE, title_style), Spacer(1, 8), Paragraph(f"<b>Issuing Authority:</b> {DEPT}", body), Spacer(1, 14)]
    for h, txt in CONTENT:
        story += [Paragraph(h, h2), Spacer(1, 4), Paragraph(txt, body), Spacer(1, 10)]
    for p in range(1, PAGES):
        story += [PageBreak(), Paragraph(f"<b>{TITLE} — Page {p + 1} of {PAGES}</b>", h2), Spacer(1, 10),
                  Paragraph("General Conditions and Standard Contract Clauses. Detailed specifications, "
                            "bill of quantities (BOQ), and compliance schedules continued. All clauses "
                            "governed by GFR 2017 and procurement guidelines.", en), Spacer(1, 15)]
    doc.build(story)
    print(f"regenerated {OUT} ({PAGES} pages) with an embedded Devanagari font")


if __name__ == "__main__":
    main()
