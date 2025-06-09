# main_orchestrator.py
import asyncio
import json
from fastmcp import Client, FastMCP, Context

# Define o hub MCP que será usado pelo web_ui.py
hub_mcp = FastMCP()

@hub_mcp.tool()
async def organize_directory(ctx: Context, directory_path: str, user_goal: str, auto_approve: bool = False):
    """Organiza um diretório com base no objetivo do usuário."""
    ctx.log.info(f"Iniciando organização para o diretório: '{directory_path}' com o objetivo: '{user_goal}'")

    # 1. Conectar-se aos agentes (servidores MCP)
    # Usaremos clientes dentro da ferramenta para se comunicar com outros agentes.
    # Idealmente, os caminhos dos agentes seriam configuráveis.
    scanner_agent_cmd = ["python", "agents/scanner_agent.py"]
    planner_agent_cmd = ["python", "agents/planner_agent.py"]
    executor_agent_cmd = ["python", "agents/executor_agent.py"]

    try:
        # 2. Chamar o ScannerAgent para analisar o diretório
        async with Client(scanner_agent_cmd, log_handler=ctx.log.handle_message) as scanner_client:
            ctx.log.info(f"🔍 Escaneando o diretório: {directory_path}...")
            files_metadata_result = await scanner_client.call_tool("scan_directory", {"directory_path": directory_path})
        
        if not files_metadata_result or not files_metadata_result[0].text:
            ctx.log.error("❌ Erro: O ScannerAgent não retornou metadados válidos.")
            return json.dumps({"status": "error", "details": "ScannerAgent não retornou metadados."})
        try:
            metadata_list = json.loads(files_metadata_result[0].text)
        except json.JSONDecodeError as e:
            ctx.log.error(f"❌ Erro ao processar metadados do ScannerAgent: {e}. Resposta: {files_metadata_result[0].text}")
            return json.dumps({"status": "error", "details": f"Erro ao decodificar metadados: {e}"})
        
        ctx.log.info(f"✅ Análise concluída. {len(metadata_list)} arquivos encontrados.")
        if not metadata_list:
            ctx.log.info("Nenhum arquivo encontrado para organizar.")
            return json.dumps({"status": "success", "details": "Nenhum arquivo encontrado para organizar."})

        # 3. Chamar o PlannerAgent para criar um plano
        async with Client(planner_agent_cmd, log_handler=ctx.log.handle_message) as planner_client:
            ctx.log.info("🧠 Criando um plano de organização...")
            # Passar o user_goal para o planner_agent
            plan_result = await planner_client.call_tool("create_organization_plan", 
                                                         {"files_metadata": metadata_list, "user_goal": user_goal})
        
        if not plan_result or not plan_result[0].text:
            ctx.log.error("❌ Erro: O PlannerAgent não retornou um plano válido.")
            return json.dumps({"status": "error", "details": "PlannerAgent não retornou um plano."})
        try:
            plan = json.loads(plan_result[0].text)
        except json.JSONDecodeError as e:
            ctx.log.error(f"❌ Erro ao processar o plano do PlannerAgent: {e}. Resposta: {plan_result[0].text}")
            return json.dumps({"status": "error", "details": f"Erro ao decodificar plano: {e}"})

        ctx.log.info("📝 Plano gerado:")
        if not plan or not isinstance(plan, list) or not all(isinstance(item, dict) and 'action' in item for item in plan):
            ctx.log.error("❌ Plano inválido ou vazio recebido do PlannerAgent.")
            if plan:
                for item in plan:
                    ctx.log.info(f"  - {item}") # Log para o WebSocket
            return json.dumps({"status": "error", "details": "Plano inválido ou vazio."})

        for action_item in plan:
            ctx.log.info(f"  - {action_item['action']}: {action_item.get('path') or action_item.get('from', 'N/A')}")

        # 4. Confirmação (se não for auto_approve)
        if not auto_approve:
            # Para a UI, esta parte é pulada. Se fosse uma CLI, aqui pediríamos confirmação.
            # No contexto da UI, o auto_approve=True já foi passado.
            # Se quiséssemos interagir com o usuário via WebSocket para confirmação, seria mais complexo.
            ctx.log.info("Aprovação automática habilitada. Pulando confirmação manual.")
            pass # Em um cenário CLI, aqui seria o input.

        # 5. Executar o plano
        ctx.log.info("\n🚀 Executando o plano...")
        execution_summary = []
        async with Client(executor_agent_cmd, log_handler=ctx.log.handle_message) as executor_client:
            for action_item in plan:
                action_str = f"Ação '{action_item['action']}'"
                if action_item.get("action") == "CREATE_FOLDER" and "path" in action_item:
                    result = await executor_client.call_tool("create_folder", {"path": action_item["path"]})
                    status = json.loads(result[0].text).get('status', 'erro desconhecido')
                    log_msg = f"  - {action_str} para '{action_item['path']}': {status}"
                    execution_summary.append({"action": action_item, "status": status})
                elif action_item.get("action") == "MOVE_FILE" and "from" in action_item and "to" in action_item:
                    result = await executor_client.call_tool("move_file", {"source_path": action_item["from"], "destination_path": action_item["to"]})
                    status = json.loads(result[0].text).get('status', 'erro desconhecido')
                    log_msg = f"  - {action_str} de '{action_item['from']}' para '{action_item['to']}': {status}"
                    execution_summary.append({"action": action_item, "status": status})
                elif action_item.get("action") == "ERROR":
                    log_msg = f"  - Erro no plano: {action_item.get('details')}"
                    execution_summary.append({"action": action_item, "status": "error", "details": action_item.get('details')})
                else:
                    log_msg = f"  - Ação desconhecida ou malformada no plano: {action_item}"
                    execution_summary.append({"action": action_item, "status": "unknown_action"})
                ctx.log.info(log_msg)
        
        ctx.log.info("\n✨ Organização finalizada! ✨")
        return json.dumps({"status": "success", "details": "Organização concluída.", "summary": execution_summary})

    except Exception as e:
        ctx.log.error(f"Ocorreu um erro inesperado na orquestração: {str(e)}")
        return json.dumps({"status": "error", "details": f"Erro inesperado na orquestração: {str(e)}"})

# O bloco if __name__ == "__main__" foi removido pois a execução agora é via web_ui.py
# Se precisar testar este hub diretamente, você pode adicionar um código similar ao de web_ui.py
# para instanciar um cliente e chamar a ferramenta 'organize_directory'.
