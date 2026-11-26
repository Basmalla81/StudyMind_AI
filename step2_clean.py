import re
import unicodedata
from collections import Counter

from step1_extract import extract_pages

INVISIBLE_CHARS = re.compile(
    r"[\u200b-\u200f\u202a-\u202e\u2066-\u2069\u00ad\ufeff]"
)

TATWEEL = "\u0640"

PRESENTATION_FORMS = re.compile(r"[\uFB00-\uFB06\uFB50-\uFDFF\uFE70-\uFEFF]+")
ARABIC_DIACRITICS = re.compile(r"[\u064B-\u0652\u0670]")

def normalize_presentation_forms(text: str) -> str:
    """NFKC على أشكال الحروف بس، وباقي الرموز (², ½, µ) متتغيرش."""
    return PRESENTATION_FORMS.sub(
        lambda m: unicodedata.normalize("NFKC", m.group()), text
    )


# Symbol-font characters (private use area) that PDFs use for math signs.
PUA_CHARS = re.compile(r"[\uE000-\uF8FF]")
PUA_TO_ASCII = {
    0xF02A: "*", 0xF02B: "+", 0xF02D: "-", 0xF03D: "=", 0xF028: "(",
    0xF029: ")", 0xF03C: "<", 0xF03E: ">", 0xF02F: "/",
}


def fix_private_use(text: str) -> str:
    """Convert known math signs, and delete the unknown private characters."""
    return PUA_CHARS.sub(lambda m: PUA_TO_ASCII.get(ord(m.group()), ""), text)


def clean_text(text: str) -> str:
    """Clean extracted text without changing its meaning."""


    text = normalize_presentation_forms(text)
    text = fix_private_use(text)

    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = INVISIBLE_CHARS.sub("", text)
    text = text.replace(TATWEEL, "")
    text = ARABIC_DIACRITICS.sub("", text)

    cleaned_lines = []

    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        
        if line:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)

def _line_key(line: str) -> str:
    """Replace digits with '#', so 'Page 3 of 15' equals 'Page 4 of 15'."""
    return re.sub(r"\d+", "#", line)


def remove_repeated_lines(pages, threshold=0.6, min_pages=5):
    """
    Remove lines that appear on at least `threshold` of the pages
    (page numbers, lecture title, doctor name, ...).
    Skipped for short documents, where repetition proves nothing.
    """

    if len(pages) < min_pages:
        return pages

    counter = Counter()

    for page in pages:
        keys = {_line_key(line) for line in page["cleaned_text"].split("\n")}
        counter.update(keys)

    limit = len(pages) * threshold
    repeated_keys = {key for key, count in counter.items() if count >= limit}

    for page in pages:
        kept_lines = [
            line
            for line in page["cleaned_text"].split("\n")
            if _line_key(line) not in repeated_keys
        ]
        page["cleaned_text"] = "\n".join(kept_lines)

    return pages

def build_clean_pages(raw_pages):
    """Take the output of extract_pages() and add cleaned_text."""

    pages = []

    for raw_page in raw_pages:
        pages.append({
            "page_number": raw_page["page_number"],
            # Keep the original text untouched, for comparison.
            "original_text": raw_page["text"],
            "cleaned_text": clean_text(raw_page["text"]),
        })

    return remove_repeated_lines(pages)


if __name__ == "__main__":
    pdf_path = "Computational Models.pdf"
    pages = build_clean_pages(extract_pages(pdf_path))
    first = pages[9]
    print("---- BEFORE CLEANING (page 1) ----")
    print(first["original_text"][:400])
    print("\n---- AFTER CLEANING (page 1) ----")
    print(first["cleaned_text"][:400])