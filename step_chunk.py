import re

from step1_extract import extract_pages
from step2_clean import build_clean_pages
from step3_language import add_language


# ============================================================
# Settings (agree on these with Member 4 once the embedding
# model is chosen: every model cuts text after a token limit)
# ============================================================

CHUNK_SIZE = 250   # maximum number of words in one chunk
OVERLAP = 40       # about this many words are repeated from the previous chunk
MIN_WORDS = 5      # chunks shorter than this are dropped (e.g. "Thank you")

# A sentence ends after . ! ? or the Arabic question mark ؟ and a space.
SENTENCE_END = re.compile(r"(?<=[.!?؟۔])\s+")


# ============================================================
# 1. Helpers
# ============================================================

def count_words(text: str) -> int:
    return len(text.split())

def merge_wrapped_lines(text: str) -> list[str]:

    lines = []
    raw_lines = text.split("\n")
    full_width = max((len(l) for l in raw_lines), default=0) * 0.85   # جديد

    for line in raw_lines:
        previous = lines[-1] if lines else ""

        if (
            previous
            and len(previous.split()) >= 8
            and not previous.endswith((".", "!", "?", "؟", "۔", ":", ";"))
            and len(previous) >= full_width                            # جديد: السطر اللي قبله واصل لعرض الصفحة
            and not line[:1].isupper()                                 # جديد: السطر ده مش بادئ بحرف كبير
            and line.split()[0] not in ("-", "•", "*", "▪", "–")       # جديد: مش bullet
        ):
            lines[-1] = previous + " " + line
        else:
            lines.append(line)

    return lines

def split_into_units(text: str, chunk_size: int) -> list[str]:
    """
    Split a page into small pieces ("units"): one per sentence or line.
    Chunks are built from whole units, so a chunk never starts or ends
    in the middle of a sentence (unless one sentence is longer than a chunk).
    """

    units = []

    for line in merge_wrapped_lines(text):
        for sentence in SENTENCE_END.split(line):
            sentence = sentence.strip()

            if not sentence:
                continue

            # A unit longer than a whole chunk is cut by words.
            words = sentence.split()
            for start in range(0, len(words), chunk_size):
                units.append(" ".join(words[start:start + chunk_size]))

    return units


def take_overlap(units: list[str], overlap: int) -> tuple[list[str], int]:
    """Take whole units from the END of a chunk, up to `overlap` words."""

    kept = []
    total = 0

    for unit in reversed(units):
        words = count_words(unit)

        if total + words > overlap:
            break

        kept.insert(0, unit)
        total += words

    return kept, total


# ============================================================
# 2. Chunk the text of ONE page
# ============================================================

def chunk_page_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Group the units of one page into chunks of at most `chunk_size` words."""

    chunks = []
    current = []         # units inside the chunk we are building
    current_words = 0

    for unit in split_into_units(text, chunk_size):
        words = count_words(unit)

        # The chunk is full: save it and start the next one.
        if current and current_words + words > chunk_size:
            chunks.append("\n".join(current))

            # The next chunk starts with the end of this one (the overlap).
            current, current_words = take_overlap(current, overlap)

            # If the new unit still does not fit, drop the oldest overlap.
            while current and current_words + words > chunk_size:
                dropped = current.pop(0)
                current_words -= count_words(dropped)

        current.append(unit)
        current_words += words

    if current:
        chunks.append("\n".join(current))

    return chunks


# ============================================================
# 3. Chunk the WHOLE lecture
# ============================================================

def build_chunks(
    pages,
    lecture_id: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = OVERLAP,
    min_words: int = MIN_WORDS,
) -> list[dict]:
    """
    Take the pages (after cleaning + add_language) and return the chunks
    with the metadata from the project documentation:
    chunk_id, lecture_id, page_number, text (plus language and word_count).
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be 0 or more, and smaller than chunk_size.")

    chunks = []

    for page in pages:
        # Each page is chunked on its own, so a chunk never crosses a page
        # boundary and its page_number is always correct for the citation.
        for text in chunk_page_text(page["cleaned_text"], chunk_size, overlap):
            words = count_words(text)

            if words < min_words:
                continue

            chunks.append({
                # lecture_id inside the id keeps it unique across lectures.
                "chunk_id": f"{lecture_id}_{len(chunks) + 1:04d}",
                "lecture_id": lecture_id,
                "page_number": page["page_number"],
                "language": page.get("language", "Unknown"),
                "text": text,
                "word_count": words,
            })

    return chunks


if __name__ == "__main__":
    # Replace this with the path of any lecture PDF.
    pdf_path = "Computational Models.pdf"

    pages = add_language(build_clean_pages(extract_pages(pdf_path)))
    chunks = build_chunks(pages, lecture_id="demo")

    sizes = [chunk["word_count"] for chunk in chunks]
    pages_with_chunks = {chunk["page_number"] for chunk in chunks}
    empty_pages = [p["page_number"] for p in pages if p["page_number"] not in pages_with_chunks]

    print(f"Pages: {len(pages)} | Chunks: {len(chunks)}")
    print(f"Words per chunk: min {min(sizes)}, max {max(sizes)}, "
          f"average {sum(sizes) // len(sizes)}")
    print(f"Pages without any chunk: {empty_pages or 'none'}")

    print("\n---- First 3 chunks ----")
    for chunk in chunks[:3]:
        print(f"\n[{chunk['chunk_id']}] page {chunk['page_number']} "
            f"| {chunk['language']} | {chunk['word_count']} words")
        print(chunk["text"][:200])