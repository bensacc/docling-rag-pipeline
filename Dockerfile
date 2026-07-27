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

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
