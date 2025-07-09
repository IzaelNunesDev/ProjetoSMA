from pathlib import Path

def _is_path_safe(file_path: Path, base_dir: Path) -> bool:
    """
    Verifica se file_path está dentro de base_dir (protege contra path traversal).
    """
    try:
        return base_dir in file_path.resolve().parents or file_path.resolve() == base_dir.resolve()
    except Exception:
        return False 