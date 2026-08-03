from pathlib import Path


def knowledge_base_changed(index_path: Path) -> bool:

    return not index_path.exists()