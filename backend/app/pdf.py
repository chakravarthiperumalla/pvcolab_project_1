"""Markdown -> PDF using python-markdown + xhtml2pdf (pure Python, no system libraries)."""
from io import BytesIO

import markdown
from xhtml2pdf import pisa

CSS = """
@page { size: A4; margin: 2cm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1a1a1a; }
h1 { font-size: 22pt; margin-top: 18pt; }
h2 { font-size: 15pt; margin-top: 16pt; border-bottom: 1px solid #ccc; padding-bottom: 3pt; }
h3 { font-size: 12pt; margin-top: 12pt; }
code, pre { font-family: Courier, monospace; font-size: 9pt; background-color: #f3f3f3; }
pre { padding: 6pt; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #bbb; padding: 4pt; text-align: left; }
"""


def markdown_to_pdf(md_text: str) -> bytes:
    body = markdown.markdown(md_text, extensions=["tables", "fenced_code", "sane_lists"])
    html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"
    buf = BytesIO()
    result = pisa.CreatePDF(html, dest=buf, encoding="utf-8")
    if result.err:
        raise RuntimeError("PDF generation failed")
    return buf.getvalue()
