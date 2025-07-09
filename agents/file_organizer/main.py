import os
import json
import google.generativeai as genai
from fastmcp import FastMCP, Context
from gitingest import ingest_async
from hivemind_core.prompt_manager import prompt_manager

# Configuração do agente
mcp = FastMCP(name="FileOrganizerAgent")

# Excluir padrões comuns para a análise da árvore
default_exclude = {
    "*.exe", "*.iso", "*.db*", "*.dll", "*.so", "*.zip", "*.rar",
    "*.jpg", "*.png", "*.gif", "node_modules/**", "__pycache__/**",
    "venv/**", ".venv/**", ".git/**", "target/**", "build/**"
}

@mcp.tool
async def get_tree_summary(root_path: str, ctx: Context) -> str:
    """Usa gitingest para gerar uma árvore textual da estrutura de diretórios."""
    try:
        await ctx.log(f"Gerando 'tree' para: {root_path}", level="info")
        _, tree, _ = await ingest_async(
            source=root_path,
            exclude_patterns=default_exclude,
            output=None
        )
        return tree
    except Exception as e:
        await ctx.log(f"Erro ao gerar árvore: {e}", level="error")
        return ""

@mcp.tool
async def categorize_from_tree(tree_text: str, ctx: Context) -> dict:
    """Usa um LLM para analisar a árvore de diretórios e sugerir reorganizações."""
    prompt = prompt_manager.format_prompt("tree-categorizer", tree=tree_text)
    if not prompt:
        raise ValueError("Prompt 'tree-categorizer' não encontrado.")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash',
            generation_config=genai.GenerationConfig(response_mime_type="application/json"))
        response = await model.generate_content_async(prompt)
        return json.loads(response.text)
    except Exception as e:
        await ctx.log(f"Erro na análise do LLM: {e}", level="error")
        return {"analysis": f"Erro ao analisar: {e}", "suggestions": []}

@mcp.tool
async def analyze_directory_structure(directory_path: str, ctx: Context) -> dict:
    """Orquestra o fluxo de análise de estrutura de diretórios."""
    await ctx.log("Iniciando análise de estrutura...", level="info")
    
    tree_text = await get_tree_summary.fn(root_path=directory_path, ctx=ctx)
    if not tree_text:
        msg = "Falha ao gerar a estrutura de diretórios. O diretório pode estar inacessível."
        await ctx.log(msg, level="error")
        return {"status": "error", "details": msg}
    
    await ctx.log(f"Estrutura detectada:\n{tree_text}", level="info")
    
    suggestions = await categorize_from_tree.fn(tree_text=tree_text, ctx=ctx)
    
    await ctx.log("Análise concluída.", level="info")
    return {
        "status": "completed",
        "tree": tree_text,
        "result": suggestions
    }

# Exportação explícita do MCP para o loader
__all__ = ["mcp"] 