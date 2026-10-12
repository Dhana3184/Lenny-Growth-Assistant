import hashlib
import os
import re
from pathlib import Path

import chromadb
import requests
import yaml


# Project configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent

TRANSCRIPT_ROOT = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "lennys-growth-placeholder"
)

# Use the actual repository folder downloaded earlier.
TRANSCRIPT_ROOT = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "lennys-podcast-transcripts"
)

CHROMA_PATH = PROJECT_ROOT / "data" / "chroma_db"

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
).rstrip("/")

EMBED_MODEL = os.getenv(
    "OLLAMA_EMBED_MODEL",
    "nomic-embed-text:latest",
)

COLLECTION_NAME = "lenny_transcripts"

CHUNK_SIZE = 2200
CHUNK_OVERLAP = 250
BATCH_SIZE = 16


def read_transcript(path: Path):
    """Read YAML metadata and the Markdown transcript body."""
    raw_text = path.read_text(
        encoding="utf-8",
        errors="replace",
    ).lstrip("\ufeff")

    metadata = {}
    body = raw_text

    if raw_text.startswith("---"):
        parts = raw_text.split("---", 2)

        if len(parts) == 3:
            try:
                parsed = yaml.safe_load(parts[1])
                if isinstance(parsed, dict):
                    metadata = parsed
                body = parts[2].strip()
            except yaml.YAMLError as exc:
                print(
                    f"Warning: Could not parse metadata in "
                    f"{path.name}: {exc}"
                )

    return metadata, body


def metadata_value(metadata, key, fallback):
    """Return a safe, non-empty string from episode metadata."""
    value = metadata.get(key)

    if value is None:
        return fallback

    if isinstance(value, list):
        value = ", ".join(str(item) for item in value)

    if isinstance(value, dict):
        return fallback

    value = str(value).strip()
    return value if value else fallback


def split_into_chunks(text):
    """Split text into overlapping, approximately equal-size chunks."""
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))

        if end < len(text):
            search_start = start + CHUNK_SIZE // 2
            paragraph_boundary = text.rfind(
                "\n\n", search_start, end
            )
            line_boundary = text.rfind(
                "\n", search_start, end
            )

            boundary = max(
                paragraph_boundary,
                line_boundary,
            )

            if boundary > search_start:
                end = boundary

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(start + 1, end - CHUNK_OVERLAP)

    return chunks


def create_embeddings(texts):
    """Generate local embeddings using Ollama."""
    endpoint = f"{OLLAMA_BASE_URL}/api/embed"

    try:
        response = requests.post(
            endpoint,
            json={
                "model": EMBED_MODEL,
                "input": texts,
            },
            timeout=(10, 180),
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Could not contact Ollama at {endpoint}. "
            "Check that Ollama is running and the embedding "
            f"model '{EMBED_MODEL}' is installed."
        ) from exc

    embeddings = response.json().get("embeddings")

    if not isinstance(embeddings, list):
        raise RuntimeError(
            "Ollama did not return an embeddings list."
        )

    if len(embeddings) != len(texts):
        raise RuntimeError(
            "The number of embeddings does not match "
            "the number of input texts."
        )

    return embeddings


def main():
    if not TRANSCRIPT_ROOT.is_dir():
        raise FileNotFoundError(
            f"Transcript repository not found: {TRANSCRIPT_ROOT}"
        )

    transcript_files = sorted(
        TRANSCRIPT_ROOT.rglob("transcript.md")
    )

    if not transcript_files:
        raise FileNotFoundError(
            "No transcript.md files were found in "
            f"{TRANSCRIPT_ROOT}"
        )

    print(
        f"Found {len(transcript_files)} transcript files."
    )
    print(f"Using embedding model: {EMBED_MODEL}")
    print("Starting transcript indexing...")

    CHROMA_PATH.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH)
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    ids = []
    documents = []
    metadatas = []
    indexed_this_run = 0
    skipped_files = 0

    def flush_batch():
        nonlocal indexed_this_run

        if not ids:
            return

        embeddings = create_embeddings(documents)

        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        indexed_this_run += len(ids)

        ids.clear()
        documents.clear()
        metadatas.clear()

    for file_number, path in enumerate(
        transcript_files, start=1
    ):
        episode, transcript = read_transcript(path)

        if not transcript.strip():
            skipped_files += 1
            continue

        relative_path = path.relative_to(
            TRANSCRIPT_ROOT
        ).as_posix()

        guest = metadata_value(
            episode, "guest", "Unknown guest"
        )
        title = metadata_value(
            episode, "title", path.parent.name
        )
        source_url = metadata_value(
            episode, "youtube_url", "Not provided"
        )
        video_id = metadata_value(
            episode, "video_id", "Unknown"
        )
        publish_date = metadata_value(
            episode, "publish_date", "Unknown"
        )

        chunks = split_into_chunks(transcript)

        for chunk_number, chunk in enumerate(chunks):
            # Include episode details in the searchable text.
            document = (
                f"Episode: {title}\n"
                f"Guest: {guest}\n"
                f"Transcript passage:\n{chunk}"
            )

            unique_key = (
                f"{relative_path}|{chunk_number}"
            )

            chunk_id = hashlib.sha1(
                unique_key.encode("utf-8")
            ).hexdigest()

            ids.append(chunk_id)
            documents.append(document)

            metadatas.append(
                {
                    "guest": guest[:200],
                    "title": title[:500],
                    "youtube_url": source_url[:1000],
                    "video_id": video_id[:100],
                    "publish_date": publish_date[:100],
                    "source_file": relative_path,
                    "chunk_index": chunk_number,
                }
            )

            if len(ids) >= BATCH_SIZE:
                flush_batch()

        if file_number % 25 == 0:
            print(
                f"Scanned {file_number}/"
                f"{len(transcript_files)} transcripts; "
                f"indexed {indexed_this_run} chunks."
            )

    # Index the final, smaller batch.
    flush_batch()

    print("\nIndexing completed.")
    print(f"Transcript files found: {len(transcript_files)}")
    print(f"Empty files skipped: {skipped_files}")
    print(f"Chunks indexed this run: {indexed_this_run}")
    print(f"Total chunks in collection: {collection.count()}")
    print(f"Vector database: {CHROMA_PATH}")


if __name__ == "__main__":
    main()