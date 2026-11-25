import pymupdf

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
            pages.append({"page_number": page_number, "text": text})

    return pages


if __name__ == "__main__":

    pdf_path = "lecture.pdf"

    pages = extract_pages(pdf_path)

    print(f"Number of pages: {len(pages)}")
    print("\n---- First 300 characters of page 1 ----")
    print(pages[0]["text"][:300])