# agents/watcher_agent.py
from pathlib import Path
from fastmcp import FastMCP, Context
from .planner_agent import create_organization_plan
from .executor_agent import create_folder, move_file, move_folder

watcher_mcp = FastMCP(name="WatcherAgent") # Initialize MCP for watcher agent

# As ferramentas abaixo são usadas pelo hub.py e são mantidas.
# A lógica de Watchdog (EventHandler, start_watcher) foi removida pois era redundante
# com a implementação em watcher.py (nível raiz do projeto).

# TOOLS PREVIOUSLY REFERRED TO AS "NEW TOOLS"
@watcher_mcp.tool
async def execute_planned_action(action: dict, root_directory: str, ctx: Context) -> dict:
    """Executa uma única ação de organização planejada."""
    action_type = action.get("action")
    await ctx.log(f"WatcherAgent: Executando ação '{action_type}' para: {action.get('path') or action.get('from')}", level="info")
    
    result = {}
    try:
        if action_type == "CREATE_FOLDER":
            result = await create_folder.fn(path=action.get("path"), root_directory=root_directory, ctx=ctx)
        elif action_type == "MOVE_FILE":
            result = await move_file.fn(from_path=action.get("from"), to_path=action.get("to"), root_directory=root_directory, ctx=ctx)
        elif action_type == "MOVE_FOLDER": # Adicionando suporte para mover pastas também, se necessário
            result = await move_folder.fn(from_path=action.get("from"), to_path=action.get("to"), root_directory=root_directory, ctx=ctx)
        else:
            result = {"status": "skipped", "details": f"WatcherAgent: Ação desconhecida ou não suportada: {action_type}"}
            await ctx.log(result["details"], level="warning")
        
        if result.get("status") == "error":
            await ctx.log(f"WatcherAgent: Falha na ação '{action_type}': {result.get('details')}", level="error")
        else:
            await ctx.log(f"WatcherAgent: Ação '{action_type}' concluída com status: {result.get('status')}", level="info")
        
        return result

    except Exception as e:
        error_message = f"WatcherAgent: Erro crítico ao executar ação {action_type}: {e}"
        await ctx.log(error_message, level="error")
        return {"status": "error", "details": error_message}
