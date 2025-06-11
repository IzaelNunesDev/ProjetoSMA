# hub.py
import json
from fastmcp import FastMCP, Context
from rich.console import Console
from rich.prompt import Confirm

# Importa as FUNÇÕES dos agentes diretamente, não as instâncias mcp
from agents.scanner_agent import scan_directory
from agents.planner_agent import create_organization_plan
from agents.executor_agent import create_folder, move_file

console = Console()

# Cria o hub principal. Ele só precisa ter a ferramenta de orquestração.
hub_mcp = FastMCP(name="Hub")

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
        await ctx.log(f"Iniciando organização para o diretório: '{directory_path}' com o objetivo: '{user_goal}'", level="info")

        # 1. Escanear
        metadata_list = await scan_directory(directory_path=directory_path, ctx=ctx)

        # 2. Planejar
        plan = await create_organization_plan(files_metadata=metadata_list, user_goal=user_goal, ctx=ctx)
        
        await ctx.log("📝 Plano gerado:", level="info")
        plan_details = "\n".join([f"  - {a['action']}: {a.get('path') or a.get('from')}" for a in plan])
        await ctx.log(plan_details, level="info")

        # 3. Confirmar (Lógica CLI, pulada na UI)
        if not auto_approve:
            if not Confirm.ask("\n[bold yellow]Você aprova este plano?[/]"):
                await ctx.log("❌ Organização cancelada pelo usuário.", level="info")
                return {"status": "cancelled"}

        # 4. Executar
        await ctx.log("\n🚀 Executando o plano...", level="info")
        execution_summary = []
        for action in plan:
            action_type = action.get("action")
            result = None
            if action_type == "CREATE_FOLDER":
                result = await create_folder(path=action.get("path"), root_directory=directory_path, ctx=ctx)
            elif action_type == "MOVE_FILE":
                result = await move_file(from_path=action.get("from"), to_path=action.get("to"), root_directory=directory_path, ctx=ctx)
            else:
                result = {"status": "skipped", "details": f"Ação desconhecida: {action_type}"}
            
            execution_summary.append(result)

        await ctx.log("\n✨ Organização finalizada! ✨", level="info")
        return {"status": "success", "summary": execution_summary}

    except Exception as e:
        error_message = f"Ocorreu um erro crítico durante a organização: {e}"
        await ctx.log(error_message, level="error")
        console.print_exception()
        return {"status": "error", "details": error_message}
