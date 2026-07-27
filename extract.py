from pathlib import Path
from dotenv import load_dotenv
from docling.chunking import HybridChunker
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer
from docling_core.transforms.chunker.base import BaseChunk
from docling_core.types.doc import DoclingDocument
from openai import OpenAI
import tiktoken
from config import (
    DATA_DIR,
    EMBEDDING_MODEL,
    CHUNK_MAX_TOKENS,
    client,
)
from db import load_db


def convert_pdf(pdf_path: Path) -> DoclingDocument:
    converter = DocumentConverter()
    print(f"Converting {pdf_path.name} ...")
    result = converter.convert(pdf_path)
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


def main():
    # prove Docling conversion works, on the smallest file first.
    files = DATA_DIR.glob("*.pdf")

    chunker = get_chunker()
    chunk_list = []
    for file in files:
        # convert pdf files to DoclingDocument object/documents
        doc = convert_pdf(file)
        print(f"Pages: {doc.num_pages()}")

        # chunk the parsed document, using a tokenizer that matches
        # the OpenAI embedding model we'll use later.
        chunks = chunk_document(doc, chunker)
        print(f"\nChunks: {len(chunks)}")

        # create list of chunks, metadata plus raw and contextualized text
        # we want contextualized text to facilitate the subsequent intreactive query steps
        for chunk in chunks:
            chunk_list.append(
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
            )
    # embed chunks along with contextualized metadata
    embed_chunks(chunk_list, client)
    # test
    # chunk_list[0]["embedding"]
    load_db(chunk_list)


if __name__ == "__main__":
    main()
