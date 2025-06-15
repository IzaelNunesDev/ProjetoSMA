# hub.py
import json
from pathlib import Path
from fastmcp import FastMCP, Context
from rich.console import Console
from rich.prompt import Confirm

# Importa as FUNÇÕES dos agentes diretamente
from agents.scanner_agent import scan_directory
from agents.planner_agent import create_organization_plan
from agents.executor_agent import create_folder, move_file, move_folder
# --- NOVA IMPORTAÇÃO PARA CORRIGIR BUG CRÍTICO ---
from agents.suggestion_agent import suggest_file_move
# -------------------------------------------------
# --- NOVAS IMPORTAÇÕES DO HIVE MIND ---
from agents.memory_agent import index_directory, query_memory, post_memory_experience, get_feed_for_agent
# ------------------------------------
from agents.maintenance_agent import find_empty_folders


console = Console()

hub_mcp = FastMCP(name="FileOrganizerHub")

@hub_mcp.tool
async def organize_directory(
    directory_path: str,
    user_goal: str,
    ctx: Context,
    auto_approve: bool = False
):
    """
    Orquestra o processo completo de organização de um diretório chamando as funções dos agentes diretamente.
    """
    try:
        root_dir = Path(directory_path).expanduser().resolve()
        await ctx.log(f"Iniciando organização para o diretório: '{root_dir}' com o objetivo: '{user_goal}'", level="info")

        # 1. Escanear
        await ctx.log("🔍 Escaneando diretório...", level="info")
        metadata_list = await scan_directory.fn(directory_path=directory_path, ctx=ctx)
        
        if not metadata_list:
            msg = "Nenhum arquivo encontrado para organizar."
            await ctx.log(msg, level="info")
            return {"status": "success", "details": msg}

        await ctx.log(f"✅ Análise concluída. {len(metadata_list)} arquivos encontrados.", level="info")

        # 2. Planejar
        await ctx.log("🧠 Criando um plano de organização...", level="info")
        plan = await create_organization_plan.fn(files_metadata=metadata_list, user_goal=user_goal, ctx=ctx)
        
        if not plan or not isinstance(plan, list) or not all('action' in p for p in plan):
             msg = "O agente de planejamento retornou um plano inválido."
             await ctx.log(msg, level="error")
             return {"status": "error", "details": msg}

        await ctx.log("📝 Plano gerado:", level="info")
        plan_details = "\n".join([f"  - {a.get('action', 'AÇÃO INDEFINIDA')}: {a.get('path') or a.get('from', 'N/A')}" for a in plan])
        await ctx.log(plan_details, level="info")

        # 3. Confirmação de Execução (agora gerenciada pela UI antes de chamar esta função)
        # Se auto_approve for False, presume-se que a UI já obteve confirmação.
        # Se auto_approve for True, o plano será executado diretamente.
        # O hub não realiza mais a confirmação interativa para aprovação do plano.

        # 4. Executar
        await ctx.log("\n🚀 Executando o plano...", level="info")
        execution_summary = []
        for action in plan:
            action_type = action.get("action")
            result = {}
            
            if action_type == "CREATE_FOLDER":
                result = await create_folder.fn(path=action.get("path"), root_directory=directory_path, ctx=ctx)
            elif action_type == "MOVE_FILE":
                result = await move_file.fn(from_path=action.get("from"), to_path=action.get("to"), root_directory=directory_path, ctx=ctx)
            # --- NOVA LÓGICA DE EXECUÇÃO ---
            elif action_type == "MOVE_FOLDER":
                result = await move_folder.fn(from_path=action.get("from"), to_path=action.get("to"), root_directory=directory_path, ctx=ctx)
            # -------------------------------
            else:
                result = {"status": "skipped", "details": f"Ação desconhecida: {action_type}"}
            
            execution_summary.append(result)

            if result.get("status") == "error":
                await ctx.log(f"❌ Falha na ação: {result.get('details')}", level="error")
                if not auto_approve:
                    await ctx.log("🛑 Execução interrompida devido a erro e auto_approve=False. A UI deve gerenciar a continuação, se desejado.", level="warning")
                    break
        
        await ctx.log("\n✨ Organização finalizada! ✨", level="info")
        return {"status": "success", "summary": execution_summary}

    except Exception as e:
        error_message = f"Ocorreu um erro crítico durante a organização: {e}"
        await ctx.log(error_message, level="error")
        console.print_exception()
        return {"status": "error", "details": error_message}

hub_mcp.add_tool(find_empty_folders)
hub_mcp.add_tool(post_memory_experience)
hub_mcp.add_tool(get_feed_for_agent)
# Adiciona a ferramenta correta para sugestão de movimento de arquivo
hub_mcp.add_tool(suggest_file_move)

@hub_mcp.tool
async def index_directory_for_memory(directory_path: str, ctx: Context) -> dict:
    """
    Ferramenta do hub para chamar a função de indexação do agente de memória.
    """
    return await index_directory.fn(directory_path=directory_path, ctx=ctx)

@hub_mcp.tool
async def query_files_in_memory(query: str, ctx: Context) -> dict:
    """
    Ferramenta do hub para chamar a função de consulta do agente de memória.
    """
    return await query_memory.fn(query=query, ctx=ctx)

@hub_mcp.tool
async def execute_planned_action(action: dict, root_directory: str, ctx: Context) -> dict:
    """
    Ferramenta do hub para executar uma única ação planejada, delegando para o executor_agent.
    """
    action_type = action.get("action")
    await ctx.log(f"Hub: Executando ação delegada '{action_type}'", level="info")

    result = {}
    if action_type == "CREATE_FOLDER":
        result = await create_folder.fn(path=action.get("path"), root_directory=root_directory, ctx=ctx)
    elif action_type == "MOVE_FILE":
        result = await move_file.fn(from_path=action.get("from"), to_path=action.get("to"), root_directory=root_directory, ctx=ctx)
    elif action_type == "MOVE_FOLDER":
        result = await move_folder.fn(from_path=action.get("from"), to_path=action.get("to"), root_directory=root_directory, ctx=ctx)
    else:
        result = {"status": "error", "details": f"Ação desconhecida recebida pelo hub: {action_type}"}
        await ctx.log(result["details"], level="warning")

    return result