import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent  # folder this script lives in

# DOCLING_DATA_DIR lets this be overridden (e.g. to /data inside a Docker
# container, where a user's own folder gets mounted). Defaults to this
# project's own data/ folder for local development.
DATA_DIR = Path(os.environ.get("DOCLING_DATA_DIR", BASE_DIR / "data"))
DB_PATH = DATA_DIR / "lancedb"

# File types build_index will pick up. All of these work with Docling
# out of the box -- no extra system dependencies required.
SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".html",
    ".htm",
    ".md",
    ".csv",
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".bmp",
    ".webp",
}
EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_MAX_TOKENS = 512  # target chunk size for retrieval, not the model's hard limit

# Whether to run OCR on PDFs. Defaults to on (correct for scanned PDFs with
# no real text layer), but OCR is the slowest part of ingestion by far and
# is wasted work on digitally-born PDFs that already have selectable text
# (e.g. most modern financial filings). If you know your PDFs are all
# digitally-born, set DOCLING_PDF_DO_OCR=false for a large speedup.
# Note: this only affects the PDF pipeline -- plain image files (.png/.jpg/
# etc.) always get OCR, since it's the only way to extract text from them.
PDF_DO_OCR = os.environ.get("DOCLING_PDF_DO_OCR", "true").lower() == "true"

client = OpenAI()
