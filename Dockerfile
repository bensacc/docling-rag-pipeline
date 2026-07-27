FROM python:3.13-slim

# Shared libraries some of Docling's OCR/vision dependencies need at import
# time (rapidocr's torch backend, opencv, etc.) that aren't in the slim image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

# Install dependencies first, separately from app code, so this layer is
# cached and only re-runs when pyproject.toml/uv.lock actually change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Now the actual application code.
COPY config.py db.py extract.py query.py app.py ./

# A user's own folder of PDFs (and the LanceDB index built from them) gets
# mounted here at `docker run` time, e.g. -v ~/my-reports:/data
ENV DOCLING_DATA_DIR=/data
VOLUME ["/data"]

# PyTorch (used internally by Docling) often detects the *host* machine's
# full CPU count from inside a container rather than what Docker actually
# allocated to it, and spins up too many threads as a result -- they end up
# contending for the same handful of real cores instead of doing useful
# work, which slows down ingestion. Pin this explicitly; override at
# `docker run`/compose time (-e OMP_NUM_THREADS=N) to match your own
# Docker Desktop CPU allocation (Settings -> Resources) for best performance.
ENV OMP_NUM_THREADS=4
ENV MKL_NUM_THREADS=4

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
