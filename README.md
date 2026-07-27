# Docling RAG Pipeline

Point this at a directory of documents, ask it questions in plain English, get
answers grounded in — and cited back to — the actual source files.

Built and tested against several years of NVIDIA's annual reports (10-Ks), but
the pipeline itself is general-purpose: it works over whatever documents you
put in the directory, not just financial filings.

## How it works

1. **Parse** — [Docling](https://docling-project.github.io/docling/) converts
   each document (PDF, Word, PowerPoint, Excel, HTML, Markdown, CSV, or image)
   into a structured representation that understands headings, reading order,
   and — critically for anything with financial tables — actual table
   structure, not just a wall of scrambled text.
2. **Chunk** — Each document is split into retrieval-sized chunks using
   Docling's `HybridChunker`, tagged with the section heading(s) and page
   number(s) each chunk came from.
3. **Embed** — Every chunk is turned into a vector via OpenAI's
   `text-embedding-3-small`, using each chunk's heading-prefixed
   ("contextualized") text so the embedding captures what section a chunk
   belongs to, not just its raw content.
4. **Store** — Chunks, metadata, and embeddings are written to a local
   [LanceDB](https://lancedb.github.io/lancedb/) database, co-located with
   the source documents (`<your directory>/lancedb`) so the index travels
   with the files it was built from.
5. **Retrieve** — A question is embedded the same way, and LanceDB's vector
   search finds the most relevant chunks across every indexed document. The
   number of chunks retrieved scales with how many documents are indexed, so
   a question spanning many years/files has a better chance of pulling in
   the right chunk from each one.
6. **Answer** — The retrieved chunks (with their source file and page
   numbers) are handed to an LLM, instructed to answer only from what it was
   given and to say so if the answer isn't fully supported by the retrieved
   context.

Re-running the ingestion step only processes files that haven't been indexed
yet — it won't reprocess or duplicate documents that are already in the
database.

## Project structure

| File                  | Purpose                                                              |
| --------------------- | --------------------------------------------------------------------- |
| `config.py`            | Shared settings: data directory, model names, the OpenAI client       |
| `db.py`                | LanceDB schema (`Chunk`) and connection helpers                       |
| `extract.py`           | Ingestion pipeline: parse → chunk → embed → store (`build_index`)     |
| `query.py`             | Retrieval + answer generation (`answer_question`)                     |
| `app.py`               | Streamlit UI                                                          |
| `Dockerfile`           | Container image definition                                            |
| `docker-compose.yml`   | Convenience wrapper for running the container                         |
| `.env.example`         | Template for the required environment variables                       |

## Setup

You'll need an OpenAI API key either way — copy `.env.example` to `.env` and
fill it in:

```
cp .env.example .env
```

### Option A: Run locally with uv

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```
uv sync
uv run streamlit run app.py
```

By default this reads/writes documents in this project's own `data/` folder.
To point it at a different folder instead, set `DOCLING_DATA_DIR` before
running:

```
DOCLING_DATA_DIR=/path/to/your/folder uv run streamlit run app.py
```

You can also run the ingestion and query steps directly from the command
line, without the UI:

```
uv run python extract.py   # builds/updates the index for DATA_DIR
uv run python query.py     # asks a hardcoded test question against it
```

### Option B: Run with Docker

Requires [Docker](https://www.docker.com/) — no local Python setup needed.

```
docker compose up --build
```

This uses this project's own `data/` folder by default. To point it at a
different folder on your machine:

```
DOCLING_DATA_DIR=/path/to/your/folder docker compose up --build
```

Either way, open **http://localhost:8501** once it's running.

The first build will take a while (installing Docling, PyTorch, LanceDB, and
their dependencies). The first time it actually processes a document, Docling
also downloads its layout/OCR models over the network — a one-time cost per
container image.

## Usage

Type a question into the text box and click **Ask**. The answer appears
below, followed by a collapsible **Sources** section listing exactly which
document(s), and page(s), the answer was drawn from — so you can verify any
fact against the original source rather than trusting the LLM's prose alone.

A **Check for new files** button in the sidebar lets you re-index on demand
(e.g. after dropping new documents into the folder) without restarting the
app — this is fast if nothing's actually new, since already-indexed files are
skipped automatically.

## Supported file types

PDF, DOCX, PPTX, XLSX, HTML, Markdown, CSV, and common image formats (PNG,
JPEG, TIFF, BMP, WEBP) — all work with no extra system dependencies. See
`SUPPORTED_EXTENSIONS` in `config.py` to adjust.

Legacy Office formats (`.doc`, `.xls`, `.ppt`) are supported by Docling but
require LibreOffice installed on the system and aren't enabled here by
default, to keep the dependency footprint (and Docker image size) smaller.

## Configuration

| Variable            | Required | Default                | Purpose                                                        |
| -------------------- | -------- | ----------------------- | ---------------------------------------------------------------- |
| `OPENAI_API_KEY`      | Yes      | —                        | Used for both embeddings and answer generation                  |
| `DOCLING_DATA_DIR`    | No       | this project's `data/`  | Directory containing the documents to index (and where the LanceDB index is stored, as `<dir>/lancedb`) |

## Notes on design decisions

- **The index lives inside the data directory**, not in a separate fixed
  location. This keeps a directory of documents and its index portable and
  self-contained — copy or move the folder, and the index comes with it.
- **Retrieval scales with corpus size** (`k` = number of indexed documents,
  not a fixed number) so questions spanning many documents aren't
  bottlenecked by a small, fixed number of retrieved chunks.
- **Indexing is incremental**: re-running it only processes files whose
  filenames aren't already recorded in the database, so adding one new file
  to a directory of hundreds doesn't mean reprocessing everything.
