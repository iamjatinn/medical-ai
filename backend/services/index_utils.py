import hashlib
import json
from pathlib import Path

from config import CHUNK_OVERLAP, CHUNK_SIZE, EMBEDDING_BACKEND, EMBEDDING_MODEL


def knowledge_fingerprint(folder: Path) -> str:
    """Hash of everything that decides what the vector index contains:
    the knowledge files, the chunking settings and the embedding model.
    If any of them change, the saved index is stale and must be rebuilt."""

    digest = hashlib.sha256()

    digest.update(f"{EMBEDDING_BACKEND}|{EMBEDDING_MODEL}|{CHUNK_SIZE}|{CHUNK_OVERLAP}".encode())

    for path in sorted(Path(folder).glob("*.txt")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())

    return digest.hexdigest()


def read_saved_fingerprint(meta_path: Path):

    try:
        with open(meta_path, "r", encoding="utf-8") as file:
            return json.load(file).get("fingerprint")
    except (OSError, ValueError):
        return None


def write_fingerprint(meta_path: Path, fingerprint: str, chunk_count: int):

    meta_path = Path(meta_path)
    meta_path.parent.mkdir(parents=True, exist_ok=True)

    with open(meta_path, "w", encoding="utf-8") as file:
        json.dump(
            {"fingerprint": fingerprint, "chunks": chunk_count},
            file,
            indent=2,
        )


def knowledge_base_changed(meta_path: Path, current_fingerprint: str) -> bool:

    return read_saved_fingerprint(meta_path) != current_fingerprint
