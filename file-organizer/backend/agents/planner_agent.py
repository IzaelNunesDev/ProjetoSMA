import os
import json
import google.generativeai as genai
from fastmcp import FastMCP, Context  # Importar FastMCP
from prompt_manager import prompt_manager
from pathlib import Path
from typing import Optional

# Carrega a chave de API do .env
from dotenv import load_dotenv
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# É crucial criar uma instância do MCP para este agente
mcp = FastMCP(name="PlannerAgent")

@mcp.tool
async def create_organization_plan(
    user_goal: str, 
    root_directory: str, 
    ctx: Context,
    directory_summaries: Optional[list[dict]] = None, 
    files_metadata: Optional[list[dict]] = None
) -> dict:
    """
    Cria um plano de organização com base em resumos de diretórios (para pastas estruturadas)
    ou em uma lista detalhada de arquivos (para pastas planas/bagunçadas).
    O plano consiste em uma lista de ações: CREATE_FOLDER, MOVE_FOLDER, MOVE_FILE.
    """
    
    if not directory_summaries and not files_metadata:
        raise ValueError("É necessário fornecer 'directory_summaries' ou 'files_metadata'.")

    log_message = f"Criando plano com base no objetivo: '{user_goal}'. "
    if directory_summaries:
        log_message += f"Analisando {len(directory_summaries)} resumos de diretórios."
    else:
        log_message += f"Analisando {len(files_metadata)} arquivos individuais."
    await ctx.log(log_message, level="info")

    model = genai.GenerativeModel('gemini-1.5-flash')

    # Constrói o dicionário de substituições dinamicamente
    prompt_data = {
        "user_goal": user_goal,
        "root_directory": root_directory,
        # Inclui as chaves apenas se os dados não forem None ou vazios
        "directory_summaries": json.dumps(directory_summaries, indent=2, ensure_ascii=False) if directory_summaries else None,
        "files_metadata": json.dumps(files_metadata, indent=2, ensure_ascii=False) if files_metadata else None,
    }

    prompt = prompt_manager.format_prompt(
        task_name="file-organization", 
        **{k: v for k, v in prompt_data.items() if v is not None} # Passa apenas as chaves com valor
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