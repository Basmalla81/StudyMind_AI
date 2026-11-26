import json
import sys

from processing import process_lecture, LectureProcessingError


pdf_path = sys.argv[1] if len(sys.argv) > 1 else "Computational Models.pdf"
lecture_id = sys.argv[2] if len(sys.argv) > 2 else "demo"

try:
    result = process_lecture(pdf_path, lecture_id)
except LectureProcessingError as error:
    sys.exit(f"Failed: {error}")

output_path = f"{lecture_id}_chunks.json"

with open(output_path, "w", encoding="utf-8") as output:
    json.dump(result["chunks"], output, ensure_ascii=False, indent=2)

sizes = [c["word_count"] for c in result["chunks"]]
print(f"Language: {result['language']} | Pages: {result['page_count']} "
      f"| Empty pages: {result['empty_pages'] or 'none'}")
print(f"Saved {len(sizes)} chunks to {output_path} "
      f"(words per chunk: min {min(sizes)}, max {max(sizes)})")