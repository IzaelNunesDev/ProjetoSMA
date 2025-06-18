# agents/memory_agent.py (VERSÃO CORRIGIDA E LIMPA)
import os
import uuid
import json
import numpy as np
from datetime import datetime
from typing import List, Dict
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
async def query_memory(query: str, ctx: Context) -> dict:
    """
    Responde a uma pergunta consultando o ChromaDB.
    """
    await ctx.log(f"Recebida a consulta: '{query}'", level="info")

    normalized_query = query.lower().strip()
    count_keywords = ["quantos arquivos", "numero de arquivos", "total de arquivos"]
    if any(keyword in normalized_query for keyword in count_keywords):
        count = hive_mind_collection.count()
        answer = f"Atualmente, há {count} arquivo(s) indexado(s) na memória persistente."
        return {"answer": answer, "source_files": ["System Memory"]}

    if hive_mind_collection.count() == 0:
        return {"answer": "A memória está vazia. Por favor, indexe um diretório primeiro.", "source_files": []}

    query_embedding_result = await genai.embed_content_async(
        model="models/text-embedding-004",
        content=query,
        task_type="RETRIEVAL_QUERY"
    )
    query_embedding = query_embedding_result['embedding']

    results = hive_mind_collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    if not results['documents'] or not results['documents'][0]:
        return {"answer": "Não consegui encontrar informações relevantes para responder.", "source_files": []}

    context_chunks = results['documents'][0]
    source_files = set(meta['name'] for meta in results['metadatas'][0])
    context_str = "\n---\n".join(context_chunks)

    prompt = prompt_manager.format_prompt(
        task_name="query-memory",
        context_str=context_str,
        query=query
    )
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = await model.generate_content_async(prompt)
    
    return {"answer": response.text, "source_files": list(source_files)}

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

    # O filtro 'where' do ChromaDB é limitado e não suporta '$in' diretamente para strings JSON.
    # Portanto, recuperamos todos e filtramos na memória, o que é aceitável para um feed.
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