# file-organizer/backend/hub.py

import json
from pathlib import Path
from fastmcp import FastMCP, Context, Client
from rich.console import Console

# Importa as FUNÇÕES dos agentes diretamente
from agents.scanner_agent import scan_directory, summarize_scan_results
from agents.categorizer_agent import categorize_items
from agents.planner_agent import build_plan_from_categorization
from agents.rules_agent import apply_categorization_rules
from agents.executor_agent import create_folder, move_file, move_folder
from agents.suggestion_agent import suggest_file_move
from agents.memory_agent import index_directory, query_memory, post_memory_experience, get_feed_for_agent
from agents.maintenance_agent import find_empty_folders
from agents.digest_agent import get_tree_summary
from agents.tree_categorizer_agent import categorize_from_tree

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
    Orquestra o processo de organização de arquivos de forma limpa e sequencial.
    """
    try:
        root_dir = Path(dir_path).expanduser().resolve()
        await ctx.log(f"Iniciando organização para: '{root_dir}'", level="info")

        # FASE 1: SCAN
        await ctx.log(" Passo 1/5: Escaneando diretório...", level="info")
        scan_results = await scan_directory.fn(directory_path=dir_path, ctx=ctx)

        # Prepara a lista de itens para categorizar (subpastas e arquivos soltos no root)
        all_dir_summaries = await summarize_scan_results.fn(scan_results=scan_results, ctx=ctx)
        sub_dirs_to_process = [s for s in all_dir_summaries if Path(s['path']).resolve() != root_dir]
        loose_files_metadata = [f for f in scan_results if str(Path(f['path']).parent.resolve()) == str(root_dir)]
        
        items_to_process = sub_dirs_to_process + loose_files_metadata
        
        await ctx.log(f" Scan concluído: {len(items_to_process)} itens encontrados para processar.", level="info")

        if not items_to_process:
            msg = "Nenhum item (subpastas ou arquivos soltos) encontrado para organizar."
            await ctx.log(msg, level="info")
            return {"status": "completed", "message": msg}

        # FASE 2: APLICAR REGRAS RÁPIDAS
        await ctx.log(" Passo 2/5: Aplicando regras de categorização rápida...", level="info")
        rule_categorized_map, items_for_llm = await apply_categorization_rules(items=items_to_process)
        await ctx.log(f" {len(rule_categorized_map)} itens categorizados por regras.", level="info")

        # FASE 3: CATEGORIZAR COM LLM (apenas os restantes)
        llm_categorized_map = {}
        if items_for_llm:
            await ctx.log(f" Passo 3/5: Categorizando {len(items_for_llm)} itens restantes com IA...", level="info")
            llm_categorized_map = await categorize_items.fn(
                user_goal=user_goal,
                root_directory=str(root_dir),
                directory_summaries=[item for item in items_for_llm if Path(item['path']).is_dir()],
                loose_files_metadata=[item for item in items_for_llm if Path(item['path']).is_file()],
                ctx=ctx
            )
        else:
            await ctx.log(" Passo 3/5: Nenhum item restante para categorização com IA.", level="info")

        categorization_map = {**rule_categorized_map, **llm_categorized_map}
        
        if not categorization_map:
            msg = "Não foi possível gerar um mapa de categorização."
            await ctx.log(msg, level="warning")
            return {"status": "warning", "details": msg}

        # FASE 4: CONSTRUIR PLANO (agora recebe o mapa bruto e resolve os conflitos internamente)
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

        # FASE 5: EXECUTAR O PLANO
        await ctx.log(" Executando plano de organização (Passo 5/5)...", level="info")
        execution_results = await execute_plan.fn(plan=plan_object, ctx=ctx)

        # Adicionar o registro da experiência de organização ao Hive Mind
        async with Client(hub_mcp) as client:
            await client.call_tool_fn('post_memory_experience', **{
                'experience': f"Organização concluída para o diretório '{root_dir}' com o objetivo '{user_goal}'. {len(plan_object.get('steps', []))} ações executadas.",
                'tags': ['organization', 'execution', 'completed'],
                'source_agent': 'FileOrganizerHub',
                'reward': 0.5 
            })

        return {
            "status": "completed",
            "plan": plan_object,
            "execution_results": execution_results
        }

    except Exception as e:
        import traceback
        error_message = f"Ocorreu um erro crítico durante a organização: {e}"
        await ctx.log(error_message, level="error")
        await ctx.log(traceback.format_exc(), level="debug")
        return {"status": "error", "details": error_message}

#
# O restante do arquivo hub.py (as outras ferramentas) pode permanecer como está.
#

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

@hub_mcp.tool
async def organize_experimental(directory_path: str, ctx: Context) -> str:
    """
    Executa o fluxo de organização experimental e retorna o resultado como uma string JSON.
    """
    await ctx.log(" Iniciando fluxo de organização experimental...", level="info")
    
    # Passo 1: Obter a árvore de diretórios
    tree_text = await get_tree_summary.fn(root_path=directory_path, ctx=ctx)
    
    # --- NOVA VERIFICAÇÃO DE ERRO DO DIGEST AGENT ---
    if not tree_text or tree_text.startswith("ERROR:"):
        msg = f"Falha ao gerar a estrutura de diretórios. Detalhes: {tree_text}"
        await ctx.log(msg, level="error")
        # Retorna um JSON de erro para o frontend
        return json.dumps({"status": "error", "details": msg})
    
    # Logar a árvore para a UI
    await ctx.log(f"Estrutura de diretórios detectada:\n{tree_text}", level="info")

    # Passo 2: Obter sugestões do LLM com base na árvore
    suggestions = await categorize_from_tree.fn(tree_text=tree_text, ctx=ctx)
    
    await ctx.log(" Análise concluída.", level="info")
    
    # --- MUDANÇA PRINCIPAL: Serializar para JSON antes de retornar ---
    result_payload = {
        "status": "completed",
        "tree": tree_text,
        "result": suggestions
    }
    return json.dumps(result_payload)

hub_mcp.add_tool(find_empty_folders)
hub_mcp.add_tool(post_memory_experience)
hub_mcp.add_tool(get_feed_for_agent)
hub_mcp.add_tool(suggest_file_move)
hub_mcp.add_tool(execute_plan)
hub_mcp.add_tool(get_tree_summary)
hub_mcp.add_tool(categorize_from_tree)
hub_mcp.add_tool(organize_experimental)

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