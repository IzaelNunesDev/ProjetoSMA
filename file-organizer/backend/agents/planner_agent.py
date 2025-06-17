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
async def create_organization_plan(directory_summaries: list[dict], user_goal: str, root_directory: str, ctx: Context) -> dict:
    """
    Cria um plano de organização de alto nível baseado nos resumos dos diretórios e no objetivo do usuário.
    O plano consiste em uma lista de ações: CREATE_FOLDER, MOVE_FOLDER, MOVE_FILE.
    """
    await ctx.log(f"Criando plano com base no objetivo: '{user_goal}' para {len(directory_summaries)} diretórios.", level="info")
    
    # MUDE AQUI PARA 'gemini-2.5-flash-lite'
    model = genai.GenerativeModel('gemini-2.5-flash-lite')

    prompt = prompt_manager.format_prompt(
        task_name="file-organization", 
        user_goal=user_goal, 
        directory_summaries=json.dumps(directory_summaries, indent=2, ensure_ascii=False),
        root_directory=root_directory
    )

    if not prompt:
        error_message = "Template de prompt 'file-organization' não encontrado."
        await ctx.log(error_message, level="error")
        raise ValueError(error_message)

    try:
        response = await model.generate_content_async(prompt)
        await ctx.log(f"📝 Resposta do planner recebida:\n{response.text}", level="debug")

        # Limpeza robusta para extrair o bloco JSON
        plan_str = response.text.strip()
        if plan_str.startswith("```json"):
            plan_str = plan_str[7:]
        if plan_str.endswith("```"):
            plan_str = plan_str[:-3]
        
        plan = json.loads(plan_str)

        if not isinstance(plan, dict) or "objective" not in plan or "steps" not in plan or not isinstance(plan["steps"], list):
            raise ValueError("Plano malformado: campo 'objective' ou 'steps' ausente ou inválido.")
            
        return plan
    except json.JSONDecodeError as e:
        error_message = f"Falha ao decodificar JSON do plano: {e}\nTexto recebido:\n{plan_str}"
        await ctx.log(error_message, level="error")
        return {"objective": "Falha no planejamento (Erro de JSON)", "steps": []}
    except Exception as e:
        error_message = f"Erro ao gerar o plano da IA: {e}"
        await ctx.log(error_message, level="error")
        return {"objective": f"Falha no planejamento ({type(e).__name__})", "steps": []}