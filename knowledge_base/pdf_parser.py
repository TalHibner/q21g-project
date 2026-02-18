"""Low-level PDF text extraction and paragraph splitting.

Building Block: extract_text_from_pdf / split_into_paragraphs
    Input Data:  Path to a PDF file
    Output Data: List of page dicts, or list of paragraph strings
    Setup Data:  pdfplumber library
"""

import re
from pathlib import Path

import pdfplumber


def extract_text_from_pdf(pdf_path: Path) -> list[dict]:
    """Extract text page-by-page from a single PDF."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and text.strip():
                pages.append({"page_number": i + 1, "text": text.strip()})
    return pages


def split_into_paragraphs(full_text: str, min_words: int = 15) -> list[str]:
    """Split text into content paragraphs, filtering noise.

    Splits on double newlines, then filters out headers, TOC lines,
    tables, and short fragments.
    """
    raw = re.split(r'\n\s*\n', full_text)
    paragraphs = []

    for p in raw:
        p = p.strip()
        words = p.split()
        if len(words) < min_words:
            continue
        # Skip TOC-style lines (number prefix + short text)
        if re.match(r'^[\d.]+\s', p) and len(words) < 10:
            continue
        # Skip content that's mostly numbers/symbols (tables, formulas)
        alpha_count = sum(1 for c in p if c.isalpha())
        if alpha_count / max(len(p), 1) < 0.4:
            continue
        paragraphs.append(p)

    return paragraphs
