# agents/planner_agent.py (VERSÃO CORRIGIDA)

import os
import json
import google.generativeai as genai
from fastmcp import FastMCP, Context  # Importar FastMCP
from prompt_manager import prompt_manager
from pathlib import Path

# Carrega a chave de API do .env
from dotenv import load_dotenv
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# É crucial criar uma instância do MCP para este agente
mcp = FastMCP(name="PlannerAgent")

@mcp.tool
async def create_organization_plan(files_metadata: list[dict], user_goal: str, ctx: Context) -> list[dict]:
    """
    Cria um plano de organização de arquivos baseado nos metadados e no objetivo do usuário.
    O plano consiste em uma lista de ações: CREATE_FOLDER, MOVE_FILE.
    """
    await ctx.log(f"Criando plano com base no objetivo: '{user_goal}'", level="info")
    
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Obtenha o diretório raiz do primeiro arquivo, assumindo que todos são do mesmo lugar.
    # Uma abordagem mais robusta seria passar o diretório raiz como argumento para a função.
    # Por simplicidade, vamos inferir:
    if files_metadata:
        root_dir = str(Path(files_metadata[0]['path']).parent)
    else:
        root_dir = "N/A"

    prompt = prompt_manager.format_prompt(
        task_name="file-organization", 
        user_goal=user_goal, 
        files_metadata=json.dumps(files_metadata, indent=2, ensure_ascii=False),
        root_directory=root_dir # Adiciona a nova variável
    )

    if not prompt:
        error_message = "Template de prompt 'file-organization' não encontrado."
        await ctx.log(error_message, level="error")
        raise ValueError(error_message)

    try:
        response = await model.generate_content_async(prompt)
        await ctx.log(f"📝 Resposta recebida:\n{response.text}", level="debug")

        # Limpa a resposta do LLM para extrair apenas o JSON
        plan_str = response.text.strip().replace("```json", "").replace("```", "")

        try:
            plan = json.loads(plan_str)
            if not isinstance(plan, dict) or "objective" not in plan or "steps" not in plan or not isinstance(plan["steps"], list):
                raise ValueError("Plano malformado: campo 'objective' ou 'steps' ausente ou inválido.")
            return plan
        except json.JSONDecodeError as e:
            raise ValueError(f"Falha ao decodificar JSON: {e}\nTexto recebido:\n{plan_str}")
    except Exception as e:
        error_message = f"Erro ao gerar ou decodificar o plano da IA: {e}\nResposta recebida: {response.text if 'response' in locals() else 'N/A'}"
        await ctx.log(error_message, level="error")
        # Retorna uma lista vazia em caso de erro para não quebrar o fluxo do hub
        return []