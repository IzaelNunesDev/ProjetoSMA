import importlib
import os
import sys
from typing import Any

async def load_agents_from_directory(agents_dir: str, hub_mcp: Any):
    """Carrega todos os agentes do diretório especificado e registra suas ferramentas no hub_mcp."""
    # A adição ao sys.path pode ser feita no main_hub.py para maior clareza
    # sys.path.insert(0, os.path.abspath(agents_dir))
    
    for root, dirs, files in os.walk(agents_dir):
        # Ignora __pycache__ para evitar erros de importação
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")

        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                # Constrói o nome do módulo a partir do caminho relativo
                relative_path = os.path.relpath(os.path.join(root, file), os.getcwd())
                module_name = relative_path.replace(os.sep, '.')[:-3]

                try:
                    module = importlib.import_module(module_name)
                    if hasattr(module, 'mcp'):
                        agent_mcp = getattr(module, 'mcp')
                        # CORREÇÃO AQUI: Chamar o método get_tools()
                        tools = await agent_mcp.get_tools()
                        for tool in tools:
                            hub_mcp.add_tool(tool)
                        print(f"  -> Agente '{module_name}' carregado com {len(tools)} ferramentas.")
                except Exception as e:
                    print(f"Erro ao importar agente {module_name}: {e}")