# agents/executor_agent.py
import os
import shutil
from pathlib import Path
from fastmcp import FastMCP

mcp = FastMCP(name="ExecutorAgent")

@mcp.tool
def create_folder(path: str) -> dict:
    """
    Create a directory at the specified path if it does not already exist.

    Args:
        path (str): The path where the directory should be created.

    Returns:
        dict: A dictionary containing the status of the operation. 
              If successful, includes the action and path. 
              If an error occurs, includes the error details.
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return {"status": "success", "action": "create_folder", "path": path}
    except Exception as e:
        return {"status": "error", "details": str(e)}

@mcp.tool
def move_file(source_path: str, destination_path: str) -> dict:
    """Move um arquivo da origem para o destino."""
    try:
        # Garante que a pasta de destino exista
        Path(destination_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source_path, destination_path)
        return {"status": "success", "action": "move_file", "from": source_path, "to": destination_path}
    except Exception as e:
        return {"status": "error", "details": str(e)}

if __name__ == "__main__":
    print("ExecutorAgent rodando...")
    mcp.run()
