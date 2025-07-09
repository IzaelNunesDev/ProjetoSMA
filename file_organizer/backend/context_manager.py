import os
from pathlib import Path
from typing import List, Optional

class ContextManager:
    @staticmethod
    def get_hierarchical_context(target_directory: str) -> str:
        """
        Busca e concatena o conteúdo dos arquivos PROJETOSMA.md de forma hierárquica:
        - Global: ~/.projetosma/PROJETOSMA.md
        - Projeto: <target_directory>/.projetosma/PROJETOSMA.md
        - Subdiretórios (opcional)
        Retorna o contexto concatenado como uma string.
        """
        context_parts: List[str] = []

        # 1. Global
        global_path = Path.home() / ".projetosma" / "PROJETOSMA.md"
        if global_path.exists():
            try:
                context_parts.append(f"[Global]\n{global_path.read_text(encoding='utf-8').strip()}")
            except Exception:
                pass

        # 2. Projeto
        project_path = Path(target_directory) / ".projetosma" / "PROJETOSMA.md"
        if project_path.exists():
            try:
                context_parts.append(f"[Projeto]\n{project_path.read_text(encoding='utf-8').strip()}")
            except Exception:
                pass

        # 3. Subdiretórios (opcional, pode ser expandido)
        # Exemplo: buscar em todos os subdirs de target_directory
        # for subdir in Path(target_directory).rglob('.projetosma/PROJETOSMA.md'):
        #     if subdir != project_path:
        #         try:
        #             context_parts.append(f"[Subdiretório: {subdir.parent.parent}]\n{subdir.read_text(encoding='utf-8').strip()}")
        #         except Exception:
        #             pass

        return "\n\n".join(context_parts) if context_parts else "" 