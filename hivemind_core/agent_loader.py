import importlib
import os
import sys
from typing import Any

async def load_agents_from_directory(agents_dir: str, hub_mcp: Any):
    """Carrega todos os agentes do diretório especificado e registra suas ferramentas no hub_mcp."""
    sys.path.insert(0, os.path.abspath(agents_dir))
    for root, dirs, files in os.walk(agents_dir):
        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                module_path = os.path.relpath(os.path.join(root, file), agents_dir)
                module_name = module_path.replace(os.sep, '.')[:-3]
                try:
                    module = importlib.import_module(module_name)
                    if hasattr(module, 'mcp'):
                        agent_mcp = getattr(module, 'mcp')
                        for tool in agent_mcp:
                            hub_mcp.add_tool(tool)
                except Exception as e:
                    print(f"Erro ao importar agente {module_name}: {e}") 