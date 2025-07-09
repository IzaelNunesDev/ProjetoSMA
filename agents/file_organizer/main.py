# izaelnunesdev-projetosma/agents/file_organizer/main.py (VERSÃO OTIMIZADA E RÁPIDA)

import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import google.generativeai as genai
from fastmcp import FastMCP, Context

# --- MUDANÇA 1: Regras de categorização rápida permanecem, são muito eficientes. ---
RULES = {
    "Imagens": {"extensions": [".jpg", ".jpeg", ".png", ".gif", ".svg", ".bmp", ".tiff"]},
    "Documentos": {"extensions": [".pdf", ".docx", ".doc", ".txt", ".md", ".odt"]},
    "Vídeos": {"extensions": [".mp4", ".mov", ".avi", ".mkv"]},
    "Instaladores": {"extensions": [".exe", ".msi", ".dmg"]},
    "Arquivos Compactados": {"extensions": [".zip", ".rar", ".7z", ".tar.gz", ".gz"]}
}

def _apply_rules(items: List[Dict]) -> Tuple[Dict[str, str], List[Dict]]:
    """Aplica regras de categorização baseadas em extensão para arquivos."""
    categorized_by_rules = {}
    remaining_items = []
    for item in items:
        path = Path(item['path'])
        # Ignora pastas nesta fase, apenas arquivos são categorizados por regras
        if path.is_file():
            # Usa a extensão completa (ex: .tar.gz)
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
            # Pastas sempre vão para a análise do LLM
            remaining_items.append(item)
            
    return categorized_by_rules, remaining_items

# --- Configuração do Agente ---
mcp = FastMCP(name="FileOrganizerAgent")

# --- MUDANÇA 2: Scan super otimizado que pega apenas itens da raiz. ---
@mcp.tool
async def _scan_root_level(directory_path: str, ctx: Context) -> list[dict]:
    """Escaneia apenas o primeiro nível de um diretório, coletando arquivos e subpastas."""
    await ctx.log(f"Iniciando escaneamento superficial em: {directory_path}", level="info")
    root = Path(directory_path).expanduser().resolve()
    items = []
    try:
        for item_path in root.iterdir():
            # Ignora arquivos/pastas ocultas (como .git, .vscode)
            if item_path.name.startswith('.'):
                continue
            items.append({"path": str(item_path)})
    except Exception as e:
        await ctx.log(f"Erro ao escanear diretório: {e}", level="error")
        return []
    
    await ctx.log(f"Escaneamento superficial concluído. {len(items)} itens encontrados na raiz.", level="info")
    return items

# --- MUDANÇA 3: Uma ÚNICA chamada de LLM para categorizar tudo de uma vez. ---
@mcp.tool
async def _categorize_with_llm(user_goal: str, items_to_categorize: list, ctx: Context) -> Dict[str, str]:
    """Usa o LLM para categorizar uma lista de itens com uma única chamada de API."""
    if not items_to_categorize:
        return {}

    # Extrai apenas os caminhos para um prompt mais limpo
    paths_only = [item['path'] for item in items_to_categorize]

    await ctx.log(f"Iniciando categorização com IA para {len(paths_only)} itens restantes...", level="info")

    # Prompt otimizado para uma única resposta JSON
    prompt = f"""
    Você é um especialista em organização de arquivos. Sua tarefa é categorizar a seguinte lista de arquivos e pastas com base no objetivo do usuário.

    **Objetivo do Usuário:** "{user_goal}"
    
    **Itens para Categorizar:**
    ```json
    {json.dumps(paths_only, indent=2)}
    ```

    **Instruções:**
    1. Analise cada caminho na lista. Considere o nome do arquivo/pasta para deduzir seu conteúdo.
    2. Crie nomes de categoria lógicos e concisos (ex: "Projetos Python", "Documentos Fiscais", "Fotos de Viagem").
    3. Se um item não tiver uma categoria clara ou parecer lixo, atribua a categoria "_a_revisar".
    4. Sua resposta deve ser **APENAS** um único objeto JSON onde a chave é o caminho completo do item e o valor é a string da categoria de destino.

    **Exemplo de Saída JSON:**
    ```json
    {{
      "/path/to/downloads/my-node-project": "Projetos Web",
      "/path/to/downloads/relatorio.pdf": "Documentos",
      "/path/to/downloads/foto-viagem.jpg": "Fotos",
      "/path/to/downloads/arquivo_bizarro.dat": "_a_revisar"
    }}
    ```
    """
    
    try:
        # Use o gemini-1.5-flash que é mais rápido e mais barato para esta tarefa
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await model.generate_content_async(prompt)
        
        # Limpeza robusta da resposta para garantir que seja um JSON válido
        json_str = response.text.strip()
        if json_str.startswith('```json'):
            json_str = json_str[7:-3].strip()
        
        categorization_map = json.loads(json_str)
        await ctx.log(f"Categorização com IA concluída com sucesso. {len(categorization_map)} itens categorizados.", level="info")
        return categorization_map
    except (json.JSONDecodeError, IndexError, Exception) as e:
        response_text = "N/A"
        if 'response' in locals() and hasattr(response, 'text'):
            response_text = response.text
        await ctx.log(f"Erro crítico ao categorizar com IA: {e}\nResposta recebida: {response_text}", level="error")
        # Retorna um mapa vazio em caso de erro para não quebrar o fluxo
        return {}

# --- MUDANÇA 4: Construtor de plano determinístico e robusto. ---
@mcp.tool
async def _build_plan(root_directory: str, categorization_map: Dict[str, str], ctx: Context) -> Dict:
    """Constrói um plano de ações (CREATE, MOVE) a partir de um mapa de categorização, diferenciando arquivos de pastas."""
    await ctx.log("Construindo plano de execução a partir das categorias...", level="info")
    steps = []
    root_dir = Path(root_directory)
    
    # Ignora a categoria especial na criação de pastas
    destination_categories = set(cat for cat in categorization_map.values() if cat != "_a_revisar")

    # 1. Criar as pastas de destino
    for category in sorted(list(destination_categories)):
        # Garante que o nome da categoria seja seguro para um nome de pasta
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
        
        if original_path.is_dir():
            # O destino de uma pasta é a pasta da categoria, o shutil.move fará a movimentação para DENTRO dela.
            to_path = str(dest_folder)
            steps.append({"action": "MOVE_FOLDER", "from": str(original_path), "to": to_path})
        elif original_path.is_file():
            to_path = str(dest_folder / original_path.name)
            steps.append({"action": "MOVE_FILE", "from": str(original_path), "to": to_path})

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
    
    # 1. SCAN SUPERFICIAL E RÁPIDO
    items_to_process = await _scan_root_level.fn(directory_path=directory_path, ctx=ctx)
    if not items_to_process:
        return {"status": "completed", "message": "Nenhum arquivo ou pasta encontrado na raiz do diretório.", "plan": None}
    
    # 2. REGRAS RÁPIDAS
    rule_map, items_for_llm = _apply_rules(items_to_process)
    await ctx.log(f"{len(rule_map)} arquivos categorizados por regras.", level="info")

    # 3. LLM (CHAMADA ÚNICA)
    llm_map = {}
    if items_for_llm:
        llm_map = await _categorize_with_llm.fn(user_goal=user_goal, items_to_categorize=items_for_llm, ctx=ctx)
    
    # 4. COMBINAR E CONSTRUIR PLANO
    full_categorization_map = {**rule_map, **llm_map}
    if not full_categorization_map:
        return {"status": "error", "message": "Não foi possível categorizar nenhum item.", "plan": None}

    plan = await _build_plan.fn(root_directory=directory_path, categorization_map=full_categorization_map, ctx=ctx)
    
    # 5. POSTAR NO HIVE MIND (opcional mas bom para a arquitetura)
    try:
        await ctx.hub.call_tool("post_entry", entry={
            "entry_id": str(uuid.uuid4()), "agent_name": mcp.name,
            "entry_type": "ORGANIZATION_PLAN", "timestamp": datetime.utcnow().isoformat(),
            "content": f"Plano de organização gerado para '{Path(directory_path).name}' com o objetivo '{user_goal}'. O plano contém {len(plan.get('steps', []))} passos.",
            "context": {"directory": directory_path, "goal": user_goal, "plan": plan},
            "tags": ["organization", "planning", "suggestion"], "utility_score": 0.0, "references_entry_id": None
        })
        await ctx.log("Plano gerado e registrado com sucesso no Hive Mind.", level="info")
    except Exception as e:
         await ctx.log(f"Aviso: Falha ao registrar plano no Hive Mind: {e}", level="warning")

    return {"status": "plan_generated", "plan": plan}

def get_agent_mcp():
    return mcp