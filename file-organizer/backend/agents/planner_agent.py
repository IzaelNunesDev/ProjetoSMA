# file-organizer/backend/agents/planner_agent.py

import os
import json
import google.generativeai as genai
from fastmcp import FastMCP, Context
from prompt_manager import prompt_manager
from pathlib import Path
from typing import Optional, Dict, List

# Carrega a chave de API do .env
from dotenv import load_dotenv
load_dotenv()
if os.getenv("GEMINI_API_KEY"):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

mcp = FastMCP(name="PlannerAgent") # Nome alterado para clareza

# A função create_organization_plan (que usava LLM) foi removida,
# pois a nova arquitetura divide Scan -> Rules -> Categorizer -> Planner(Deterministic).
# Esta função agora é a única e principal ferramenta do agente.

@mcp.tool
async def build_plan_from_categorization(
    root_directory: str,
    categorization_map: Dict[str, str],
    ctx: Context
) -> Dict:
    """
    Constrói um plano de ações executável (CREATE, MOVE) a partir de um mapa de categorização,
    resolvendo conflitos de movimento aninhado de forma robusta.
    Esta função NÃO usa um LLM e é o cérebro da construção do plano.
    """
    await ctx.log("🛠️ Construindo plano de execução a partir das categorias...", level="info")
    steps = []
    root_dir = Path(root_directory)

    # --- INÍCIO DA LÓGICA DE FILTRAGEM DEFINITIVA ---
    await ctx.log("   - Resolvendo conflitos de movimento aninhado...", level="debug")

    # Ordena os caminhos pelo número de partes (do mais curto para o mais longo).
    # Isso garante que os pais (ex: 'a/b') sejam processados antes dos filhos ('a/b/c').
    sorted_paths = sorted(categorization_map.keys(), key=lambda p: len(Path(p).parts))
    
    final_categorization_map = {}
    paths_already_included_in_a_move = set()

    for path_str in sorted_paths:
        current_path = Path(path_str)
        
        # Se este caminho já foi "engolido" por um movimento de um pai, pule-o.
        if current_path in paths_already_included_in_a_move:
            await ctx.log(f"   - Ignorando movimento de '{current_path.name}' pois já faz parte de um movimento maior.", level="debug")
            continue

        # Adiciona o movimento principal ao mapa final.
        final_categorization_map[path_str] = categorization_map[path_str]

        # Se o item movido for um diretório, marque todos os seus descendentes diretos
        # no mapa de categorização original como "já incluídos".
        if current_path.is_dir():
            for other_path_str in categorization_map.keys():
                other_path = Path(other_path_str)
                if current_path in other_path.parents:
                    paths_already_included_in_a_move.add(other_path)
    
    await ctx.log(f"   - Plano será construído com {len(final_categorization_map)} ações de movimento principais.", level="info")
    # --- FIM DA LÓGICA DE FILTRAGEM ---

    # 1. Identificar todas as pastas de destino necessárias A PARTIR DO MAPA FILTRADO
    destination_categories = set(final_categorization_map.values())
    
    # 2. Criar as pastas de destino (CREATE_FOLDER)
    for category in sorted(list(destination_categories)):
        if category == "_a_revisar":
            dest_path = root_dir / "_A_REVISAR"
        else:
            # Garante que o nome da categoria seja seguro para um nome de pasta
            safe_category_name = category.replace("/", "-").replace("\\", "-").strip()
            dest_path = root_dir / safe_category_name
        
        steps.append({"action": "CREATE_FOLDER", "path": str(dest_path)})

    # 3. Criar as ações de movimento (MOVE_FOLDER e MOVE_FILE) USANDO O MAPA FILTRADO
    for original_path_str, category in final_categorization_map.items():
        original_path = Path(original_path_str)
        safe_category_name = category.replace("/", "-").replace("\\", "-").strip()
        
        if category == "_a_revisar":
            dest_folder = root_dir / "_A_REVISAR"
        else:
            dest_folder = root_dir / safe_category_name

        if original_path.is_dir():
            steps.append({
                "action": "MOVE_FOLDER",
                "from": str(original_path),
                "to": str(dest_folder) # O destino é a pasta categoria
            })
        elif original_path.is_file():
            steps.append({
                "action": "MOVE_FILE",
                "from": str(original_path),
                "to": str(dest_folder / original_path.name)
            })

    plan_object = {
        "objective": f"Organizar {len(final_categorization_map)} itens principais em {len(destination_categories)} categorias.",
        "steps": steps,
        "root_directory": root_directory
    }
    
    await ctx.log(f"✅ Plano de execução robusto construído com {len(steps)} ações.", level="info")
    return plan_object