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

## Step-by-step install guide (no technical background required)

This walks through everything from scratch — you don't need to know how to
code. You will need to type a couple of commands into a command-line program
(**Terminal** on Mac, **Command Prompt** on Windows) — that's unavoidable,
but every command you need is given below to copy and paste exactly as
written. Steps below are labeled **Mac** / **Windows** wherever they differ.

Budget about 20-30 minutes for first-time setup, most of it waiting for
downloads.

### 1. Install Docker Desktop

Docker is the program that runs this app without you needing to install
Python or any other developer tools yourself. Same for both operating
systems:

1. Go to [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
   and download Docker Desktop for your computer (it'll detect Mac vs.
   Windows automatically).
2. Install it like any other application (Mac: open the downloaded file and
   drag it to Applications; Windows: run the downloaded installer and
   follow the prompts — it may ask to restart your computer).
3. Open Docker Desktop and wait for it to say it's running. **Leave it open**
   in the background — the app won't work if Docker Desktop is closed.

### 2. Get an OpenAI API key

This app uses OpenAI to understand your documents and answer questions. This
is separate from a ChatGPT subscription — it's billed per use, based on how
much you actually ask it to do (check current pricing at
[platform.openai.com/docs/pricing](https://platform.openai.com/docs/pricing);
for personal use, indexing and asking questions typically costs a small
fraction of a dollar per session). Same steps on both operating systems:

1. Go to [platform.openai.com](https://platform.openai.com) and sign up or
   log in.
2. Add a payment method under **Settings → Billing** (required before the
   API will work).
3. Go to **API keys** (under Settings, or directly at
   [platform.openai.com/api-keys](https://platform.openai.com/api-keys)) and
   click **Create new secret key**.
4. Copy the key immediately and paste it somewhere safe (like a notes app) —
   OpenAI only shows it to you once.

### 3. Download this project

Same steps on both operating systems:

1. Go to this project's GitHub page.
2. Click the green **Code** button, then **Download ZIP**.
3. Find the downloaded ZIP file (usually in your Downloads folder) and
   double-click it to unzip it.
4. Move the resulting folder somewhere you'll remember, e.g. your Desktop.

### 4. Open a command line and navigate to the folder

**Mac:**

1. Press `Cmd + Space` to open Spotlight, type `Terminal`, and press Enter.
2. Type `cd ` (with a trailing space), then drag the project folder from
   Finder directly into the Terminal window — this automatically fills in
   the correct path. Press Enter.

**Windows:**

1. Click the Start menu, type `Command Prompt`, and press Enter.
2. Type `cd ` (with a trailing space), then drag the project folder from
   File Explorer directly into the Command Prompt window to fill in the
   path automatically. Press Enter.

### 5. Add your API key

In the command-line window (still in the project folder):

**Mac** — paste and press Enter:

```
cp .env.example .env
```

**Windows** — paste and press Enter:

```
copy .env.example .env
```

Now open the new `.env` file in a plain text editor. On Mac: in Finder,
right-click it → **Open With** → **TextEdit**. On Windows: in File Explorer,
right-click it → **Open with** → **Notepad**.

(Mac note: files starting with a `.` are hidden by Finder by default — press
`Cmd + Shift + .` to reveal them if you don't see `.env` or `.env.example`.
Windows shows these files normally, no extra step needed.)

The file contains one line:

```
OPENAI_API_KEY=
```

Paste your API key from step 2 right after the `=` (no spaces, no quotes),
then save and close the file.

### 6. Add your documents

Open the project folder (Finder on Mac, File Explorer on Windows). There's
no `data` folder yet — create a new folder here and name it exactly `data`.
Then drag and drop whatever PDFs, Word documents, PowerPoint files,
spreadsheets, or similar files you want to ask questions about into it.

### 7. Start the app

Make sure Docker Desktop (from step 1) is open, then back in your
command-line window, run:

```
docker compose up --build
```

A lot of text will scroll by — that's normal. The first time you run this,
it downloads and installs everything the app needs, which can take several
minutes. Once it settles down and stops scrolling rapidly, the app itself is
running — but it hasn't looked at your documents yet.

### 8. Open the app

Open your web browser and go to:

```
http://localhost:8501
```

Opening this page is what actually tells the app to read the documents in
your `data` folder — you'll see an "Indexing documents..." message while it
works through them. For a first run with several documents, or large ones,
this can take a few minutes; the terminal window will keep scrolling with
progress while it happens. Once it finishes, you'll see the text box to ask
questions.

### 9. Stopping the app

Go back to the command-line window and press `Control + C`. You can start
it again anytime by repeating step 7 (it'll be much faster the second time).

### 10. Adding more documents later

Drag new files into the `data` folder, then either click **Check for new
files** in the app's sidebar, or just stop and restart the app (step 7 then
8). Only the new files get processed — everything already indexed is left
alone.
