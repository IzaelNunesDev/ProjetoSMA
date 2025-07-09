# agents/file_organizer/main.py (VERSÃO OTIMIZADA PARA DEMONSTRAÇÃO)

import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import google.generativeai as genai
from fastmcp import FastMCP, Context

# --- Início dos Utilitários de Regras (Rápido e Eficiente) ---
RULES = {
    "Imagens": {"extensions": [".jpg", ".jpeg", ".png", ".gif", ".svg", ".bmp", ".tiff"]},
    "Documentos": {"extensions": [".pdf", ".docx", ".doc", ".txt", ".md", ".odt"]},
    "Instaladores": {"extensions": [".exe", ".msi", ".dmg"]},
    "Arquivos Compactados": {"extensions": [".zip", ".rar", ".7z", ".tar.gz", ".gz"]}
}

def _apply_rules(items: List[Dict]) -> Tuple[Dict[str, str], List[Dict]]:
    categorized_by_rules = {}
    remaining_items = []
    for item in items:
        path = Path(item['path'])
        # Usa ''.join(path.suffixes) para lidar com extensões duplas como .tar.gz
        ext = ''.join(path.suffixes).lower()
        categorized = False
        for category, rule in RULES.items():
            if ext in rule.get("extensions", []):
                categorized_by_rules[item['path']] = category
                categorized = True
                break
        if not categorized:
            remaining_items.append(item)
    return categorized_by_rules, remaining_items
# --- Fim dos Utilitários de Regras ---


# --- Configuração do Agente ---
mcp = FastMCP(name="FileOrganizerAgent")

@mcp.tool
async def _scan_directory_fast(directory_path: str, ctx: Context) -> list[dict]:
    """Escaneia um diretório rapidamente, coletando apenas caminhos e metadados básicos."""
    await ctx.log(f"Iniciando escaneamento rápido em: {directory_path}", level="info")
    root = Path(directory_path).expanduser().resolve()
    resultados = []
    EXCLUDED_DIRS = {"node_modules", "venv", ".venv", "__pycache__", ".git", ".vscode"}
    
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        current_dir = Path(dirpath)
        
        for name in filenames:
            file_path = current_dir / name
            try:
                # Coleta apenas o necessário para a categorização
                metadata = {"path": str(file_path)}
                resultados.append(metadata)
            except Exception:
                continue # Ignora arquivos que não podem ser lidos
    await ctx.log(f"Escaneamento rápido concluído. {len(resultados)} itens encontrados.", level="info")
    return resultados

@mcp.tool
async def _categorize_with_llm(user_goal: str, items_to_categorize: list, ctx: Context) -> Dict[str, str]:
    """Usa um LLM para categorizar itens com base APENAS em seus caminhos."""
    if not items_to_categorize: return {}
    
    # ## MUDANÇA PRINCIPAL ##: Enviamos apenas a lista de caminhos, não o conteúdo.
    paths_only = [item['path'] for item in items_to_categorize]
    
    await ctx.log(f" Categorizando {len(paths_only)} itens com IA (baseado em nomes)...", level="info")
    
    prompt = f"""
    Sua tarefa é categorizar a seguinte lista de arquivos com base em seus nomes, extensões e caminhos, de acordo com o objetivo do usuário.
    Objetivo: "{user_goal}"
    
    Lista de caminhos dos arquivos:
    {json.dumps(paths_only, indent=2)}

    Retorne APENAS um objeto JSON onde a chave é o caminho completo do arquivo e o valor é a string da categoria de destino (ex: "Projetos de Jogo", "Relatórios Financeiros", "Fotos de Viagem").
    Se não souber, use a categoria "_a_revisar".
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = await model.generate_content_async(prompt)
        json_str = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(json_str)
    except (json.JSONDecodeError, IndexError) as e:
        await ctx.log(f"Erro ao decodificar resposta do LLM: {e}\nResposta: {response.text}", level="error")
        return {}

@mcp.tool
async def _build_plan(root_directory: str, categorization_map: Dict[str, str]) -> Dict:
    """Constrói um plano de ações (CREATE, MOVE) a partir de um mapa de categorização."""
    steps = []
    root_dir = Path(root_directory)
    destination_categories = set(cat for cat in categorization_map.values() if cat != "_a_revisar")

    for category in sorted(list(destination_categories)):
        safe_category_name = category.replace("/", "-").replace("\\", "-").strip()
        if not safe_category_name: continue
        dest_path = root_dir / safe_category_name
        steps.append({"action": "CREATE_FOLDER", "path": str(dest_path)})

    for original_path_str, category in categorization_map.items():
        if category == "_a_revisar": continue
        
        original_path = Path(original_path_str)
        safe_category_name = category.replace("/", "-").replace("\\", "-").strip()
        dest_folder = root_dir / safe_category_name
        to_path = str(dest_folder / original_path.name)
        
        steps.append({"action": "MOVE_FILE", "from": str(original_path), "to": to_path})

    return {
        "objective": f"Plano para organizar {len(steps)} ações em {len(destination_categories)} categorias.",
        "steps": steps,
        "root_directory": root_directory
    }

@mcp.tool
async def generate_organization_plan(directory_path: str, user_goal: str, ctx: Context) -> dict:
    """Orquestra o processo completo de geração de um plano de organização para um diretório."""
    await ctx.log(f"Iniciando geração de plano para: '{directory_path}'", level="info")
    
    # 1. SCAN RÁPIDO
    scan_results = await _scan_directory_fast.fn(directory_path=directory_path, ctx=ctx)
    if not scan_results:
        return {"status": "completed", "message": "Nenhum arquivo encontrado.", "plan": None}
    
    # 2. REGRAS
    rule_map, items_for_llm = _apply_rules(scan_results)
    await ctx.log(f"{len(rule_map)} itens categorizados por regras.", level="info")

    # 3. LLM (RÁPIDO)
    llm_map = await _categorize_with_llm.fn(user_goal=user_goal, items_to_categorize=items_for_llm, ctx=ctx)
    
    # 4. COMBINAR E CONSTRUIR PLANO
    full_categorization_map = {**rule_map, **llm_map}
    if not full_categorization_map:
        return {"status": "error", "message": "Não foi possível categorizar nenhum arquivo.", "plan": None}

    plan = await _build_plan.fn(root_directory=directory_path, categorization_map=full_categorization_map)
    
    # 5. POSTAR NO HIVE MIND
    await ctx.hub.call_tool("post_entry", entry={
        "entry_id": str(uuid.uuid4()), "agent_name": mcp.name,
        "entry_type": "ORGANIZATION_PLAN", "timestamp": datetime.utcnow().isoformat(),
        "content": f"Plano de organização gerado para '{Path(directory_path).name}' com o objetivo '{user_goal}'. O plano contém {len(plan.get('steps', []))} passos.",
        "context": {"directory": directory_path, "goal": user_goal, "plan": plan},
        "tags": ["organization", "planning", "suggestion"], "utility_score": 0.0, "references_entry_id": None
    })
    await ctx.log("Plano gerado e registrado no Hive Mind.", level="info")

    return {"status": "plan_generated", "plan": plan}

def get_agent_mcp():
    return mcp