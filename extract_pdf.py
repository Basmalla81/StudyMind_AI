import json
import re
import unicodedata
from pathlib import Path
from tkinter import Tk, filedialog

import pymupdf


# ============================================================
# 1. CONFIGURATION
# ============================================================

CHUNK_SIZE_WORDS = 500
CHUNK_OVERLAP_WORDS = 80


# ============================================================
# 2. TEXT CLEANING & NORMALIZATION
# ============================================================

def clean_text(text: str) -> str:
    """Clean extracted text while preserving its wording and meaning."""

    # Normalize Unicode representation.
    text = unicodedata.normalize("NFC", text)

    # Remove null characters and normalize line endings.
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    cleaned_lines = []

    for line in text.split("\n"):
        # Replace repeated spaces and tabs with a single space.
        line = re.sub(r"[ \t]+", " ", line).strip()

        # Keep non-empty lines.
        if line:
            cleaned_lines.append(line)

    # Join non-empty lines.
    return "\n".join(cleaned_lines)


def detect_language(text: str) -> str:
    """Return a simple language label based on the presence of Arabic letters."""

    if re.search(r"[\u0600-\u06FF]", text):
        return "Arabic"

    return "English"


# ============================================================
# 3. PAGE-AWARE TEXT CHUNKING
# ============================================================

def create_chunks(
    pages,
    chunk_size=CHUNK_SIZE_WORDS,
    overlap=CHUNK_OVERLAP_WORDS
):
    """
    Split cleaned page text into word-based chunks.
    Each chunk keeps its source page number and language.
    Chunks do not cross page boundaries.
    """

    if chunk_size <= 0:
        raise ValueError("Chunk size must be greater than zero.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "Chunk overlap must be zero or greater, and smaller than chunk size."
        )

    chunks = []
    chunk_id = 1
    step = chunk_size - overlap

    for page in pages:
        words = page["cleaned_text"].split()

        if not words:
            continue

        start = 0

        while start < len(words):
            end = min(start + chunk_size, len(words))

            chunks.append({
                "chunk_id": chunk_id,
                "page_number": page["page_number"],
                "language": page["language"],
                "text": " ".join(words[start:end])
            })

            chunk_id += 1

            if end == len(words):
                break

            start += step

    return chunks


# ============================================================
# 4. SELECT PDF FILE
# ============================================================

def select_pdf():
    """Open a dialog so the user can select any PDF."""

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    selected_path = filedialog.askopenfilename(
        title="Choose a Lecture PDF",
        filetypes=[("PDF files", "*.pdf")]
    )

    root.destroy()
    return selected_path


# ============================================================
# 5. SAVE OUTPUT FILES
# ============================================================

def save_outputs(pdf_file, output_folder, pages, chunks):
    """Save page JSON, cleaned TXT, chunks JSON, and before/after comparison."""

    # Output file paths.
    pages_json_path = output_folder / f"{pdf_file.stem}_pages.json"
    text_path = output_folder / f"{pdf_file.stem}_text.txt"
    chunks_json_path = output_folder / f"{pdf_file.stem}_chunks.json"
    comparison_path = output_folder / f"{pdf_file.stem}_comparison.txt"

    # A. Save original and cleaned page text in JSON.
    with pages_json_path.open("w", encoding="utf-8") as file:
        json.dump(pages, file, ensure_ascii=False, indent=4)

    # B. Save cleaned text in a readable TXT file.
    with text_path.open("w", encoding="utf-8") as file:
        for page in pages:
            file.write(f"\n--- Page {page['page_number']} ---\n")
            file.write(page["cleaned_text"])
            file.write("\n")

    # C. Save chunks for the RAG team.
    with chunks_json_path.open("w", encoding="utf-8") as file:
        json.dump(chunks, file, ensure_ascii=False, indent=4)

    # D. Save before/after comparison.
    with comparison_path.open("w", encoding="utf-8") as file:
        for page in pages:
            file.write("\n" + "=" * 65 + "\n")
            file.write(f"PAGE {page['page_number']}\n")
            file.write("=" * 65 + "\n")

            file.write("\n--- BEFORE CLEANING ---\n")
            file.write(page["original_text"])

            file.write("\n\n--- AFTER CLEANING ---\n")
            file.write(page["cleaned_text"])

            file.write("\n\n")

    return (
        pages_json_path,
        text_path,
        chunks_json_path,
        comparison_path
    )


# ============================================================
# 6. PROCESS THE SELECTED PDF
# ============================================================

def process_pdf(pdf_path: str):
    pdf_file = Path(pdf_path)

    # Save results inside the project folder, not beside the source PDF.
    project_folder = Path(__file__).resolve().parent
    output_folder = project_folder / "processed_files" / pdf_file.stem
    output_folder.mkdir(parents=True, exist_ok=True)

    pages = []

    print("\nOpening PDF...")

    with pymupdf.open(pdf_path) as document:

        if document.is_encrypted:
            raise RuntimeError(
                "This PDF is password-protected. Unlock it before processing."
            )

        total_pages = len(document)

        for page_number, page in enumerate(document, start=1):

            # Keep the original extracted text unchanged for comparison.
            original_text = page.get_text("text")

            # Create a separate cleaned version.
            cleaned_text = clean_text(original_text)

            pages.append({
                "page_number": page_number,
                "language": detect_language(cleaned_text),
                "original_text": original_text,
                "cleaned_text": cleaned_text
            })

            print(f"Processed page {page_number}/{total_pages}")

    # Check whether any selectable text was extracted.
    total_words = sum(
        len(page["cleaned_text"].split()) for page in pages
    )

    if total_words == 0:
        raise RuntimeError(
            "No selectable text was found. This may be a scanned PDF "
            "that requires OCR."
        )

    # Create chunks from cleaned text.
    chunks = create_chunks(pages)

    # Save all four output files.
    output_paths = save_outputs(
        pdf_file,
        output_folder,
        pages,
        chunks
    )

    # Print processing summary.
    print("\n" + "=" * 55)
    print("StudyMind AI - Processing completed successfully")
    print("=" * 55)
    print(f"PDF name: {pdf_file.name}")
    print(f"Total pages: {len(pages)}")
    print(f"Extracted words: {total_words}")
    print(f"Chunks created: {len(chunks)}")
    print(f"\nOutput folder:\n{output_folder}")

    print("\nGenerated files:")
    for index, path in enumerate(output_paths, start=1):
        print(f"{index}. {path.name}")

    print("=" * 55)


# ============================================================
# 7. MAIN PROGRAM
# ============================================================

def main():
    print("StudyMind AI - PDF Processing & NLP")
    print("Select a lecture PDF to begin.")

    pdf_path = select_pdf()

    if not pdf_path:
        print("\nNo PDF selected. Program stopped.")
        return

    try:
        process_pdf(pdf_path)

    except Exception as error:
        print(f"\nProcessing failed: {error}")

    input("\nPress Enter to close...")


if __name__ == "__main__":
    main()
