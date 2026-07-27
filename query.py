from config import EMBEDDING_MODEL, CHUNK_MAX_TOKENS, client
from db import get_table
import json


def embed_query(question: str) -> list[float]:
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=[question])
    return response.data[0].embedding


def retrieve_answer(question: str, k: int = 5) -> list:
    table = get_table()
    query_vector = embed_query(question)
    return table.search(query_vector).limit(k).to_list()


def answer_question(question: str):
    results = retrieve_answer(question)
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

    return response.output_text


if __name__ == "__main__":
    question = "how has revenue changed from 2024 to 2026?"
    result = answer_question(question)
    print(result)
