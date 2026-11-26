import re

import pymupdf

ARABIC = re.compile(r"[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]")
BULLETS = {"•", "●", "▪", "◦", "·", "-", "–", "*"}


def _is_arabic(text: str) -> bool:
    return bool(ARABIC.search(text))


def _page_text_by_rows(page) -> str:
    """
    Rebuild the text of a page that contains Arabic.

    PyMuPDF returns the pieces (spans) of a visual line in a wrong order when
    Arabic and English are mixed. Here we collect all the pieces, group the
    ones that sit on the same row, and order each row by its x position:
    right-to-left if the row has Arabic, left-to-right otherwise.
    """

    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["text"].strip()]
            for s in spans:
                s["line_id"] = id(line)
            if spans:
                x0, y0, x1, y1 = line["bbox"]
                lines.append({"spans": spans, "center": (y0 + y1) / 2, "height": y1 - y0})

    # Group lines whose vertical centers are close into rows.
    lines.sort(key=lambda l: l["center"])
    rows = []
    for line in lines:
        if rows and abs(line["center"] - rows[-1]["center"]) <= 0.5 * line["height"]:
            rows[-1]["spans"].extend(line["spans"])
        else:
            rows.append({"center": line["center"], "height": line["height"],
                         "spans": list(line["spans"])})

    output = []
    for row in rows:
        spans = row["spans"]
        rtl = any(_is_arabic(s["text"]) for s in spans)

        bullets = [s for s in spans if s["text"].strip() in BULLETS]
        rest = [s for s in spans if s["text"].strip() not in BULLETS]
        rest.sort(key=lambda s: s["bbox"][0], reverse=rtl)

        parts = []
        previous = None
        for span in bullets + rest:
            raw = span["text"]
            text = raw.strip()
            if previous is not None:
                gap = abs(span["bbox"][0] - previous["bbox"][2]) if not rtl \
                    else abs(previous["bbox"][0] - span["bbox"][2])
                joined = (
                    span["line_id"] == previous["line_id"]       # same PyMuPDF line
                    and _is_arabic(text) == _is_arabic(previous["text"])  # same script
                    and raw == raw.strip() and previous["text"] == previous["text"].strip()
                    and gap <= 1.5
                )
                parts.append("" if joined else " ")
            parts.append(text)
            previous = span
        output.append("".join(parts))

    return "\n".join(output)


def extract_pages(pdf_path: str) -> list[dict]:
    """
    Read a PDF and return one dictionary per page:
    [{"page_number": 1, "text": "..."}, {"page_number": 2, "text": "..."}, ...]
    """

    pages = []

    with pymupdf.open(pdf_path) as document:

        if document.needs_pass:
            raise RuntimeError("This PDF is password-protected.")

        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text")

            # Only pages with Arabic need the careful row-by-row rebuild.
            if _is_arabic(text):
                text = _page_text_by_rows(page)

            pages.append({"page_number": page_number, "text": text})

    return pages