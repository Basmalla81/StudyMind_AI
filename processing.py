from step1_extract import extract_pages
from step2_clean import build_clean_pages
from step3_language import add_language, detect_document_language
from step_chunk import build_chunks


class LectureProcessingError(Exception):
    """Raised when a PDF cannot be processed (corrupted, protected, scanned)."""


def process_lecture(pdf_path: str, lecture_id: str) -> dict:
    """
    The ONE function Member 2 (backend) calls after saving the uploaded PDF.

    Returns:
        {
          "lecture_id":  str,
          "language":    "Arabic" | "English" | "Mixed" | "Unknown",
          "page_count":  int,
          "empty_pages": [page numbers with no text],
          "pages":  [{"page_number", "language", "text"}]   # for summary / quiz
          "chunks": [{"chunk_id", "lecture_id", "page_number",
                      "language", "text", "word_count"}]    # for RAG
        }
    Raises LectureProcessingError with a message safe to show to the user.
    """

    try:
        pages = add_language(build_clean_pages(extract_pages(pdf_path)))
    except Exception as error:
        raise LectureProcessingError(
            "Could not read the PDF. It may be corrupted or password-protected."
        ) from error

    empty_pages = [p["page_number"] for p in pages if not p["cleaned_text"].strip()]

    if not pages or len(empty_pages) == len(pages):
        raise LectureProcessingError(
            "No extractable text found. This looks like a scanned PDF."
        )

    return {
        "lecture_id": lecture_id,
        "language": detect_document_language(pages),
        "page_count": len(pages),
        "empty_pages": empty_pages,
        "pages": [
            {
                "page_number": p["page_number"],
                "language": p["language"],
                "text": p["cleaned_text"],
            }
            for p in pages
        ],
        "chunks": build_chunks(pages, lecture_id=lecture_id),
    }