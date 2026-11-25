import importlib
import sys

# (display name, import name)
PACKAGES = [
    ("FastAPI", "fastapi"),
    ("Uvicorn", "uvicorn"),
    ("python-multipart", "multipart"),
    ("Pydantic", "pydantic"),
    ("python-dotenv", "dotenv"),
    ("PyMuPDF", "pymupdf"),
    ("Sentence Transformers", "sentence_transformers"),
    ("ChromaDB", "chromadb"),
    ("SQLAlchemy", "sqlalchemy"),
    ("psycopg2", "psycopg2"),
    ("NumPy", "numpy"),
    ("Pandas", "pandas"),
    ("pytest", "pytest"),
    ("httpx", "httpx"),
    ("ipykernel", "ipykernel"),
]

print(f"Python {sys.version.split()[0]}\n")

failed = []
for name, module in PACKAGES:
    try:
        importlib.import_module(module)
        print(f"[OK]    {name}")
    except Exception as error:
        print(f"[FAIL]  {name} -> {error}")
        failed.append(name)

print()
if failed:
    print("Missing:", ", ".join(failed))
else:
    print("Everything is installed correctly.")