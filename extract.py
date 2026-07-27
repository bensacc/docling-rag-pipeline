from pathlib import Path
from dotenv import load_dotenv
from docling.chunking import HybridChunker
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer
from docling_core.transforms.chunker.base import BaseChunk
from docling_core.types.doc import DoclingDocument
from openai import OpenAI
import tiktoken
from config import (
    DATA_DIR,
    EMBEDDING_MODEL,
    CHUNK_MAX_TOKENS,
    SUPPORTED_EXTENSIONS,
    PDF_DO_OCR,
    client,
)
from db import load_db, get_processed_sources


def get_converter() -> DocumentConverter:
    # Only the PDF pipeline's OCR setting is configurable -- image formats
    # (.png/.jpg/etc.) always need OCR to extract any text at all, so their
    # pipeline is left on its default regardless of PDF_DO_OCR.
    pdf_options = PdfPipelineOptions()
    pdf_options.do_ocr = PDF_DO_OCR
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)}
    )


def convert_document(path: Path, converter: DocumentConverter) -> DoclingDocument:
    print(f"Converting {path.name} ...")
    result = converter.convert(path)
    return result.document


def get_chunker() -> HybridChunker:
    tokenizer = OpenAITokenizer(
        tokenizer=tiktoken.encoding_for_model(EMBEDDING_MODEL),
        max_tokens=CHUNK_MAX_TOKENS,
    )
    return HybridChunker(tokenizer=tokenizer)


def chunk_document(doc: DoclingDocument, chunker: HybridChunker) -> list[BaseChunk]:
    return list(chunker.chunk(dl_doc=doc))


def embed_chunks(chunk_list: list, client: OpenAI):
    for i in range(0, len(chunk_list), 100):
        chunk_batch = chunk_list[i : i + 100]
        embed_text = [d.get("embedding_text") for d in chunk_batch]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=embed_text)
        for chunk_dict, item in zip(chunk_batch, response.data):
            chunk_dict["embedding"] = item.embedding


def build_index(data_dir: Path):
    db_path = data_dir / "lancedb"

    processed = get_processed_sources(db_path)
    files = [
        f
        for f in data_dir.iterdir()
        if f.is_file()
        and f.suffix.lower() in SUPPORTED_EXTENSIONS
        and f.name not in processed
    ]
    if not files:
        print("No new files to process.")
        return

    converter = get_converter()
    chunker = get_chunker()

    for file in files:
        # convert this file to a DoclingDocument
        doc = convert_document(file, converter)
        print(f"Pages: {doc.num_pages()}")

        # chunk the parsed document, using a tokenizer that matches
        # the OpenAI embedding model we'll use later.
        chunks = chunk_document(doc, chunker)
        print(f"Chunks: {len(chunks)}")

        # create list of chunks, metadata plus raw and contextualized text
        # we want contextualized text to facilitate the subsequent interactive query steps
        chunk_list = [
            {
                "source": file.name,
                "text": chunk.text,
                "headings": chunk.meta.headings or [],
                "embedding_text": chunker.contextualize(chunk),
                "pages": sorted(
                    {
                        prov.page_no
                        for item in chunk.meta.doc_items
                        for prov in item.prov
                    }
                ),
            }
            for chunk in chunks
        ]

        # embed and commit this file's chunks immediately, rather than
        # accumulating every file in memory and writing once at the very
        # end -- so a crash or interruption partway through only costs the
        # one file in progress, not the whole run, and doesn't hold
        # everything indexed so far only in RAM.
        embed_chunks(chunk_list, client)
        load_db(chunk_list, db_path)
        print(f"Saved {file.name} ({len(chunk_list)} chunks) to the index.\n")


if __name__ == "__main__":
    build_index(DATA_DIR)
