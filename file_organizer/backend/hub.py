# file_organizer/backend/hub.py

import asyncio
import json
from pathlib import Path
from fastmcp import FastMCP, Context, Client
from rich.console import Console
from file_organizer.backend.context_manager import ContextManager
from file_organizer.backend.checkpoint_manager import CheckpointManager

# Importa as FUNÇÕES dos agentes diretamente
from agents.file_organizer.scanner import scan_directory, summarize_scan_results
from agents.file_organizer.categorizer import categorize_items
from agents.file_organizer.planner import build_plan_from_categorization
from agents.file_organizer.rules import apply_categorization_rules
from agents.file_organizer.executor import create_folder, move_file, move_folder
from agents.file_organizer.suggestion import suggest_file_move
from hivemind_core.memory_manager import index_directory, query_memory, post_memory_experience, get_feed_for_agent
from agents.file_organizer.maintenance import find_empty_folders
from agents.file_organizer.digest import get_tree_summary
from agents.file_organizer.tree_categorizer import categorize_from_tree

from agents.maintenance_agent import find_empty_folders, find_duplicates

console = Console()
hub_mcp = FastMCP(name="FileOrganizerHub")

@hub_mcp.tool
async def organize_directory(
    ctx: Context,
    dir_path: str,
    user_goal: str,
    auto_approve: bool = False,
    dry_run: bool = False,
    example_file_contents: str = ""
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
            # Buscar contexto hierárquico
            user_rules_context = ContextManager.get_hierarchical_context(str(root_dir))
            llm_categorized_map = await categorize_items.fn(
                user_goal=user_goal,
                root_directory=str(root_dir),
                directory_summaries=[item for item in items_for_llm if Path(item['path']).is_dir()],
                loose_files_metadata=[item for item in items_for_llm if Path(item['path']).is_file()],
                ctx=ctx,
                user_rules_context=user_rules_context,
                example_file_contents=example_file_contents
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
        execution_results = await execute_plan(plan=plan_object, ctx=ctx)

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

        # --- CHECKPOINT MOVIDO PARA CÁ ---
        try:
            commit_hash = await asyncio.to_thread(CheckpointManager.create_checkpoint, str(root_directory))
            await ctx.log(f"Checkpoint criado antes da execução do plano: {commit_hash}", level="info")
        except Exception as e:
            await ctx.log(f"Falha ao criar checkpoint: {e}", level="warning")
        # --- FIM DO BLOCO DE CHECKPOINT ---

        await ctx.log(f" Executando plano aprovado para '{root_directory}'...", level="info")
        execution_summary = []
        async with Client(hub_mcp) as client:
            for action in steps:
                action_type = action.get("action")
                result_object = await client.call_tool('execute_planned_action', { # Usar o client definido
                    'action': action,
                    'root_directory': root_directory,
                    'ctx': ctx
                })
                result = result_object.structured_content
                execution_summary.append(result)
                if result and result.get("status") == "error":
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
async def organize_experimental(directory_path: str, ctx: Context) -> dict:
    """
    Executa o fluxo de organização experimental e retorna o resultado como um objeto Python.
    """
    await ctx.log(" Iniciando fluxo de organização experimental...", level="info")
    
    # Passo 1: Obter a árvore de diretórios
    tree_text = await get_tree_summary.fn(root_path=directory_path, ctx=ctx)
    
    # --- VERIFICAÇÃO DE ERRO DO DIGEST AGENT (CORRIGIDO) ---
    if not tree_text:
        msg = "Falha ao gerar a estrutura de diretórios. O diretório pode estar inacessível ou ocorreu um erro interno no scanner."
        await ctx.log(msg, level="error")
        # CORRETO: Retornando um dicionário Python.
        return {"status": "error", "details": msg}
    
    # Logar a árvore para a UI
    await ctx.log(f"Estrutura de diretórios detectada:\n{tree_text}", level="info")

    # Passo 2: Obter sugestões do LLM com base na árvore
    suggestions = await categorize_from_tree.fn(tree_text=tree_text, ctx=ctx)
    
    await ctx.log(" Análise concluída.", level="info")
    
    result_payload = {
        "status": "completed",
        "tree": tree_text,
        "result": suggestions
    }
    return result_payload



@hub_mcp.tool
async def execute_planned_action(action: dict, root_directory: str, ctx: Context) -> dict:
    """
    Executa uma ação planejada (criar pasta, mover arquivo/pasta).
    """
    action_type = action.get("action")
    async with Client(hub_mcp) as client: # Use Client para chamar ferramentas de outros agentes
        result_object = None
        if action_type == "CREATE_FOLDER":
            result_object = await client.call_tool('create_folder', {'path': action['path'], 'root_directory': root_directory, 'ctx': ctx})
        elif action_type == "MOVE_FILE":
            move_params = {
                'from_path': action['from'],
                'to_path': action['to'],
                'root_directory': root_directory,
                'ctx': ctx
            }
            if 'suggestion_entry_id' in action and action['suggestion_entry_id']:
                move_params['suggestion_entry_id'] = action['suggestion_entry_id']
            result_object = await client.call_tool('move_file', move_params)
        elif action_type == "MOVE_FOLDER":
            result_object = await client.call_tool('move_folder', {'from_path': action['from'], 'to_path': action['to'], 'root_directory': root_directory, 'ctx': ctx})
        else:
            msg = f"Tipo de ação desconhecido: {action_type}"
            await ctx.log(msg, level="error")
            return {"status": "error", "details": msg}
        
        return result_object.structured_content if result_object else {"status": "error", "details": "A ação não retornou resultado."}

@hub_mcp.tool
async def handle_file_deleted(path: str, ctx: Context) -> dict:
    """
    Lida com o evento de arquivo deletado, removendo-o do índice de memória.
    """
    await ctx.log(f"Arquivo deletado detectado: {path}. Removendo do índice de memória...", level="info")
    async with Client(hub_mcp) as client:
        result = await client.call_tool_fn('remove_from_memory_index', path=path)
    return result

@hub_mcp.tool
async def handle_file_modified(path: str, ctx: Context) -> dict:
    """
    Lida com o evento de arquivo modificado, atualizando-o no índice de memória.
    """
    await ctx.log(f"Arquivo modificado detectado: {path}. Atualizando no índice de memória...", level="info")
    async with Client(hub_mcp) as client:
        result = await client.call_tool_fn('update_memory_index', path=path)
    return result

hub_mcp.add_tool(create_folder)
hub_mcp.add_tool(move_file)
hub_mcp.add_tool(move_folder)
hub_mcp.add_tool(find_empty_folders)
hub_mcp.add_tool(find_duplicates)
hub_mcp.add_tool(get_feed_for_agent)
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

