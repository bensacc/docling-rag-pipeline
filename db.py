from pathlib import Path

import lancedb
from lancedb.pydantic import LanceModel, Vector

TABLE_NAME = "chunks"


class Chunk(LanceModel):
    source: str
    text: str
    headings: list[str]
    pages: list[int]
    embedding: Vector(1536)
    embedding_text: str


def load_db(chunk_list: list, db_path: Path):
    db = lancedb.connect(db_path)
    if TABLE_NAME in db.list_tables().tables:
        table = db.open_table(TABLE_NAME)
        table.add(chunk_list, mode="append")
    else:
        table = db.create_table(TABLE_NAME, data=chunk_list, schema=Chunk)
    return table


def get_table(db_path: Path):
    db = lancedb.connect(db_path)
    return db.open_table(TABLE_NAME)


def get_processed_sources(db_path: Path) -> set[str]:
    """Return the set of source filenames already stored in the table.

    Empty set if the table doesn't exist yet (i.e. nothing's been indexed).
    """
    db = lancedb.connect(db_path)
    if TABLE_NAME not in db.list_tables().tables:
        return set()
    table = db.open_table(TABLE_NAME)
    return set(table.to_pandas()["source"].unique())
