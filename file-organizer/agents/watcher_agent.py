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
async def suggest_organization_for_file(file_path: str, ctx: Context) -> dict:
    """Sugere um plano de organização para um único arquivo detectado."""
    await ctx.log(f"WatcherAgent: Sugerindo organização para: {file_path}", level="info")
    try:
        p_file_path = Path(file_path)
        if not p_file_path.exists() or not p_file_path.is_file():
            msg = f"Arquivo não encontrado ou não é um arquivo válido: {file_path}"
            await ctx.log(msg, level="error")
            return {"status": "error", "details": msg, "plan": []}

        # Criar metadados básicos para o arquivo único
        file_metadata = {
            "name": p_file_path.name,
            "path": str(p_file_path),
            "size": p_file_path.stat().st_size,
            "extension": p_file_path.suffix.lower(),
            "type": "file",
            "last_modified": p_file_path.stat().st_mtime
        }
        files_metadata_list = [file_metadata]

        # Usar um objetivo genérico para o planejador, ou permitir que seja passado?
        # Por enquanto, um objetivo genérico para organização automática.
        user_goal = "Organizar este novo arquivo na estrutura de pastas existente ou em uma nova apropriada."

        await ctx.log(f"WatcherAgent: Chamando planner_agent para: {p_file_path.name}", level="debug")
        plan = await create_organization_plan.fn(
            files_metadata=files_metadata_list, 
            user_goal=user_goal, 
            ctx=ctx
        )

        if not plan or not isinstance(plan, list):
            msg = "O agente de planejamento retornou um plano inválido para o arquivo."
            await ctx.log(msg, level="warning")
            return {"status": "success", "details": msg, "plan": []} # Retorna sucesso, mas plano vazio

        await ctx.log(f"WatcherAgent: Plano recebido para '{p_file_path.name}': {plan}", level="info")
        return {"status": "success", "plan": plan}

    except Exception as e:
        error_message = f"WatcherAgent: Erro ao sugerir organização para {file_path}: {e}"
        await ctx.log(error_message, level="error")
        # Idealmente, teríamos uma forma de print_exception aqui também se ctx suportar ou se tivermos console
        return {"status": "error", "details": error_message, "plan": []}

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
