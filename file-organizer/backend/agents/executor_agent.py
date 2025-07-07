# agents/executor_agent.py
import shutil
from pathlib import Path
from fastmcp import FastMCP, Context
from agents.memory_agent import post_entry, MemoryEntry
import uuid
from datetime import datetime

mcp = FastMCP(name="ExecutorAgent")

def _is_path_safe(path_to_check: Path, root_directory: Path) -> bool:
    """Verifica se um caminho está contido com segurança no diretório raiz."""
    try:
        safe_root = root_directory.resolve()
        target_path = Path(path_to_check).resolve()
        # Adicionado para verificar explicitamente se o caminho resolvido ainda está dentro do diretório raiz
        return target_path.is_relative_to(safe_root) and safe_root in target_path.parents
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
        return {"status": "success", "action": "create_folder", "path": path}
    except Exception as e:
        msg = f"Falha ao criar pasta '{path}': {e}"
        await ctx.log(msg, level="error")
        return {"status": "error", "details": msg}

@mcp.tool
async def move_file(from_path: str, to_path: str, root_directory: str, ctx: Context, suggestion_entry_id: str = None) -> dict:
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
        # --- Postar resultado no HiveMind ---
        entry_id = uuid.uuid4().hex
        entry: MemoryEntry = {
            "entry_id": entry_id,
            "agent_name": "ExecutorAgent",
            "entry_type": "ACTION_RESULT",
            "timestamp": datetime.utcnow().isoformat(),
            "content": f"Arquivo movido de {from_path} para {to_path}",
            "context": {
                "root_directory": root_directory,
                "from": from_path,
                "to": to_path
            },
            "tags": ["action_result", "move_file"],
            "utility_score": 0.0,
            "references_entry_id": suggestion_entry_id
        }
        await post_entry.fn(entry=entry, ctx=ctx)
        return {"status": "success", "action": "move_file", "from": from_path, "to": to_path, "action_entry_id": entry_id}
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

# É importante notar que a integração dessas novas ferramentas no fluxo principal
# de consulta do agente precisará ser feita no local apropriado. Por exemplo:
#
# 1. Após a indexação, o sistema deve chamar `await mcp.get_tool('update_indexed_files_count').call(count=N)`.
#    (Ou, se você tiver uma instância do agente: `await agent_instance.update_indexed_files_count(count=N, ctx=your_context)`)
# 2. Quando uma nova consulta do usuário é recebida (ex: "Quantos arquivos há na memoria?"):
#    a. Primeiro, tente: `response = await mcp.get_tool('query_indexed_files_count').call(query_text=user_query)`
#       (Ou: `response = await agent_instance.query_indexed_files_count(query_text=user_query, ctx=your_context)`)
#    b. Se `response['status'] == 'answered'`, use `response['answer']`.
#    c. Se `response['status'] == 'pass_through'`, prossiga com a busca semântica normal.
#
# Este arquivo (executor_agent.py) agora fornece as ferramentas, mas o orquestrador
# principal do agente (que pode estar em web_ui.py ou outro módulo de agente)
# precisa ser ajustado para usar essas ferramentas na ordem correta.
