import json
from pathlib import Path

from src.rag.embedding_store import (
    TenderVectorStore
)


# --------------------------------
# Load processed tender JSON
# --------------------------------

json_path = Path(
    "data/processed/tender_001_pdf.json"
)

with open(
    json_path,
    "r",
    encoding="utf-8"
) as file:

    pdf_data = json.load(file)


# --------------------------------
# Get previously created chunks
# --------------------------------

chunks = pdf_data[
    "rag_chunks"
]


print(
    "Chunks loaded:",
    len(chunks)
)


# --------------------------------
# Initialize vector database
# --------------------------------

vector_store = TenderVectorStore()


# --------------------------------
# Add chunks to Chroma
# --------------------------------

vector_store.add_chunks(
    chunks
)

print(
    "Chunks stored in vector database."
)


# --------------------------------
# Test semantic search
# --------------------------------

question = (
    "What is the penalty "
    "if the contractor delays the work?"
)

print(
    "\nQuestion:",
    question
)


results = vector_store.search(
    question,
    top_k=3
)


# --------------------------------
# Display results
# --------------------------------

documents = results[
    "documents"
][0]

metadatas = results[
    "metadatas"
][0]

distances = results[
    "distances"
][0]


print(
    "\nRetrieved Chunks:"
)


for index in range(
    len(documents)
):

    print(
        "\n--------------------"
    )

    print(
        "Rank:",
        index + 1
    )

    print(
        "Section:",
        metadatas[index][
            "section_number"
        ],
        "-",
        metadatas[index][
            "section_title"
        ]
    )

    print(
        "Page:",
        metadatas[index][
            "page_number"
        ]
    )

    print(
        "Distance:",
        distances[index]
    )

    print(
        "Text:",
        documents[index]
    )