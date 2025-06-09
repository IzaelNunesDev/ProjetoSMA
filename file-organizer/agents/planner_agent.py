# agents/planner_agent.py
import os
import google.generativeai as genai
from fastmcp import FastMCP

# Carrega a chave de API do .env
from dotenv import load_dotenv
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
mcp = FastMCP(name="PlannerAgent")

@mcp.tool
def create_organization_plan(files_metadata: list[dict], user_goal: str = "Organize por tipo de arquivo") -> list[dict]:
    """
    Cria um plano de organização de arquivos baseado nos metadados e no objetivo do usuário.
    O plano consiste em uma lista de ações: CREATE_FOLDER, MOVE_FILE.
    """
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""
    Você é um assistente especialista em organização de arquivos.
    Seu objetivo é criar um plano de organização estruturado em JSON com base na lista de metadados de arquivos fornecida.
    O objetivo do usuário é: "{user_goal}".

    As ações permitidas são:
    1. {{ "action": "CREATE_FOLDER", "path": "caminho/completo/para/a/nova/pasta" }}
    2. {{ "action": "MOVE_FILE", "from": "caminho/original/arquivo.ext", "to": "caminho/novo/arquivo.ext" }}

    Analise os seguintes metadados de arquivos e crie o plano:
    {files_metadata}

    Retorne APENAS a lista JSON do plano, nada mais.
    """

    response = model.generate_content(prompt)
    
    # Limpa a resposta do LLM para extrair apenas o JSON
    import json
    try:
        plan_str = response.text.strip().replace("```json", "").replace("```", "")
        plan = json.loads(plan_str)
        return plan
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"Erro ao decodificar o plano: {e}")
        return [{"action": "ERROR", "details": str(e)}]


if __name__ == "__main__":
    print("PlannerAgent rodando...")
    mcp.run()
