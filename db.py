import lancedb
from lancedb.pydantic import LanceModel, Vector
from config import DB_PATH

TABLE_NAME = "chunks"
DB = lancedb.connect(DB_PATH)


class Chunk(LanceModel):
    source: str
    text: str
    headings: list[str]
    pages: list[int]
    embedding: Vector(1536)
    embedding_text: str


def load_db(chunk_list: list):
    if TABLE_NAME in DB.table_names():
        table = DB.open_table(TABLE_NAME)
        table.add(chunk_list, mode="append")
    else:
        table = DB.create_table(TABLE_NAME, data=chunk_list, schema=Chunk)
    return table


def get_table():
    return DB.open_table(TABLE_NAME)
