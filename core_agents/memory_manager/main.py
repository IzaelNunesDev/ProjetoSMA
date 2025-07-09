# hivemind_core/memory_manager.py (MIGRADO DE agents/memory_agent.py)
import os
import uuid
import json
from datetime import datetime
from typing import List, Dict, TypedDict, Optional
import google.generativeai as genai
from fastmcp import FastMCP, Context
import chromadb
from chromadb.config import Settings

from dotenv import load_dotenv
load_dotenv()
if os.getenv("GEMINI_API_KEY"):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

client = chromadb.PersistentClient(
    path="chroma_db",
    settings=Settings(anonymized_telemetry=False)
)
hive_mind_collection = client.get_or_create_collection(
    name="hive_mind_simulation", # Nome mais genérico
    metadata={"hnsw:space": "cosine"}
)
mcp = FastMCP(name="MemoryManager")

class MemoryEntry(TypedDict):
    entry_id: str
    agent_name: str
    entry_type: str
    timestamp: str
    content: str
    context: dict
    tags: List[str]
    utility_score: float
    references_entry_id: Optional[str]

@mcp.tool
async def post_entry(entry: MemoryEntry, ctx: Context) -> dict:
    """Armazena uma entrada completa do HiveMind (MemoryEntry) na memória compartilhada."""
    try:
        await ctx.log(f"HiveMind: Registrando entrada de '{entry['agent_name']}'", level="debug")
        result = await genai.embed_content_async(
            model="models/text-embedding-004",
            content=entry['content'],
            task_type="RETRIEVAL_DOCUMENT"
        )
        embedding = result['embedding']
        metadata = dict(entry) # Todos os campos vão para metadados
        
        # Garante que tags sejam strings JSON
        if 'tags' in metadata and isinstance(metadata['tags'], list):
            metadata['tags'] = json.dumps(metadata['tags'])

        hive_mind_collection.upsert(
            ids=[entry['entry_id']],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[entry['content']]
        )
        return {"status": "success", "entry_id": entry['entry_id']}
    except Exception as e:
        error_msg = f"Falha ao postar entrada no HiveMind: {e}"
        await ctx.log(error_msg, level="error")
        return {"status": "error", "message": error_msg}

@mcp.tool
async def query_memory(query: str, ctx: Context, top_k: int = 5) -> dict:
    """Consulta o HiveMind por similaridade semântica."""
    # ... (código da função query_memory pode permanecer, é genérico)
    return {"results": []} # Placeholder

# Adicione get_feed_for_agent e update_entry_score se quiser, eles são genéricos.
# REMOVEMOS: index_directory, remove_from_memory_index, update_memory_index

@mcp.tool
async def get_feed(ctx: Context, top_k: int = 50) -> List[dict]:
    """Retorna as N memórias mais recentes do Hive Mind."""
    if hive_mind_collection.count() == 0:
        return []

    # Recupera os N itens mais recentes. A ordenação por timestamp
    # é feita após a busca, pois o ChromaDB não ordena nativamente por metadados.
    results = hive_mind_collection.get(
        limit=top_k,
        include=["metadatas"]
    )
    
    all_metadatas = results['metadatas']
    
    # Deserializa as tags se necessário
    for meta in all_metadatas:
        if 'tags' in meta and isinstance(meta.get('tags'), str):
            try:
                meta['tags'] = json.loads(meta['tags'])
            except (json.JSONDecodeError, TypeError):
                meta['tags'] = []
    
    # Ordenar o feed pela data, do mais novo para o mais antigo
    sorted_feed = sorted(all_metadatas, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return sorted_feed

@mcp.tool
async def update_entry_score(entry_id: str, score_delta: float, ctx: Context) -> dict:
    """Atualiza o utility_score de uma entrada do HiveMind."""
    try:
        entry = hive_mind_collection.get(ids=[entry_id], include=["metadatas"])
        if not entry or not entry.get('metadatas'):
            return {"status": "error", "message": "Entrada não encontrada."}
        
        meta = entry['metadatas'][0]
        current_score = meta.get('utility_score', 0.0)
        # Garante que o score seja float
        if not isinstance(current_score, (int, float)):
            current_score = 0.0

        meta['utility_score'] = current_score + score_delta
        
        # Garante que tags sejam strings JSON para o ChromaDB
        if 'tags' in meta and isinstance(meta['tags'], list):
            meta['tags'] = json.dumps(meta['tags'])

        hive_mind_collection.update(ids=[entry_id], metadatas=[meta])
        return {"status": "success", "new_score": meta['utility_score']}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_agent_mcp():
    """Retorna a instância do FastMCP do agente para o loader."""
    return mcp 