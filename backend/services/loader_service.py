import json
import logging
from dataclasses import dataclass
from pathlib import Path

from config import SOURCES_MANIFEST

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Document:
    name: str            # file name without .txt, e.g. "mplus_hemoglobin_test"
    title: str           # readable title, e.g. "Hemoglobin Test"
    url: str             # where it came from ("" for our own notes)
    source: str          # who to credit
    text: str


def _load_manifest() -> dict:
    """data/sources.json: title, url and credit for every downloaded document."""

    try:
        return json.loads(Path(SOURCES_MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def load_documents(folder_path):
    """Read every .txt knowledge file in a folder (sorted, so the order is
    deterministic) together with its title and source."""

    manifest = _load_manifest()
    documents = []

    for path in sorted(Path(folder_path).glob("*.txt")):

        text = path.read_text(encoding="utf-8").strip()

        if not text:
            continue

        info = manifest.get(path.name, {})

        documents.append(Document(
            name=path.stem,
            title=info.get("title") or path.stem.replace("_", " ").title(),
            url=info.get("url", ""),
            source=info.get("source", "AuraHealth notes"),
            text=text,
        ))

    logger.info("%d knowledge documents loaded from %s.", len(documents), folder_path)

    return documents
