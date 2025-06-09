# agents/scanner_agent.py
import os
from pathlib import Path
from fastmcp import FastMCP

mcp = FastMCP(name="ScannerAgent")

@mcp.tool
def scan_directory(directory_path: str) -> list[dict]:
    """
    Escaneia um diretório e retorna metadados sobre cada arquivo.
    """
    files_metadata = []
    abs_path = Path(directory_path).expanduser().resolve()

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
    return files_metadata

if __name__ == "__main__":
    print("ScannerAgent rodando...")
    mcp.run()
