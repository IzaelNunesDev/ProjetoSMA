# izaelnunesdev-projetosma/agents/file_organizer/main.py (VERSÃO CORRIGIDA E ROBUSTA)

import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any
import google.generativeai as genai
from fastmcp import FastMCP, Context

# --- Regras de categorização rápida permanecem, são muito eficientes. ---
RULES = {
    "Imagens": {"extensions": [".jpg", ".jpeg", ".png", ".gif", ".svg", ".bmp", ".tiff"]},
    "Documentos": {"extensions": [".pdf", ".docx", ".doc", ".txt", ".md", ".odt"]},
    "Vídeos": {"extensions": [".mp4", ".mov", ".avi", ".mkv"]},
    "Instaladores": {"extensions": [".exe", ".msi", ".dmg"]},
    "Arquivos Compactados": {"extensions": [".zip", ".rar", ".7z", ".tar.gz", ".gz"]}
}

def _apply_rules(items: List[Dict]) -> Tuple[Dict[str, str], List[Dict]]:
    categorized_by_rules = {}
    remaining_items = []
    for item in items:
        if item.get("type") == "file":
            path = Path(item['path'])
            ext = ''.join(path.suffixes).lower()
            categorized = False
            for category, rule in RULES.items():
                if ext in rule.get("extensions", []):
                    categorized_by_rules[item['path']] = category
                    categorized = True
                    break
            if not categorized:
                remaining_items.append(item)
        else:
            remaining_items.append(item)
    return categorized_by_rules, remaining_items

# --- Configuração do Agente ---
mcp = FastMCP(name="FileOrganizerAgent")

async def _get_item_details(item_path: Path, ctx: Context) -> Dict[str, Any]:
    details = {"path": str(item_path)}
    try:
        if item_path.is_dir():
            details["type"] = "folder"
            peek_contents = [p.name for p in item_path.iterdir() if not p.name.startswith('.')]
            details["sample_contents"] = peek_contents[:10]
        elif item_path.is_file():
            details["type"] = "file"
    except Exception as e:
        await ctx.log(f"Não foi possível acessar {item_path}: {e}", level="warning")
        details["type"] = "inaccessible"
    return details

@mcp.tool
async def _scan_and_detail_root_level(directory_path: str, ctx: Context) -> list[dict]:
    await ctx.log(f"Iniciando escaneamento superficial em: {directory_path}", level="info")
    root = Path(directory_path).expanduser().resolve()
    detailed_items = []
    try:
        for item_path in root.iterdir():
            if item_path.name.startswith('.'):
                continue
            details = await _get_item_details(item_path, ctx)
            detailed_items.append(details)
    except Exception as e:
        await ctx.log(f"Erro ao escanear diretório: {e}", level="error")
        return []
    await ctx.log(f"Escaneamento superficial concluído. {len(detailed_items)} itens detalhados.", level="info")
    return detailed_items

@mcp.tool
async def _categorize_with_llm(user_goal: str, items_to_categorize: list, ctx: Context) -> Dict[str, str]:
    if not items_to_categorize:
        return {}
    await ctx.log(f"Iniciando categorização com IA para {len(items_to_categorize)} itens...", level="info")
    prompt = f"""
    Você é um especialista em organização de arquivos. Sua tarefa é categorizar a seguinte lista de itens com base no objetivo do usuário e nas pistas fornecidas.
    **Objetivo do Usuário:** "{user_goal}"
    **Itens para Categorizar:**
    ```json
    {json.dumps(items_to_categorize, indent=2)}
    ```
    **Instruções:**
    1. Analise cada item no JSON. Para "folder", use `sample_contents`. Para "file", use o nome/extensão.
    2. Crie nomes de categoria lógicos (ex: "Projetos Python", "Documentos Fiscais", "Fotos de Viagem").
    3. Se um item não tiver categoria clara, atribua a categoria "_a_revisar".
    4. Sua resposta deve ser **APENAS** um único objeto JSON onde a chave é o caminho completo do item (`path`) e o valor é a string da categoria de destino.
    **Exemplo de Saída JSON:**
    ```json
    {{
      "/path/to/downloads/my-node-project": "Projetos Web",
      "/path/to/downloads/relatorio.pdf": "Documentos",
      "/path/to/downloads/fotos_ferias": "Fotos de Viagem"
    }}
    ```
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await model.generate_content_async(prompt)
        json_str = response.text.strip()
        if json_str.startswith('```json'):
            json_str = json_str[7:-3].strip()
        categorization_map = json.loads(json_str)
        await ctx.log(f"Categorização com IA concluída. {len(categorization_map)} itens categorizados.", level="info")
        return categorization_map
    except Exception as e:
        response_text = "N/A"
        if 'response' in locals() and hasattr(response, 'text'):
            response_text = response.text
        # LOG DE ERRO MELHORADO:
        await ctx.log(f"!!!!!! ERRO CRÍTICO AO CATEGORIZAR COM IA !!!!!!", level="error")
        await ctx.log(f"Erro: {e}", level="error")
        await ctx.log(f"Resposta recebida da API que causou o erro: {response_text}", level="error")
        return {}

# --- A CORREÇÃO PRINCIPAL ESTÁ AQUI ---
@mcp.tool
async def _build_plan(root_directory: str, categorization_map: Dict[str, str], ctx: Context) -> Dict:
    """Constrói um plano de ações (CREATE, MOVE) a partir de um mapa de categorização."""
    await ctx.log("Construindo plano de execução a partir das categorias...", level="info")
    steps = []
    root_dir = Path(root_directory)
    destination_categories = set(cat for cat in categorization_map.values() if cat != "_a_revisar")

    # 1. Criar as pastas de destino
    for category in sorted(list(destination_categories)):
        safe_category_name = category.replace("/", "-").replace("\\", "-").strip()
        if not safe_category_name: continue
        dest_path = root_dir / safe_category_name
        steps.append({"action": "CREATE_FOLDER", "path": str(dest_path)})

    # 2. Criar as ações de movimento
    for original_path_str, category in categorization_map.items():
        if category == "_a_revisar": continue
        
        original_path = Path(original_path_str)
        safe_category_name = category.replace("/", "-").replace("\\", "-").strip()
        dest_folder = root_dir / safe_category_name
        
        # LÓGICA CORRIGIDA:
        if original_path.is_dir():
            # O destino de uma pasta é a pasta da categoria PAI.
            # O executor (ex: shutil.move) moverá a pasta original para DENTRO dela.
            # ANTES (ERRADO): "to": str(dest_folder / original_path.name)
            # AGORA (CORRETO): "to": str(dest_folder)
            steps.append({
                "action": "MOVE_FOLDER",
                "from": str(original_path),
                "to": str(dest_folder) 
            })
        elif original_path.is_file():
            # O destino de um arquivo é o caminho completo DENTRO da pasta de categoria.
            steps.append({
                "action": "MOVE_FILE",
                "from": str(original_path),
                "to": str(dest_folder / original_path.name)
            })

    plan_object = {
        "objective": f"Plano para executar {len(steps)} ações em {len(destination_categories)} categorias.",
        "steps": steps,
        "root_directory": root_directory
    }
    await ctx.log(f"Plano de execução construído com {len(steps)} passos.", level="info")
    return plan_object

@mcp.tool
async def generate_organization_plan(directory_path: str, user_goal: str, ctx: Context) -> dict:
    """Orquestra o processo completo e RÁPIDO de geração de um plano de organização."""
    await ctx.log(f"Iniciando geração de plano para: '{directory_path}'", level="info")
    
    items_to_process = await _scan_and_detail_root_level.fn(directory_path=directory_path, ctx=ctx)
    if not items_to_process:
        return {"status": "completed", "message": "Nenhum arquivo ou pasta encontrado na raiz do diretório.", "plan": None}
    
    rule_map, items_for_llm = _apply_rules(items_to_process)
    await ctx.log(f"{len(rule_map)} arquivos categorizados por regras.", level="info")

    llm_map = {}
    if items_for_llm:
        llm_map = await _categorize_with_llm.fn(user_goal=user_goal, items_to_categorize=items_for_llm, ctx=ctx)
    
    full_categorization_map = {**rule_map, **llm_map}
    if not full_categorization_map:
        await ctx.log("O mapa de categorização final está vazio. Nenhum item foi categorizado por regras ou pela IA. Interrompendo.", level="error")
        return {"status": "error", "message": "Não foi possível categorizar nenhum item. Verifique os logs para erros da IA.", "plan": None}

    plan = await _build_plan.fn(root_directory=directory_path, categorization_map=full_categorization_map, ctx=ctx)
    
    try:
        await ctx.hub.call_tool("post_entry", entry={
            "entry_id": str(uuid.uuid4()), "agent_name": mcp.name,
            "entry_type": "ORGANIZATION_PLAN", "timestamp": datetime.utcnow().isoformat(),
            "content": f"Plano gerado para '{Path(directory_path).name}'. Passos: {len(plan.get('steps', []))}",
            "context": {"directory": directory_path, "goal": user_goal, "plan": plan},
            "tags": ["organization", "planning", "suggestion"], "utility_score": 0.0, "references_entry_id": None
        })
        await ctx.log("Plano gerado e registrado no Hive Mind.", level="info")
    except Exception as e:
         await ctx.log(f"Aviso: Falha ao registrar plano no Hive Mind: {e}", level="warning")

    return {"status": "plan_generated", "plan": plan}

def get_agent_mcp():
    return mcp