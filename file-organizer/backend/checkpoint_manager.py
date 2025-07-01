import os
import shutil
import hashlib
from pathlib import Path
from typing import List
from datetime import datetime

try:
    import git
except ImportError:
    git = None

class CheckpointManager:
    @staticmethod
    def get_shadow_repo_path(directory_path: str) -> Path:
        hash_dir = hashlib.sha1(directory_path.encode()).hexdigest()
        return Path.home() / ".projetosma" / "history" / hash_dir

    @staticmethod
    def create_checkpoint(directory_path: str) -> str:
        """
        Cria um snapshot do diretório em um repositório git sombra.
        Retorna o hash do commit criado.
        """
        if git is None:
            raise ImportError("GitPython não está instalado. Instale com 'pip install gitpython'.")
        src = Path(directory_path).resolve()
        shadow_repo = CheckpointManager.get_shadow_repo_path(str(src))
        shadow_repo.mkdir(parents=True, exist_ok=True)

        # Copiar conteúdo do diretório para o repositório sombra (exceto .git)
        for item in src.iterdir():
            if item.name == ".git":
                continue
            dest = shadow_repo / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        # Inicializar repositório git se necessário
        if not (shadow_repo / ".git").exists():
            repo = git.Repo.init(shadow_repo)
        else:
            repo = git.Repo(shadow_repo)

        repo.git.add(A=True)
        commit_msg = f"Checkpoint: {datetime.now().isoformat()}"
        commit = repo.index.commit(commit_msg)
        return commit.hexsha

    @staticmethod
    def list_checkpoints(directory_path: str) -> List[dict]:
        """
        Lista os commits (checkpoints) do repositório sombra.
        """
        if git is None:
            raise ImportError("GitPython não está instalado. Instale com 'pip install gitpython'.")
        shadow_repo = CheckpointManager.get_shadow_repo_path(directory_path)
        if not (shadow_repo / ".git").exists():
            return []
        repo = git.Repo(shadow_repo)
        return [
            {"hash": c.hexsha, "msg": c.message, "date": c.committed_datetime.isoformat()}
            for c in repo.iter_commits()
        ]

    @staticmethod
    def restore_checkpoint(directory_path: str, commit_hash: str):
        """
        Restaura o diretório para o estado do commit especificado.
        """
        if git is None:
            raise ImportError("GitPython não está instalado. Instale com 'pip install gitpython'.")
        src = Path(directory_path).resolve()
        shadow_repo = CheckpointManager.get_shadow_repo_path(str(src))
        if not (shadow_repo / ".git").exists():
            raise FileNotFoundError("Nenhum checkpoint encontrado para este diretório.")
        repo = git.Repo(shadow_repo)
        repo.git.checkout(commit_hash)
        # Restaurar arquivos do shadow_repo para o diretório original
        for item in shadow_repo.iterdir():
            if item.name == ".git":
                continue
            dest = src / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest) 