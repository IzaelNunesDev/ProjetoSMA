# hivemind_core/agent_loader.py (VERSÃO CORRIGIDA)
import importlib
import os
import json
from typing import Any
import traceback

async def load_agents_from_directory(hub_mcp: Any):
    """Carrega todos os agentes dos diretórios 'core_agents' e 'agents' e registra suas ferramentas no hub_mcp."""
    
    agent_base_dirs = ['core_agents', 'agents']

    for base_dir in agent_base_dirs:
        if not os.path.isdir(base_dir):
            print(f"AVISO: Diretório de agentes '{base_dir}' não encontrado. Pulando.")
            continue

        for agent_name in os.listdir(base_dir):
            agent_path = os.path.join(base_dir, agent_name)
            if os.path.isdir(agent_path):
                main_py_path = os.path.join(agent_path, 'main.py')
                if not os.path.exists(main_py_path):
                    continue

                module_name = f"{base_dir}.{agent_name}.main"
                try:
                    module = importlib.import_module(module_name)
                    
                    # PADRÃO CORRIGIDO: Usar get_agent_mcp() para obter a instância do agente
                    if hasattr(module, 'get_agent_mcp'):
                        agent_mcp = module.get_agent_mcp()
                        # Acessa diretamente o dicionário de ferramentas para obter os objetos completos
                        agent_tools_dict = agent_mcp._tool_manager._tools
                        
                        for tool_object in agent_tools_dict.values():
                            hub_mcp.add_tool(tool_object)
                        
                        if agent_tools_dict:
                            print(f"  -> Módulo '{agent_name}' ({base_dir}) carregado com {len(agent_tools_dict)} ferramentas.")
                    else:
                        print(f"AVISO: Agente '{agent_name}' não possui a função get_agent_mcp(). Nenhuma ferramenta carregada.")

                except Exception as e:
                    print(f"Erro ao carregar agente de '{agent_name}' em '{base_dir}': {e}")
                    print(traceback.format_exc())