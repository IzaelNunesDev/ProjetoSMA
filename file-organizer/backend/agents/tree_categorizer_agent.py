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
        model = genai.GenerativeModel(
            'gemini-1.5-flash',
            generation_config=genai.GenerationConfig(response_mime_type="application/json") 
        )
        response = await model.generate_content_async(prompt)
        
        result = json.loads(response.text)
        await ctx.log("Análise da árvore recebida do LLM.", level="info")
        return result

    except Exception as e:
        response_text = "N/A"
        if 'response' in locals() and hasattr(response, 'text'):
            response_text = response.text
        await ctx.log(f"TreeCategorizerAgent encontrou um erro: {e}. Resposta recebida: {response_text}", level="error")
        return {"analysis": f"Erro ao analisar: {e}", "suggestions": []}
