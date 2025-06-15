# agents/maintenance_agent.py
import os
from pathlib import Path
from fastmcp import FastMCP, Context

mcp = FastMCP(name="MaintenanceAgent")

@mcp.tool
async def find_empty_folders(directory_path: str, ctx: Context) -> dict:
    """Encontra e lista todas as pastas vazias dentro de um diretório."""
    root = Path(directory_path).expanduser().resolve()
    empty_folders = []
    await ctx.log(f"Verificando pastas vazias em: {root}", level="info")
    for dirpath, dirnames, filenames in os.walk(root):
        if not dirnames and not filenames:
            await ctx.log(f"Pasta vazia encontrada: {dirpath}", level="debug")
            empty_folders.append(str(dirpath))
    
    if not empty_folders:
        return {"status": "success", "message": "Nenhuma pasta vazia encontrada."}
    
    return {"status": "success", "empty_folders": empty_folders}

# Outras ferramentas de manutenção como find_duplicates e find_anomalies podem ser adicionadas aqui.
