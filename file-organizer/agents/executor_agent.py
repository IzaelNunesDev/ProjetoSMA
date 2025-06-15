# agents/executor_agent.py
import shutil
from pathlib import Path
from fastmcp import FastMCP, Context
from agents.memory_agent import post_memory_experience # <<< NOVA IMPORTAÇÃO

mcp = FastMCP(name="ExecutorAgent")



def _is_path_safe(path_to_check: Path, root_directory: Path) -> bool:
    """Verifica se um caminho está contido com segurança no diretório raiz."""
    try:
        safe_root = root_directory.resolve()
        target_path = Path(path_to_check).resolve()
        return target_path.is_relative_to(safe_root)
    except Exception:
        return False

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
        
        # --- Postar no Hive Mind ---
        await post_memory_experience.fn(
            experience=f"Criei a pasta '{Path(path).name}' em '{Path(path).parent}'.",
            tags=["create_folder", "maintenance"],
            source_agent="ExecutorAgent",
            ctx=ctx
        )
        # ---------------------------

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

        # --- Postar no Hive Mind ---
        file_extension = source.suffix.lstrip(".").lower()
        await post_memory_experience.fn(
            experience=f"Movi o arquivo '{source.name}' para o diretório '{destination.parent}'.",
            tags=["move_file", file_extension, "organization"],
            source_agent="ExecutorAgent",
            ctx=ctx
        )
        # ---------------------------

        return {"status": "success", "action": "move_file", "from": from_path, "to": to_path}
    except Exception as e:
        msg = f"Falha ao mover arquivo '{source}': {e}"
        await ctx.log(msg, level="error")
        return {"status": "error", "details": msg}

@mcp.tool
async def move_folder(from_path: str, to_path: str, root_directory: str, ctx: Context) -> dict:
    """Move uma pasta inteira de forma segura."""
    source = Path(from_path)
    destination_dir = Path(to_path) # O destino é a pasta que conterá a pasta movida
    root = Path(root_directory)

    # Garante que a origem e o destino estejam dentro do diretório raiz
    if not _is_path_safe(source, root) or not _is_path_safe(destination_dir, root):
        msg = f"Acesso negado: Operação de mover pasta '{source}' para '{destination_dir}' está fora do diretório permitido."
        await ctx.log(msg, level="error")
        return {"status": "error", "details": msg}
    
    try:
        destination_path = destination_dir / source.name
        await ctx.log(f"  - Movendo pasta: {source.name} -> {destination_path}", level="info")
        destination_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination_path))
        return {"status": "success", "action": "move_folder", "from": from_path, "to": str(destination_path)}
    except Exception as e:
        msg = f"Falha ao mover a pasta '{source}': {e}"
        await ctx.log(msg, level="error")
        return {"status": "error", "details": msg}


