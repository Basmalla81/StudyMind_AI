import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from step1_extract import extract_pages
from step2_clean import build_clean_pages
from step3_language import add_language, detect_document_language


# ============================================================
# Settings
# ============================================================

# Uploaded PDFs are saved here (a new folder next to this file).
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_SIZE_MB = 50

app = FastAPI(title="StudyMind - PDF upload test")


# ============================================================
# 1. A simple page with an upload form  ->  http://127.0.0.1:8000
# ============================================================

UPLOAD_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>StudyMind - Upload lecture</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 760px;
           margin: 40px auto; padding: 0 16px; line-height: 1.5; }
    button { padding: 8px 16px; font-size: 1rem; cursor: pointer; }
    pre { background: #f2f2f2; padding: 12px; overflow-x: auto;
          white-space: pre-wrap; border-radius: 6px; }
  </style>
</head>
<body>
  <h1>Upload a lecture</h1>
  <p>Choose a PDF from your computer.</p>

  <input type="file" id="file" accept="application/pdf">
  <button id="send">Upload</button>

  <p id="status"></p>
  <pre id="result" hidden></pre>

  <script>
    const status = document.getElementById("status");
    const result = document.getElementById("result");

    document.getElementById("send").addEventListener("click", async () => {
      const file = document.getElementById("file").files[0];
      if (!file) {
        status.textContent = "Choose a PDF first.";
        return;
      }

      const formData = new FormData();
      formData.append("file", file);

      status.textContent = "Processing...";
      result.hidden = true;

      const response = await fetch("/api/lectures", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();

      if (response.ok) {
        status.textContent = "Done.";
        result.textContent = JSON.stringify(data, null, 2);
      } else {
        status.textContent = "Upload failed.";
        result.textContent = data.detail;
      }
      result.hidden = false;
    });
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home():
    return UPLOAD_PAGE


# ============================================================
# 2. The upload endpoint (same name as in the project documentation)
# ============================================================

@app.post("/api/lectures")
def upload_lecture(file: UploadFile = File(...)):
    """Receive a PDF, save it, then run extract -> clean -> language."""

    # Only accept PDFs.
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    # Save under a random id. We never use the uploaded file name as the
    # path, because a name like "../../x.pdf" could write outside the folder.
    lecture_id = uuid.uuid4().hex
    saved_path = UPLOAD_DIR / f"{lecture_id}.pdf"

    with saved_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    # Check the real content: every PDF starts with "%PDF", and check the size.
    with saved_path.open("rb") as saved:
        looks_like_pdf = saved.read(5).startswith(b"%PDF")

    too_big = saved_path.stat().st_size > MAX_SIZE_MB * 1024 * 1024

    if not looks_like_pdf or too_big:
        saved_path.unlink()
        raise HTTPException(
            status_code=400,
            detail=f"The file must be a valid PDF under {MAX_SIZE_MB} MB.",
        )

    # Run the pipeline from steps 1, 2 and 3.
    try:
        pages = build_clean_pages(extract_pages(str(saved_path)))
    except Exception as error:
        saved_path.unlink()
        print(f"PDF processing failed: {error}")  # details stay in the terminal
        raise HTTPException(
            status_code=400,
            detail="Could not read the PDF. It may be corrupted or password-protected.",
        )

    pages = add_language(pages)

    # Pages with no text (images / scanned pages).
    empty_pages = [p["page_number"] for p in pages if not p["cleaned_text"].strip()]

    # Version 1 does not support OCR, so a fully scanned PDF is rejected.
    if len(empty_pages) == len(pages):
        saved_path.unlink()
        raise HTTPException(
            status_code=422,
            detail="No extractable text found. This looks like a scanned PDF.",
        )

    return {
        "lecture_id": lecture_id,
        "filename": file.filename,
        "page_count": len(pages),
        "language": detect_document_language(pages),
        "empty_pages": empty_pages,
        "pages": [
            {
                "page_number": p["page_number"],
                "language": p["language"],
                "characters": len(p["cleaned_text"]),
                "preview": p["cleaned_text"][:150],
            }
            for p in pages
        ],
    }