# agents/suggestion_agent.py
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from fastmcp import FastMCP, Context
from agents.scanner_agent import scan_directory
from agents.memory_agent import query_memory, post_entry, MemoryEntry
from prompt_manager import prompt_manager
import uuid
from datetime import datetime

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configura a API do Google
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("A variável de ambiente GEMINI_API_KEY não foi definida.")
genai.configure(api_key=GEMINI_API_KEY)

mcp = FastMCP(name="SuggestionAgent")

@mcp.tool
async def suggest_file_move(file_path: str, ctx: Context) -> dict:
    """
    Analisa um único arquivo, consulta a memória por arquivos similares e sugere um local para movê-lo.
    """
    await ctx.log(f"🧠 Analisando novo arquivo para sugestão: {file_path}", level="info")
    try:
        # 1. Obter metadados do arquivo novo
        file_metadata_list = await scan_directory.fn(directory_path=str(Path(file_path).parent), ctx=ctx)
        target_file_metadata = next((f for f in file_metadata_list if f['path'] == file_path), None)

        if not target_file_metadata:
            return {"status": "error", "details": "Não foi possível obter metadados para o arquivo."}

        # 2. Consultar a memória por arquivos similares
        query_str = f"Arquivos relacionados a: {target_file_metadata['name']}"
        if target_file_metadata.get('content_summary'):
            query_str += f"\nConteúdo inicial: {target_file_metadata['content_summary']}"
        
        await ctx.log(f"🔎 Consultando memória com a query: '{query_str}'", level="info")
        memory_result = await query_memory.fn(query=query_str, ctx=ctx)
        
        similar_files_info = memory_result.get("results", [])

        if not similar_files_info:
            await ctx.log("Nenhum arquivo similar encontrado na memória. Não é possível sugerir.", level="info")
            return {"status": "no_suggestion", "details": "Nenhum arquivo similar encontrado."}

        # 3. Gerar a sugestão com o LLM
        await ctx.log("💡 Gerando sugestão de organização com a IA...", level="info")
        prompt = prompt_manager.format_prompt(
            task_name="generate-suggestion",
            target_file_metadata=json.dumps(target_file_metadata, indent=2),
            similar_files_info=json.dumps(similar_files_info, indent=2)
        )
        
        if not prompt:
            raise ValueError("Template de prompt 'generate-suggestion' não encontrado.")

        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await model.generate_content_async(prompt)
        
        suggestion_str = response.text.strip().replace("```json", "").replace("```", "")
        suggestion = json.loads(suggestion_str)

        await ctx.log(f"✨ Sugestão recebida: Mover para '{suggestion.get('to')}'", level="info")

        # --- NOVO: Postar sugestão no HiveMind ---
        entry_id = uuid.uuid4().hex
        entry: MemoryEntry = {
            "entry_id": entry_id,
            "agent_name": "SuggestionAgent",
            "entry_type": "SUGGESTION",
            "timestamp": datetime.utcnow().isoformat(),
            "content": f"Sugiro mover {file_path} para {suggestion.get('to')}",
            "context": {
                "directory": str(Path(file_path).parent),
                "file_name": Path(file_path).name,
                "file_ext": Path(file_path).suffix
            },
            "tags": ["suggestion", Path(file_path).suffix.lstrip('.')],
            "utility_score": 0.0,
            "references_entry_id": None
        }
        await post_entry.fn(entry=entry, ctx=ctx)
        # Retornar o entry_id junto com a sugestão
        suggestion["entry_id"] = entry_id
        return {"status": "success", "suggestion": suggestion}

    except Exception as e:
        error_msg = f"Erro ao gerar sugestão para '{file_path}': {e}"
        await ctx.log(error_msg, level="error")
        return {"status": "error", "details": error_msg}
