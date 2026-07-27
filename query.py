from pathlib import Path
import json
from config import EMBEDDING_MODEL, DB_PATH, client
from db import get_table, get_processed_sources


def embed_query(question: str) -> list[float]:
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=[question])
    return response.data[0].embedding


def retrieve_answer(db_path: Path, question: str, k: int = 5) -> list:
    table = get_table(db_path)
    query_vector = embed_query(question)
    return table.search(query_vector).limit(k).to_list()


def answer_question(db_path: Path, question: str):
    file_count = len(get_processed_sources(db_path))
    results = retrieve_answer(db_path=db_path, question=question, k=file_count)
    context = [
        f"[Source: {item['source']}, page(s) {item['pages']}]\n{item['text']}"
        for item in results
    ]
    instructions = (
        f"Use the supplied text entries to answer this question: {question}\n\n"
        "Combine overlapping information and remove repetition. "
        "Do not add facts that are not present in the supplied entries. "
        "If the entries do not contain enough information, say so."
    )

    response = client.responses.create(
        model="gpt-5.6-terra", instructions=instructions, input=json.dumps(context)
    )

    return response.output_text, results


if __name__ == "__main__":
    question = "how has revenue changed from 2021 to 2026?"
    answer, sources = answer_question(DB_PATH, question)
    print(answer)
    print("\nSources:")
    for r in sources:
        print(f"  {r['source']} — page(s) {r['pages']}")
