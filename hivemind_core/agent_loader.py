# hivemind_core/agent_loader.py (VERSÃO FINAL UNIFICADA)
import importlib
import os
import json
from typing import Any

async def load_agents_from_directory(hub_mcp: Any):
    """Carrega todos os agentes dos diretórios 'core_agents' e 'agents' e registra suas ferramentas no hub_mcp."""
    
    agent_base_dirs = ['core_agents', 'agents']

    for base_dir in agent_base_dirs:
        if not os.path.isdir(base_dir):
            print(f"AVISO: Diretório de agentes '{base_dir}' não encontrado. Pulando.")
            continue

        # Itera sobre as pastas dos agentes
        for agent_name in os.listdir(base_dir):
            agent_path = os.path.join(base_dir, agent_name)
            if os.path.isdir(agent_path):
                manifest_path = os.path.join(agent_path, 'manifest.json')
                main_py_path = os.path.join(agent_path, 'main.py')

                if os.path.exists(manifest_path) and os.path.exists(main_py_path):
                    # O nome do módulo agora inclui o diretório base (core_agents ou agents)
                    module_name = f"{base_dir}.{agent_name}.main"
                    try:
                        # Carrega o manifesto
                        with open(manifest_path, 'r') as f:
                            manifest = json.load(f)
                        
                        supported_tools_names = manifest.get("supported_tools", [])
                        
                        # Importa o módulo do agente
                        module = importlib.import_module(module_name)
                        importlib.reload(module) # Garante que a versão mais recente seja carregada

                        # Busca os objetos de ferramenta reais no módulo
                        tools_added_count = 0
                        for tool_name in supported_tools_names:
                            if hasattr(module, tool_name):
                                tool_obj = getattr(module, tool_name)
                                hub_mcp.add_tool(tool_obj)
                                tools_added_count += 1
                            else:
                                print(f"AVISO: Ferramenta '{tool_name}' listada no manifesto de '{agent_name}' mas não encontrada no módulo.")
                        
                        if tools_added_count > 0:
                            print(f"  -> Módulo '{agent_name}' ({base_dir}) carregado com {tools_added_count} ferramentas.")

                    except Exception as e:
                        import traceback
                        print(f"Erro ao carregar agente de '{agent_name}' em '{base_dir}': {e}")
                        print(traceback.format_exc())