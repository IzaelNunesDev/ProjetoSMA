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

@mcp.tool  # <-- Adicionar o decorador!
async def create_organization_plan(files_metadata: list[dict], user_goal: str, ctx: Context) -> list[dict]:
    """
    Cria um plano de organização de arquivos baseado nos metadados e no objetivo do usuário.
    O plano consiste em uma lista de ações: CREATE_FOLDER, MOVE_FILE.
    """
    await ctx.log("Criando plano com base no objetivo: '{}'".format(user_goal), level="info")
    
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Use o PromptManager para obter e formatar o prompt da estrutura correta
    prompt = prompt_manager.format_prompt(
        task_name="file-organization", 
        user_goal=user_goal, 
        files_metadata=json.dumps(files_metadata, indent=2, ensure_ascii=False) # Garantir que os dados sejam passados como string JSON
    )

    if not prompt:
        error_message = "Template de prompt 'file-organization' não encontrado."
        await ctx.log(error_message, level="error")
        raise ValueError(error_message)

    try:
        response = await model.generate_content_async(prompt)
        await ctx.log("📝 Resposta da IA recebida, processando o plano...", level="info")
        
        # Limpa a resposta do LLM para extrair apenas o JSON
        plan_str = response.text.strip().replace("```json", "").replace("```", "")
        plan = json.loads(plan_str)
        return plan
    except Exception as e:
        error_message = f"Erro ao gerar ou decodificar o plano da IA: {e}"
        await ctx.log(error_message, level="error")
        raise ValueError(error_message)