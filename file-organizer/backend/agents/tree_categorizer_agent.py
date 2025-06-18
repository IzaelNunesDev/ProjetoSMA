# agents/tree_categorizer_agent.py
import os
import json
import google.generativeai as genai
from fastmcp import FastMCP, Context
from prompt_manager import prompt_manager

from dotenv import load_dotenv
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

mcp = FastMCP(name="TreeCategorizerAgent")

@mcp.tool
async def categorize_from_tree(tree_text: str, ctx: Context) -> dict:
    """
    Usa um LLM para analisar a árvore de diretórios e sugerir reorganizações.
    """
    prompt = prompt_manager.format_prompt("tree-categorizer", tree=tree_text)
    if not prompt:
        raise ValueError("Prompt 'tree-categorizer' não encontrado.")

    await ctx.log("Enviando árvore para análise do LLM...", level="info")
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await model.generate_content_async(prompt)
        
        json_str = response.text.strip()
        if json_str.startswith('```json'):
            json_str = json_str[7:-3].strip()

        result = json.loads(json_str)
        await ctx.log("Análise da árvore recebida do LLM.", level="info")
        return result

    except Exception as e:
        await ctx.log(f"TreeCategorizerAgent encontrou um erro: {e}", level="error")
        return {"analysis": f"Erro ao analisar: {e}", "suggestions": []}
