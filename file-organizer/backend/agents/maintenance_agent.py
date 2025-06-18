# agents/maintenance_agent.py
import os
from pathlib import Path
from fastmcp import FastMCP, Context
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Tuple

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

@mcp.tool
async def find_duplicates(ctx: Context, directory: str) -> List[Tuple[str, List[str]]]:
    """Find duplicate files by content hash"""
    await ctx.log(f"🔍 Searching for duplicates in {directory}", level="info")
    
    hash_map: Dict[str, List[str]] = {}
    
    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    hash_map.setdefault(file_hash, []).append(filepath)
            except (IOError, OSError) as e:
                await ctx.log(f"⚠️ Could not read {filepath}: {e}", level="warning")
    
    # Filter for hashes with multiple files
    duplicates = [(h, paths) for h, paths in hash_map.items() if len(paths) > 1]
    await ctx.log(f"✅ Found {len(duplicates)} sets of duplicates", level="info")
    
    return duplicates

# Outras ferramentas de manutenção como find_anomalies podem ser adicionadas aqui.
