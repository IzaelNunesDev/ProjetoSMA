# agents/executor_agent.py
import shutil
from pathlib import Path
from fastmcp import FastMCP, Context

mcp = FastMCP(name="ExecutorAgent")

def _is_path_safe(path_to_check: Path, root_directory: Path) -> bool:
    """Verifica se um caminho está contido com segurança no diretório raiz."""
    safe_root = root_directory.resolve()
    target_path = Path(path_to_check).resolve()
    return target_path.is_relative_to(safe_root)

@mcp.tool
async def create_folder(path: str, root_directory: str, ctx: Context) -> dict:
    """Cria uma pasta de forma segura dentro do diretório raiz."""
    if not _is_path_safe(Path(path), Path(root_directory)):
        msg = f"Acesso negado: O caminho '{path}' está fora do diretório permitido."
        await ctx.log(msg, level="error")
        return {"status": "error", "details": msg}
    
    try:
        await ctx.log(f"  - Criando pasta: {path}", level="info")
        Path(path).mkdir(parents=True, exist_ok=True)
        return {"status": "success", "action": "create_folder", "path": path}
    except Exception as e:
        msg = f"Falha ao criar pasta '{path}': {e}"
        await ctx.log(msg, level="error")
        return {"status": "error", "details": msg}

@mcp.tool
async def move_file(from_path: str, to_path: str, root_directory: str, ctx: Context) -> dict:
    """Move um arquivo de forma segura, garantindo que ambas as localidades estejam dentro do diretório raiz."""
    source = Path(from_path)
    destination = Path(to_path)
    root = Path(root_directory)

    if not _is_path_safe(source, root) or not _is_path_safe(destination.parent, root):
        msg = f"Acesso negado: Operação de mover '{source}' para '{destination}' está fora do diretório permitido."
        await ctx.log(msg, level="error")
        return {"status": "error", "details": msg}

    try:
        await ctx.log(f"  - Movendo: {source.name} -> {to_path}", level="info")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        return {"status": "success", "action": "move_file", "from": from_path, "to": to_path}
    except Exception as e:
        msg = f"Falha ao mover arquivo '{source}': {e}"
        await ctx.log(msg, level="error")
        return {"status": "error", "details": msg}

# REMOVA o bloco if __name__ == "__main__":
