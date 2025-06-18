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
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# É crucial criar uma instância do MCP para este agente
mcp = FastMCP(name="PlanBuilderAgent")

@mcp.tool
async def create_organization_plan(
    user_goal: str,
    root_directory: str,
    ctx: Context,
    directory_summaries: Optional[list[dict]] = None,
    loose_files_metadata: Optional[list[dict]] = None
) -> dict:
    """
    Cria um plano de organização abrangente, considerando tanto subpastas quanto arquivos soltos.
    """
    if not directory_summaries and not loose_files_metadata:
        await ctx.log("Nenhum item (pasta ou arquivo) encontrado para organizar.", level="warning")
        return {"objective": "Nenhum item para organizar", "steps": []}

    await ctx.log(
        f"📝 Gerando plano de organização para {len(directory_summaries or [])} pastas "
        f"e {len(loose_files_metadata or [])} arquivos soltos",
        level="info"
    )
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    template_base = prompt_manager.get_prompt_template("file-organization")
    if not template_base:
        error_msg = "Template 'file-organization' não encontrado"
        await ctx.log(error_msg, level="error")
        raise ValueError(error_msg)

    # Prepara os blocos de dados
    summaries_json = json.dumps(directory_summaries, indent=2, ensure_ascii=False) if directory_summaries else "[]"
    loose_files_json = json.dumps(loose_files_metadata, indent=2, ensure_ascii=False) if loose_files_metadata else "[]"

    # --- CORREÇÃO DEFINITIVA: USAR str.replace() ---
    # Isso evita qualquer ambiguidade com o método .format()
    prompt = template_base \
        .replace("{user_goal}", user_goal) \
        .replace("{root_directory}", root_directory) \
        .replace("{directory_summaries_json}", summaries_json) \
        .replace("{loose_files_json}", loose_files_json)
    # --- FIM DA CORREÇÃO ---

    try:
        response = await model.generate_content_async(prompt)
        
        if not response.text:
            error_msg = "Resposta vazia do modelo generativo"
            await ctx.log(error_msg, level="error")
            raise ValueError(error_msg)
        
        await ctx.log(f"📝 Resposta bruta do modelo:\n{response.text}", level="debug")
        
        json_str = response.text.strip()
        if json_str.startswith('```json') and json_str.endswith('```'):
            json_str = json_str[7:-3].strip()
        elif json_str.startswith('```') and json_str.endswith('```'):
            json_str = json_str[3:-3].strip()
        
        if not (json_str.startswith('{') and json_str.endswith('}')):
            error_msg = f"Resposta do modelo não contém JSON válido:\n{json_str}"
            await ctx.log(error_msg, level="error")
            raise ValueError(error_msg)
            
        plan_object = json.loads(json_str)
        
        if not isinstance(plan_object, dict) or "steps" not in plan_object:
            error_msg = f"Plano mal formatado - faltando campo 'steps':\n{json_str}"
            await ctx.log(error_msg, level="error")
            raise ValueError(error_msg)
            
        await ctx.log(f"✅ Plano gerado com {len(plan_object.get('steps', []))} ações", level="info")
        return plan_object
        
    except json.JSONDecodeError as e:
        error_msg = f"Erro ao decodificar JSON do plano: {str(e)}\nTexto recebido:\n{json_str}"
        await ctx.log(error_msg, level="error")
        raise ValueError(error_msg) from e
    except Exception as e:
        # Não inclua o prompt inteiro no erro para não poluir o log com dados gigantes
        error_msg = f"Erro ao gerar plano: {str(e)}"
        await ctx.log(error_msg, level="error")
        raise Exception(error_msg) from e

@mcp.tool
async def build_plan_from_categorization(
    root_directory: str,
    categorization_map: Dict[str, str],
    ctx: Context
) -> Dict:
    """
    Constrói um plano de ações executável (CREATE, MOVE) a partir de um mapa de categorização.
    Esta função NÃO usa um LLM.
    """
    await ctx.log("🛠️ Construindo plano de execução a partir das categorias...", level="info")
    steps = []
    root_dir = Path(root_directory)

    # 1. Identificar todas as pastas de destino necessárias
    destination_categories = set(categorization_map.values())
    
    # 2. Criar as pastas de destino (CREATE_FOLDER)
    for category in sorted(list(destination_categories)):
        if category == "_a_revisar":
             # Nome especial para revisão
            dest_path = root_dir / "_A_REVISAR"
        else:
            dest_path = root_dir / category
        
        steps.append({"action": "CREATE_FOLDER", "path": str(dest_path)})

    # 3. Criar as ações de movimento (MOVE_FOLDER e MOVE_FILE)
    for original_path_str, category in categorization_map.items():
        original_path = Path(original_path_str)
        
        if category == "_a_revisar":
            dest_folder = root_dir / "_A_REVISAR"
        else:
            dest_folder = root_dir / category

        if original_path.is_dir():
            steps.append({
                "action": "MOVE_FOLDER",
                "from": str(original_path),
                "to": str(dest_folder)
            })
        elif original_path.is_file():
            steps.append({
                "action": "MOVE_FILE",
                "from": str(original_path),
                "to": str(dest_folder / original_path.name)
            })

    plan_object = {
        "objective": f"Organizar {len(categorization_map)} itens em {len(destination_categories)} categorias.",
        "steps": steps,
        "root_directory": root_directory # Adiciona o diretório raiz para o executor
    }
    
    await ctx.log(f"✅ Plano de execução construído com {len(steps)} ações.", level="info")
    return plan_object