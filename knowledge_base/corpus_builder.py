"""PDF to paragraphs extraction pipeline.

Input:  course_pdfs/ directory with Hebrew PDF files
Output: knowledge_base/data/paragraphs.json
"""

import json
import re
from pathlib import Path

import pdfplumber

from knowledge_base.sentence_extractor import extract_first_sentence


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


def build_corpus(pdf_dir: Path, output_dir: Path) -> dict:
    """Main pipeline: PDFs -> paragraphs.json.

    Returns the full data dict with paragraphs and metadata.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    all_paragraphs = []

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDFs")

    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}")
        pages = extract_text_from_pdf(pdf_path)
        full_text = "\n\n".join(p["text"] for p in pages)
        paragraphs = split_into_paragraphs(full_text)
        print(f"  -> {len(paragraphs)} paragraphs")

        for i, para_text in enumerate(paragraphs):
            all_paragraphs.append({
                "id": f"{pdf_path.stem}_p{i:04d}",
                "pdf_name": pdf_path.stem,
                "pdf_filename": pdf_path.name,
                "paragraph_index": i,
                "text": para_text,
                "opening_sentence": extract_first_sentence(para_text),
                "word_count": len(para_text.split()),
            })

    data = {
        "paragraphs": all_paragraphs,
        "metadata": {
            "total_paragraphs": len(all_paragraphs),
            "total_pdfs": len(pdf_files),
            "pdf_names": [p.stem for p in pdf_files],
        },
    }

    json_path = output_dir / "paragraphs.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(all_paragraphs)} paragraphs to {json_path}")

    return data


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    pdf_dir = project_root / "course_pdfs"
    output_dir = Path(__file__).resolve().parent / "data"
    build_corpus(pdf_dir, output_dir)
