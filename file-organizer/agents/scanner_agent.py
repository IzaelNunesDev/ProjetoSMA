# agents/scanner_agent.py
import os
from pathlib import Path
from fastmcp import FastMCP, Context

mcp = FastMCP(name="ScannerAgent")

@mcp.tool
async def scan_directory(directory_path: str, ctx: Context) -> list[dict]:
    """
    Escaneia um diretório e retorna metadados sobre cada arquivo, logando o progresso.
    """
    await ctx.log(f"🔍 Analisando o conteúdo de: {directory_path}", level="info")
    
    files_metadata = []
    try:
        abs_path = Path(directory_path).expanduser().resolve()

        if not abs_path.is_dir():
            await ctx.log(f"O caminho especificado não é um diretório válido: {directory_path}", level="error")
            raise ValueError("O caminho especificado não é um diretório válido.")

        for root, _, files in os.walk(abs_path):
            for file in files:
                file_path = Path(root) / file
                files_metadata.append({
                    "path": str(file_path),
                    "name": file,
                    "size_kb": round(file_path.stat().st_size / 1024, 2),
                    "ext": file_path.suffix.lower(),
                    "modified_at": file_path.stat().st_mtime
                })
        
        await ctx.log(f"encontrados {len(files_metadata)} arquivos.", level="info")
        return files_metadata
    except Exception as e:
        await ctx.log(f"Falha ao escanear o diretório: {e}", level="error")
        raise
