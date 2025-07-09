# hivemind_core/agent_loader.py (VERSÃO CORRIGIDA)
import importlib
import os
import sys
from typing import Any

async def load_agents_from_directory(agents_dir: str, hub_mcp: Any):
    """Carrega todos os agentes do diretório especificado e registra suas ferramentas no hub_mcp."""

    # --- REATORADO: Carregar o MemoryManager usando o novo padrão ---
    try:
        import hivemind_core.memory_manager
        memory_mcp = hivemind_core.memory_manager.get_agent_mcp()
        memory_tools = await memory_mcp.get_tools()
        for tool in memory_tools:
            hub_mcp.add_tool(tool)
        print(f"  -> Módulo 'MemoryManager' carregado com {len(memory_tools)} ferramentas.")
    except Exception as e:
        print(f"Erro ao carregar MemoryManager: {e}")
    # --- FIM DO BLOCO REATORADO ---

    for root, dirs, files in os.walk(agents_dir):
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")

        for file in files:
            if file.endswith('.py') and not file.startswith('__'):
                relative_path = os.path.relpath(os.path.join(root, file), os.getcwd())
                module_name = relative_path.replace(os.sep, '.')[:-3]

                try:
                    module = importlib.import_module(module_name)
                    # --- REATORADO: Usar a função get_agent_mcp para um carregamento explícito ---
                    if hasattr(module, 'get_agent_mcp'):
                        agent_mcp = module.get_agent_mcp()
                        agent_tools = await agent_mcp.get_tools()
                        for tool in agent_tools:
                            hub_mcp.add_tool(tool)
                        print(f"  -> Agente '{module_name}' carregado com {len(agent_tools)} ferramentas.")
                except Exception as e:
                    # Adiciona mais detalhes ao erro para depuração futura
                    import traceback
                    print(f"Erro ao importar ou carregar agente {module_name}: {e}")
                    print(traceback.format_exc())