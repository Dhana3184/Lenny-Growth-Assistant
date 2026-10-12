from pathlib import Path

import chromadb
import requests


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHROMA_PATH = PROJECT_ROOT / "data" / "chroma_db"

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text:latest"
COLLECTION_NAME = "lenny_transcripts"


def embed_question(question: str) -> list[float]:
    """Convert the question into an embedding using Ollama."""
    response = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={
            "model": EMBED_MODEL,
            "input": [question],
        },
        timeout=120,
    )
    response.raise_for_status()

    embeddings = response.json()["embeddings"]

    if not embeddings:
        raise RuntimeError("Ollama returned no embeddings.")

    return embeddings[0]


def search_transcripts(question: str, top_k: int = 5):
    """Retrieve the most relevant podcast transcript passages."""
    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH)
    )

    collection = client.get_collection(COLLECTION_NAME)

    if collection.count() == 0:
        raise RuntimeError("The transcript collection is empty.")

    query_embedding = embed_question(question)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    print(f"\nQuestion: {question}")
    print(f"Results found: {len(results['documents'][0])}")

    for index, document in enumerate(results["documents"][0]):
        metadata = results["metadatas"][0][index]
        distance = results["distances"][0][index]

        print(f"\n--- Result {index + 1} ---")
        print(f"Episode: {metadata.get('title', 'Unknown')}")
        print(f"Guest: {metadata.get('guest', 'Unknown')}")
        print(f"Distance: {distance:.4f}")
        print(f"Source: {metadata.get('youtube_url', 'Unavailable')}")
        print(f"Passage:\n{document[:900]}")


if __name__ == "__main__":
    question = input("Enter a podcast-related question: ").strip()

    if not question:
        print("Please enter a question.")
    else:
        search_transcripts(question)