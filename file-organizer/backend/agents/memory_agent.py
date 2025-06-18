# agents/memory_agent.py
import numpy as np
import google.generativeai as genai
from fastmcp import FastMCP, Context
from agents.scanner_agent import scan_directory
from prompt_manager import prompt_manager
import json
from typing import List, Dict
from datetime import datetime
import chromadb
import uuid

# Initialize persistent ChromaDB client
client = chromadb.PersistentClient(path="chroma_db")

# Get or create the collection for our vector store
hive_mind_collection = client.get_or_create_collection(
    name="file_organizer_mind",
    metadata={"hnsw:space": "cosine"}
)

mcp = FastMCP(name="MemoryAgent")

def _calculate_cosine_similarity(vec1, vec2):
    """Calcula a similaridade de cosseno entre dois vetores."""
    if not isinstance(vec1, np.ndarray):
        vec1 = np.array(vec1)
    if not isinstance(vec2, np.ndarray):
        vec2 = np.array(vec2)
    
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0
        
    return dot_product / (norm_vec1 * norm_vec2)

@mcp.tool
async def index_directory(directory_path: str, ctx: Context) -> dict:
    """
    Escaneia um diretório, gera embeddings e os armazena no ChromaDB.
    """
    await ctx.log(f"Iniciando indexação do diretório: {directory_path}", level="info")

    try:
        files_metadata = await scan_directory.fn(directory_path=directory_path, ctx=ctx)
        
        files_with_content = [f for f in files_metadata if f.get("content_summary")]
        if not files_with_content:
            msg = "Nenhum arquivo com conteúdo de texto extraível foi encontrado para indexação."
            await ctx.log(msg, level="warning")
            return {"status": "warning", "message": msg}

        await ctx.log(f"Gerando embeddings para {len(files_with_content)} arquivos...", level="info")
        
        contents_to_embed = [
            f"Arquivo: {file['name']}\nConteúdo:\n{file['content_summary']}" 
            for file in files_with_content
        ]

        result = await genai.embed_content_async(
            model="models/text-embedding-004",
            content=contents_to_embed,
            task_type="RETRIEVAL_DOCUMENT"
        )
        
        embeddings = result['embedding']

        # Generate unique IDs for each document
        ids_to_add = [str(uuid.uuid5(uuid.NAMESPACE_DNS, file["path"])) for file in files_with_content]
        
        # Prepare metadata for ChromaDB
        metadatas = [
            {
                "path": file["path"],
                "name": file["name"],
                "text_chunk": content,
                "content": content,
                "source": "scanner_agent",
                "tags": ["index", "scan", file["ext"].lstrip('.')],
                "timestamp": file["modified_at"]
            }
            for file, content in zip(files_with_content, contents_to_embed)
        ]

        # Upsert documents into ChromaDB
        hive_mind_collection.upsert(
            embeddings=embeddings,
            metadatas=metadatas,
            documents=contents_to_embed,
            ids=ids_to_add
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

    # --- LÓGICA DE CONTAGEM MELHORADA E CENTRALIZADA ---
    normalized_query = query.lower().strip()
    count_keywords = [
        "quantos arquivos", "numero de arquivos", "arquivos na memoria", 
        "arquivos indexados", "total de arquivos", "how many files"
    ]
    if any(keyword in normalized_query for keyword in count_keywords):
        count = hive_mind_collection.count()
        answer = f"Atualmente, há {count} arquivo(s) indexado(s) na memória persistente."
        await ctx.log(f"Respondendo à meta-consulta diretamente: {answer}", level="info")
        return {"answer": answer, "source_files": ["System Memory"]}
    # --- FIM DA LÓGICA DE CONTAGEM ---

    # Check if collection is empty
    if hive_mind_collection.count() == 0:
        return {"answer": "A memória está vazia. Por favor, indexe um diretório primeiro.", "source_files": []}

    await ctx.log("Gerando embedding para a consulta...", level="info")
    query_embedding_result = await genai.embed_content_async(
        model="models/text-embedding-004",
        content=query,
        task_type="RETRIEVAL_QUERY"
    )
    query_embedding = query_embedding_result['embedding']

    # Query ChromaDB
    results = hive_mind_collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )

    context_chunks = results['documents'][0]
    source_files = set(meta['name'] for meta in results['metadatas'][0])

    if not context_chunks:
        return {"answer": "Não consegui encontrar informações relevantes nos arquivos para responder à sua pergunta.", "source_files": []}

    context_str = "\n---\n".join(context_chunks)
    
    prompt = prompt_manager.format_prompt(
        task_name="query-memory",
        context_str=context_str,
        query=query
    )
    if not prompt:
        raise ValueError("Template de prompt 'query-memory' não encontrado ou malformado.")

    await ctx.log("Gerando resposta com base no contexto encontrado...", level="info")
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = await model.generate_content_async(prompt)
    
    return {"answer": response.text, "source_files": list(source_files)}

@mcp.tool
async def post_memory_experience(
    self, 
    experience: str, 
    tags: List[str] = None,
    source_agent: str = None,
    reward: float = 0.0
) -> bool:
    """Store an experience with metadata"""
    memory = {
        'timestamp': datetime.utcnow().isoformat(),
        'experience': experience,
        'tags': tags or [],
        'source_agent': source_agent,
        'reward': reward
    }
    return await self.memory_store.add_memory(memory)

@mcp.tool
async def get_feed_for_agent(self, tags: List[str] = None) -> List[Dict]:
    """Retrieve experiences filtered by tags"""
    query = {}
    if tags:
        query['tags'] = {'$in': tags}
    return await self.memory_store.query_memories(query)

@mcp.tool
async def get_feed_for_agent_original(tags_of_interest: List[str] = None, top_k: int = 20, ctx: Context = None) -> List[dict]:
    """
    Retorna as memórias mais recentes do Hive Mind, opcionalmente filtradas por tags.
    """
    # Get all items from ChromaDB
    items = hive_mind_collection.get()
    
    if tags_of_interest:
        # Filter by tags
        filtered = [
            {"metadata": meta, "document": doc}
            for meta, doc in zip(items['metadatas'], items['documents'])
            if any(tag in meta.get("tags", []) for tag in tags_of_interest)
        ]
    else:
        # Get all items
        filtered = [
            {"metadata": meta, "document": doc}
            for meta, doc in zip(items['metadatas'], items['documents'])
        ]

    # Sort by timestamp (newest first)
    filtered.sort(key=lambda x: x['metadata'].get("timestamp", ""), reverse=True)
    
    return [item['metadata'] for item in filtered[:top_k]]

class MemoryAgent:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="chroma_db")
        self.collection = self.client.get_or_create_collection(
            name="file_organizer_mind",
            metadata={"hnsw:space": "cosine"}
        )

    async def post_memory_experience(self, experience: str, tags: List[str] = None, 
                                   source_agent: str = None, reward: float = 0.0) -> bool:
        """Store an experience with metadata"""
        memory = {
            'timestamp': datetime.utcnow().isoformat(),
            'experience': experience,
            'tags': tags or [],
            'source_agent': source_agent,
            'reward': reward
        }
        
        # Generate embedding for the experience
        embedding_result = await genai.embed_content_async(
            model="models/text-embedding-004",
            content=experience,
            task_type="RETRIEVAL_DOCUMENT"
        )
        embedding = embedding_result['embedding']
        
        # Store in ChromaDB
        self.collection.upsert(
            embeddings=[embedding],
            metadatas=[memory],
            documents=[experience],
            ids=[str(uuid.uuid4())]
        )
        return True

    async def get_feed_for_agent(self, tags: List[str] = None, top_k: int = 20) -> List[Dict]:
        """Retrieve experiences filtered by tags"""
        if tags:
            # Filter by tags
            items = self.collection.get(where={"tags": {"$in": tags}})
        else:
            # Get all items
            items = self.collection.get()
        
        # Sort by timestamp (newest first)
        metadatas = items['metadatas']
        metadatas.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return metadatas[:top_k]


def get_memory_agent():
    """Dependency function for FastAPI to get MemoryAgent instance"""
    return MemoryAgent()
