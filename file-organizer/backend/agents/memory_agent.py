# agents/memory_agent.py (VERSÃO CORRIGIDA E LIMPA)
import os
import uuid
import json
import numpy as np
from datetime import datetime
from typing import List, Dict, TypedDict, Optional
import google.generativeai as genai
from fastmcp import FastMCP, Context
from agents.scanner_agent import scan_directory
from prompt_manager import prompt_manager
import chromadb

# --- Configuração do Gemini (deve ser feita uma vez) ---
from dotenv import load_dotenv
load_dotenv()
if os.getenv("GEMINI_API_KEY"):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# --------------------------------------------------------

# Initialize persistent ChromaDB client
client = chromadb.PersistentClient(path="chroma_db")

# Get or create the collection for our vector store
hive_mind_collection = client.get_or_create_collection(
    name="file_organizer_mind",
    metadata={"hnsw:space": "cosine"}
)

mcp = FastMCP(name="MemoryAgent")

class MemoryEntry(TypedDict):
    entry_id: str             # UUID único para cada postagem
    agent_name: str           # ex: "CategorizerAgent", "UserInteraction"
    entry_type: str           # "INSIGHT", "ALERT", "SUGGESTION", "ACTION_RESULT"
    timestamp: str            # ISO format
    content: str              # O texto da postagem: "Sugiro mover X para Y"
    context: dict             # { "directory": "/path/to/dir", "file_ext": ".pdf" }
    tags: List[str]
    utility_score: float      # Começa em 0, modificado por feedback
    references_entry_id: Optional[str] # Para "comentários" ou "respostas"

@mcp.tool
async def index_directory(directory_path: str, ctx: Context, force_rescan: bool = False) -> dict:
    """
    Escaneia um diretório, gera embeddings para arquivos novos/modificados e os armazena no ChromaDB.
    """
    await ctx.log(f"Iniciando indexação do diretório: {directory_path}", level="info")

    try:
        # Usa a função de scan incremental
        files_metadata = await scan_directory.fn(directory_path=directory_path, ctx=ctx, force_rescan=force_rescan)

        files_with_content = [f for f in files_metadata if f.get("content_summary")]
        if not files_with_content:
            msg = "Nenhum arquivo novo ou modificado com conteúdo extraível foi encontrado para indexação."
            await ctx.log(msg, level="warning")
            return {"status": "warning", "message": msg, "indexed_files": 0}

        await ctx.log(f"Gerando embeddings para {len(files_with_content)} arquivos...", level="info")

        contents_to_embed = [
            f"Arquivo: {file['name']}\nCaminho: {file['path']}\nResumo do Conteúdo:\n{file['content_summary']}"
            for file in files_with_content
        ]

        # Batch embedding generation
        result = await genai.embed_content_async(
            model="models/text-embedding-004",
            content=contents_to_embed,
            task_type="RETRIEVAL_DOCUMENT"
        )
        embeddings = result['embedding']

        # Use o hash do path como ID para consistência e evitar duplicatas
        ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, file["path"])) for file in files_with_content]
        
        metadatas = [
            {
                "path": file["path"],
                "name": file["name"],
                "source": "scanner_agent",
                "tags": json.dumps(["index", "scan", file["ext"].lstrip('.')]), # Armazenar como JSON string
                "timestamp": file["modified_at"]
            }
            for file in files_with_content
        ]

        hive_mind_collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=contents_to_embed
        )

        msg = f"Indexação concluída. {len(files_with_content)} documentos foram vetorizados e armazenados na memória persistente."
        await ctx.log(msg, level="info")
        return {"status": "success", "indexed_files": len(files_with_content)}

    except Exception as e:
        await ctx.log(f"Falha ao indexar diretório: {e}", level="error")
        raise

@mcp.tool
async def query_memory(query: str = "", ctx: Context = None, agent_name: str = None, entry_type: str = None, tags: List[str] = None, top_k: int = 5) -> dict:
    """
    Consulta o HiveMind por similaridade semântica e/ou filtros estruturados (agente, tipo, tags), ordenando por utility_score.
    """
    await ctx.log(f"Consulta HiveMind: '{query}' | agent_name={agent_name} | entry_type={entry_type} | tags={tags}", level="info")
    if hive_mind_collection.count() == 0:
        return {"results": []}

    # Busca semântica se query fornecida
    if query:
        query_embedding_result = await genai.embed_content_async(
            model="models/text-embedding-004",
            content=query,
            task_type="RETRIEVAL_QUERY"
        )
        query_embedding = query_embedding_result['embedding']
        results = hive_mind_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k*2  # buscar mais para filtrar depois
        )
        metadatas = results['metadatas'][0]
    else:
        # Busca todos para filtrar
        all_results = hive_mind_collection.get(include=["metadatas"])
        metadatas = all_results['metadatas']

    # Filtros estruturados
    filtered = []
    for meta in metadatas:
        if agent_name and meta.get('agent_name') != agent_name:
            continue
        if entry_type and meta.get('entry_type') != entry_type:
            continue
        if tags:
            meta_tags = meta.get('tags', [])
            if isinstance(meta_tags, str):
                try:
                    meta_tags = json.loads(meta_tags)
                except Exception:
                    meta_tags = [meta_tags]
            if not any(tag in meta_tags for tag in tags):
                continue
        filtered.append(meta)

    # Ranking por utility_score
    filtered.sort(key=lambda m: m.get('utility_score', 0), reverse=True)
    return {"results": filtered[:top_k]}

@mcp.tool
async def post_memory_experience(experience: str, tags: List[str], source_agent: str, ctx: Context, reward: float = 0.0) -> dict:
    """
    Armazena uma experiência textual como vetor na memória compartilhada (Hive Mind).
    """
    try:
        await ctx.log(f"HiveMind: Registrando experiência de '{source_agent}' com tags {tags}", level="debug")
        
        result = await genai.embed_content_async(
            model="models/text-embedding-004",
            content=experience,
            task_type="RETRIEVAL_DOCUMENT"
        )
        embedding = result['embedding']

        metadata = {
            "source": source_agent,
            "tags": json.dumps(tags), # Armazenar lista como JSON string
            "content": experience,
            "timestamp": datetime.now().isoformat(),
            "reward": reward
        }
        
        # Usar um ID único para cada experiência
        exp_id = str(uuid.uuid4())

        hive_mind_collection.add(
            ids=[exp_id],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[experience]
        )

        return {"status": "success", "message": "Experiência registrada no Hive Mind."}
    except Exception as e:
        error_msg = f"Falha ao postar experiência no Hive Mind: {e}"
        await ctx.log(error_msg, level="error")
        return {"status": "error", "message": error_msg}

@mcp.tool
async def get_feed_for_agent(tags_of_interest: List[str] = None, top_k: int = 50, ctx: Context = None) -> List[dict]:
    """
    Retorna as memórias mais recentes do Hive Mind, opcionalmente filtradas por tags.
    """
    if hive_mind_collection.count() == 0:
        return []

    # NOTA DE ESCALABILIDADE: O filtro 'where' do ChromaDB não suporta consultas complexas
    # como verificar se um item de uma lista está contido em uma string JSON.
    # A abordagem atual recupera todos os metadados e filtra na memória.
    # Isso é aceitável para dezenas de milhares de itens, mas pode se tornar um
    # gargalo de desempenho com um volume de memória muito maior.
    # Uma solução futura poderia envolver uma estrutura de metadados diferente ou
    # uma consulta mais granular se a API do ChromaDB evoluir.
    results = hive_mind_collection.get(include=["metadatas"])
    
    all_metadatas = results['metadatas']
    
    feed_items = []
    for meta in all_metadatas:
        # Pular itens que não são experiências (ex: apenas arquivos indexados sem 'content')
        if 'content' not in meta:
            continue
            
        # Deserializar as tags para poder filtrar
        try:
            meta_tags = json.loads(meta.get("tags", "[]"))
        except (json.JSONDecodeError, TypeError):
            meta_tags = []

        if tags_of_interest:
            if any(tag in meta_tags for tag in tags_of_interest):
                meta['tags'] = meta_tags # Substituir string JSON pela lista
                feed_items.append(meta)
        else:
            meta['tags'] = meta_tags # Substituir string JSON pela lista
            feed_items.append(meta)

    # Ordenar o feed pela data, do mais novo para o mais antigo
    sorted_feed = sorted(feed_items, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return sorted_feed[:top_k]

@mcp.tool
async def post_entry(entry: MemoryEntry, ctx: Context) -> dict:
    """
    Armazena uma entrada completa do HiveMind (MemoryEntry) como vetor na memória compartilhada (ChromaDB).
    """
    try:
        await ctx.log(f"HiveMind: Registrando entrada de '{entry['agent_name']}' tipo {entry['entry_type']} com tags {entry['tags']}", level="debug")
        result = await genai.embed_content_async(
            model="models/text-embedding-004",
            content=entry['content'],
            task_type="RETRIEVAL_DOCUMENT"
        )
        embedding = result['embedding']
        # Todos os campos do MemoryEntry vão para metadados
        metadata = dict(entry)
        hive_mind_collection.upsert(
            ids=[entry['entry_id']],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[entry['content']]
        )
        return {"status": "success", "message": "Entrada registrada no HiveMind.", "entry_id": entry['entry_id']}
    except Exception as e:
        error_msg = f"Falha ao postar entrada no HiveMind: {e}"
        await ctx.log(error_msg, level="error")
        return {"status": "error", "message": error_msg}

@mcp.tool
async def update_entry_score(entry_id: str, score_delta: float, ctx: Context = None) -> dict:
    """
    Atualiza o utility_score de uma entrada do HiveMind (MemoryEntry) pelo entry_id.
    """
    try:
        # Buscar metadados atuais
        result = hive_mind_collection.get(ids=[entry_id], include=["metadatas"])
        if not result['metadatas'] or not result['metadatas'][0]:
            return {"status": "error", "message": "Entrada não encontrada."}
        meta = result['metadatas'][0]
        current_score = meta.get('utility_score', 0)
        new_score = current_score + score_delta
        meta['utility_score'] = new_score
        # Atualizar metadados no ChromaDB
        hive_mind_collection.update(ids=[entry_id], metadatas=[meta])
        return {"status": "success", "entry_id": entry_id, "new_utility_score": new_score}
    except Exception as e:
        return {"status": "error", "message": str(e)}