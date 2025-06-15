# agents/executor_agent.py
import shutil
from pathlib import Path
from fastmcp import FastMCP, Context

mcp = FastMCP(name="ExecutorAgent")

# <<< NEW: Variable to store the number of indexed files >>>
_indexed_files_count = None  # Initialize to None, indicating count is not yet set

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

@mcp.tool
async def update_indexed_files_count(count: int, ctx: Context) -> dict:
    """
    Atualiza o contador global de arquivos indexados.
    Esta função deve ser chamada após a conclusão do processo de indexação.
    """
    global _indexed_files_count
    _indexed_files_count = count
    log_message = f"Contador de arquivos indexados atualizado para: {count}"
    await ctx.log(log_message, level="info")
    return {"status": "success", "message": log_message}

@mcp.tool
async def query_indexed_files_count(query_text: str, ctx: Context) -> dict:
    """
    Verifica se a consulta do usuário é sobre a contagem de arquivos indexados.
    Se for, responde diretamente com a contagem armazenada.
    Caso contrário, indica que a consulta deve ser processada por outros meios (ex: busca semântica).
    
    Esta função deve ser chamada no início do fluxo de processamento de consultas.
    """
    global _indexed_files_count
    
    # Palavras-chave para identificar perguntas sobre a contagem de arquivos
    # Ajuste conforme necessário para cobrir mais variações da pergunta
    keywords = [
        "quantos arquivos", 
        "numero de arquivos", # sem acento para simplicidade
        "arquivos na memoria", 
        "arquivos indexados",
        "total de arquivos"
    ]
    
    normalized_query = query_text.lower()
    
    is_count_query = any(keyword in normalized_query for keyword in keywords)
    
    if is_count_query:
        if _indexed_files_count is not None:
            answer = f"Atualmente, há {_indexed_files_count} arquivo(s) indexado(s) na memória."
            await ctx.log(f"Respondendo à consulta sobre contagem de arquivos: '{query_text}'. Resposta: {answer}", level="info")
            return {"status": "answered", "answer": answer, "sources": "System Metadata"}
        else:
            answer = "A informação sobre a quantidade de arquivos indexados ainda não está disponível."
            await ctx.log(f"Consulta sobre contagem de arquivos ('{query_text}'), mas contagem não definida.", level="warn")
            return {"status": "answered", "answer": answer, "sources": "System Metadata"}
    else:
        # Indica que esta ferramenta não tratou a consulta e ela deve seguir o fluxo normal (ex: busca semântica)
        await ctx.log(f"Consulta '{query_text}' não é sobre contagem de arquivos, passando para próximo handler.", level="debug")
        return {"status": "pass_through", "reason": "Query not related to indexed file count."}

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
