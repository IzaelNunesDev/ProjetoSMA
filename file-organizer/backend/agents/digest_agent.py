# agents/digest_agent.py
import os
from pathlib import Path
from fastmcp import FastMCP, Context
from gitingest.entrypoint import ingest_async

mcp = FastMCP(name="DigestAgent")

# Lista de padrões a serem sempre ignorados na análise da árvore
DEFAULT_EXCLUDE = {
    "*.exe", "*.iso", "*.db*", "*.dll", "*.so", "*.a", "*.lib",
    "*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.tiff",
    "*.zip", "*.rar", "*.7z", "*.tar", "*.gz",
    "node_modules/**", "__pycache__/**", "venv/**", ".venv/**",
    ".git/**", ".vscode/**", "target/**", "build/**", "dist/**"
}

@mcp.tool
async def get_tree_summary(root_path: str, ctx: Context) -> str:
    """
    Usa gitingest para gerar uma árvore textual da estrutura de diretórios.
    """
    try:
        await ctx.log(f"Gerando 'tree' para: {root_path}", level="info")
        # Ignoramos summary e content, focando apenas na árvore (tree)
        _, tree, _ = await ingest_async(
            source=root_path,
            exclude_patterns=DEFAULT_EXCLUDE,
            output=None
        )
        await ctx.log("Árvore de diretórios gerada com sucesso pelo DigestAgent.", level="info")
        return tree
    except Exception as e:
        await ctx.log(f"DigestAgent encontrou um erro: {e}", level="error")
        return ""
