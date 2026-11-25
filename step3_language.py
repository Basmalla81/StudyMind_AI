import re
from step1_extract import extract_pages
from step2_clean import build_clean_pages

ARABIC_LETTERS = re.compile(r"[\u0621-\u064A\u0671-\u06D3\u0750-\u077F]")
LATIN_LETTERS = re.compile(r"[A-Za-z]")

def count_letters(text: str) -> tuple[int, int]:
    """Return (arabic_letters, latin_letters) found in the text."""

    arabic = len(ARABIC_LETTERS.findall(text))
    latin = len(LATIN_LETTERS.findall(text))

    return arabic, latin

def detect_language(
    text: str,
    arabic_threshold: float = 0.7,
    english_threshold: float = 0.3,
    min_letters: int = 10,
) -> str:
    """Label a page as Arabic, English, Mixed, or Unknown."""

    arabic, latin = count_letters(text)
    total = arabic + latin

    if total < min_letters:
        return "Unknown"

    arabic_ratio = arabic / total

    if arabic_ratio >= arabic_threshold:
        return "Arabic"

    if arabic_ratio <= english_threshold:
        return "English"

    return "Mixed"

def detect_document_language(pages) -> str:
    """Use all letters in the lecture, so big pages count more."""

    all_text = "\n".join(page["cleaned_text"] for page in pages)

    return detect_language(all_text)

def add_language(pages):
    """Add a 'language' field to each page dictionary."""

    for page in pages:
        page["language"] = detect_language(page["cleaned_text"])

    return pages


if __name__ == "__main__":
    pdf_path = "lecture.pdf"

    pages = build_clean_pages(extract_pages(pdf_path))
    pages = add_language(pages)

    print(f"Lecture language: {detect_document_language(pages)}\n")

    for page in pages:
        arabic, latin = count_letters(page["cleaned_text"])
        print(
            f"Page {page['page_number']:>3} | {page['language']:<8} "
            f"| Arabic letters: {arabic:>5} | English letters: {latin:>5}"
        )