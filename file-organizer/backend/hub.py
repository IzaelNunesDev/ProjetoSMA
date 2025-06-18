# hub.py
import json
from pathlib import Path
from fastmcp import FastMCP, Context
from rich.console import Console
from rich.prompt import Confirm

# Importa as FUNÇÕES dos agentes diretamente
from agents.scanner_agent import scan_directory, summarize_scan_results
# --- NOVOS IMPORTS ---
from agents.categorizer_agent import categorize_items
from agents.planner_agent import build_plan_from_categorization
from agents.rules_agent import apply_categorization_rules
# --------------------
from agents.executor_agent import create_folder, move_file, move_folder
from agents.suggestion_agent import suggest_file_move
from agents.memory_agent import index_directory, query_memory, post_memory_experience, get_feed_for_agent
from agents.maintenance_agent import find_empty_folders


console = Console()

hub_mcp = FastMCP(name="FileOrganizerHub")

@hub_mcp.tool
async def organize_directory(
    ctx: Context,
    dir_path: str,
    user_goal: str,
    auto_approve: bool = False,
    dry_run: bool = False
):
    """
    Orquestra o processo de organização, garantindo que o diretório raiz não seja movido.
    """
    try:
        root_dir = Path(dir_path).expanduser().resolve()
        await ctx.log(f"Iniciando organização para: '{root_dir}'", level="info")

        # FASE 0: SCAN
        await ctx.log(" Passo 1/5: Escaneando diretório...", level="info")
        scan_results = await scan_directory.fn(directory_path=dir_path, ctx=ctx)

        # Filtra subpastas, excluindo o próprio diretório raiz.
        dir_summaries_all = await summarize_scan_results.fn(scan_results=scan_results, ctx=ctx)
        dir_summaries = [s for s in dir_summaries_all if Path(s['path']).resolve() != root_dir]
        
        # Filtra arquivos soltos, garantindo que estão diretamente no diretório raiz.
        loose_files_metadata = [f for f in scan_results if str(Path(f['path']).parent.resolve()) == str(root_dir)]
        
        await ctx.log(f" Scan concluído: {len(dir_summaries)} subpastas e {len(loose_files_metadata)} arquivos soltos encontrados para processar.", level="info")
        
        if not dir_summaries and not loose_files_metadata:
            msg = "Nenhum item (subpastas ou arquivos soltos) encontrado dentro do diretório para organizar."
            await ctx.log(msg, level="info")
            return {"status": "completed", "message": msg, "plan": {}, "execution_results": []}

        # Antes da FASE 1: CATEGORIZAR com Regras
        await ctx.log(" Passo 2/5: Aplicando regras de categorização rápida...", level="info")
        all_items_to_process = dir_summaries + loose_files_metadata
        
        # --- CORREÇÃO DA CHAMADA DA FUNÇÃO ---
        # Chamada direta para a função async, sem .fn e sem ctx
        rule_categorized_map, items_for_llm_metadata = await apply_categorization_rules(items=all_items_to_process)
        # --- FIM DA CORREÇÃO ---

        await ctx.log(f" {len(rule_categorized_map)} itens categorizados por regras.", level="info")

        llm_categorized_map = {}
        if items_for_llm_metadata:
            # FASE 2: CATEGORIZAR com LLM
            await ctx.log(f" Passo 3/5: Categorizando {len(items_for_llm_metadata)} itens restantes com IA...", level="info")
            
            items_for_llm_dirs = [item for item in items_for_llm_metadata if Path(item['path']).is_dir()]
            items_for_llm_files = [item for item in items_for_llm_metadata if Path(item['path']).is_file()]

            llm_categorized_map = await categorize_items.fn(
                user_goal=user_goal,
                root_directory=str(root_dir),
                directory_summaries=items_for_llm_dirs,
                loose_files_metadata=items_for_llm_files,
                ctx=ctx
            )
        else:
            await ctx.log(" Passo 3/5: Nenhum item restante para categorização com IA.", level="info")

        categorization_map = {**rule_categorized_map, **llm_categorized_map}
        
        if not categorization_map:
            msg = "Não foi possível gerar um mapa de categorização. Nenhum item foi categorizado."
            await ctx.log(msg, level="warning")
            return {"status": "warning", "details": msg}

        # FASE 3: CONSTRUIR PLANO
        await ctx.log(" Passo 4/5: Construindo plano de execução...", level="info")
        plan_object = await build_plan_from_categorization.fn(
            root_directory=str(root_dir),
            categorization_map=categorization_map,
            ctx=ctx
        )

        await ctx.log(" Plano gerado:", level="info")
        if dry_run:
            await ctx.log(" Modo de simulação (dry run) ativado. Retornando plano para aprovação.", level="info")
            return {"status": "plan_generated", "plan": plan_object}

        # 5. Executar o plano
        await ctx.log(" Executando plano de organização (Passo 5/5)...", level="info")
        execution_results = await execute_plan.fn(
            plan=plan_object,
            ctx=ctx
        )

        # Adicionar o registro da experiência de organização ao Hive Mind
        async with Client(hub_mcp) as client:
            await client.call_tool('post_memory_experience', {
                'experience': f"Organização concluída para o diretório '{root_dir}' com o objetivo '{user_goal}'. {len(plan_object.get('steps', []))} ações executadas.",
                'tags': ['organization', 'execution', 'completed'],
                'source_agent': 'FileOrganizerHub',
                'reward': 0.5 # Recompensa neutra/positiva por completar uma tarefa
            })

        return {
            "status": "completed",
            "plan": plan_object,
            "execution_results": execution_results
        }

    except Exception as e:
        error_message = f"Ocorreu um erro crítico durante a organização: {e}"
        await ctx.log(error_message, level="error")
        return {"status": "error", "details": error_message}

@hub_mcp.tool
async def execute_plan(plan: dict, ctx: Context) -> dict:
    """
    Executa um plano de organização previamente aprovado pelo usuário.
    """
    try:
        steps = plan.get("steps", [])
        root_directory = plan.get("root_directory")
        
        if not root_directory:
            return {"status": "error", "details": "O plano não contém um 'root_directory'."}

        await ctx.log(f" Executando plano aprovado para '{root_directory}'...", level="info")
        execution_summary = []
        for action in steps:
            action_type = action.get("action")
            result = await execute_planned_action.fn(
                action=action,
                root_directory=root_directory,
                ctx=ctx
            )
            execution_summary.append(result)
            if result.get("status") == "error":
                await ctx.log(f" Falha na ação, interrompendo execução: {result.get('details')}", level="error")
                break
        
        await ctx.log("\n Execução do plano finalizada! ", level="info")
        return {"status": "success", "summary": execution_summary}
    except Exception as e:
        error_message = f"Ocorreu um erro crítico durante a execução do plano: {e}"
        await ctx.log(error_message, level="error")
        console.print_exception()
        return {"status": "error", "details": error_message}

hub_mcp.add_tool(find_empty_folders)
hub_mcp.add_tool(post_memory_experience)
hub_mcp.add_tool(get_feed_for_agent)
# Adiciona a ferramenta correta para sugestão de movimento de arquivo
hub_mcp.add_tool(suggest_file_move)
hub_mcp.add_tool(execute_plan)

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