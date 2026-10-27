from src.rag.embedding_store import TenderVectorStore


store = TenderVectorStore()

print("=" * 60)
print("VECTOR DATABASE CHECK")
print("=" * 60)

count = store.collection.count()

print(f"\nTotal chunks in Chroma: {count}")

results = store.collection.get(
    include=["documents", "metadatas"]
)

documents = results.get("documents", [])
metadatas = results.get("metadatas", [])
ids = results.get("ids", [])

print("\nSearching stored chunks for:")
print("proposal / validity / 180 days")
print("=" * 60)

found = False

for i, document in enumerate(documents):

    text = str(document)

    if (
        "proposal" in text.lower()
        or "validity" in text.lower()
        or "180 days" in text.lower()
    ):

        found = True

        print(f"\nChunk ID: {ids[i]}")

        if i < len(metadatas):
            print("Metadata:")
            print(metadatas[i])

        print("\nText:")
        print(text)

        print("-" * 60)


if not found:
    print(
        "\nNO stored chunk contains "
        "'proposal', 'validity', or '180 days'."
    )