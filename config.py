from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# PDFs live in a sibling folder to this project.
BASE_DIR = Path(__file__).resolve().parent  # folder this script lives in
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "lancedb"
EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_MAX_TOKENS = 512  # target chunk size for retrieval, not the model's hard limit

client = OpenAI()
