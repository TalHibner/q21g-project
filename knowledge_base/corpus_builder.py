"""PDF to paragraphs extraction pipeline.

Uses multiprocessing to parse PDFs in parallel (CPU-bound task).

Input:  course_pdfs/ directory with Hebrew PDF files
Output: knowledge_base/data/paragraphs.json
"""

import json
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from knowledge_base.pdf_parser import extract_text_from_pdf, split_into_paragraphs
from knowledge_base.sentence_extractor import extract_first_sentence

logger = logging.getLogger(__name__)



def _process_single_pdf(pdf_path: Path) -> list[dict]:
    """Process a single PDF into paragraph records (runs in worker process).

    This function is designed to run in a separate process via
    ProcessPoolExecutor.  Each worker independently extracts text,
    splits into paragraphs, and detects opening sentences — fully
    CPU-bound work that benefits from true parallelism.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of paragraph dicts ready for the corpus.
    """
    pages = extract_text_from_pdf(pdf_path)
    full_text = "\n\n".join(p["text"] for p in pages)
    paragraphs = split_into_paragraphs(full_text)

    records = []
    for i, para_text in enumerate(paragraphs):
        records.append({
            "id": f"{pdf_path.stem}_p{i:04d}",
            "pdf_name": pdf_path.stem,
            "pdf_filename": pdf_path.name,
            "paragraph_index": i,
            "text": para_text,
            "opening_sentence": extract_first_sentence(para_text),
            "word_count": len(para_text.split()),
        })
    return records


def build_corpus(pdf_dir: Path, output_dir: Path) -> dict:
    """Main pipeline: PDFs -> paragraphs.json.

    Uses multiprocessing to parse PDFs in parallel across available
    CPU cores.  Each PDF is processed independently (CPU-bound: text
    extraction, paragraph splitting, sentence detection), making this
    an ideal multiprocessing workload.

    Falls back to sequential processing if the process pool fails.

    Returns the full data dict with paragraphs and metadata.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    all_paragraphs: list[dict] = []

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDFs")

    # Use multiprocessing for parallel PDF parsing (CPU-bound)
    n_workers = min(len(pdf_files), multiprocessing.cpu_count() or 1)
    logger.info("Parsing %d PDFs with %d worker processes", len(pdf_files), n_workers)

    try:
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            futures = {
                pool.submit(_process_single_pdf, pdf_path): pdf_path
                for pdf_path in pdf_files
            }
            for future in as_completed(futures):
                pdf_path = futures[future]
                try:
                    records = future.result()
                    all_paragraphs.extend(records)
                    print(f"Processing: {pdf_path.name}  -> {len(records)} paragraphs")
                except Exception as exc:
                    logger.error("Failed to process %s: %s", pdf_path.name, exc)
    except Exception as exc:
        # Fallback: sequential processing if pool fails
        logger.warning("Process pool failed (%s), falling back to sequential", exc)
        for pdf_path in pdf_files:
            records = _process_single_pdf(pdf_path)
            all_paragraphs.extend(records)
            print(f"Processing: {pdf_path.name}  -> {len(records)} paragraphs")

    # Sort by ID to ensure deterministic output regardless of process order
    all_paragraphs.sort(key=lambda p: p["id"])

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
