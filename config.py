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

client = OpenAI()
