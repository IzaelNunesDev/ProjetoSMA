# agents/memory_agent.py
import numpy as np
import google.generativeai as genai
from fastmcp import FastMCP, Context
from agents.scanner_agent import scan_directory
from prompt_manager import prompt_manager
import json

# Simples armazenamento de vetores em memória
VECTOR_STORE = {
    "embeddings": [],
    "metadata": []
}

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
    Escaneia um diretório, gera embeddings para o conteúdo dos arquivos e os armazena.
    """
    global VECTOR_STORE
    await ctx.log(f"Iniciando indexação do diretório: {directory_path}", level="info")

    # Limpa o armazenamento vetorial antes de uma nova indexação
    VECTOR_STORE = {"embeddings": [], "metadata": []}

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

        VECTOR_STORE["embeddings"] = embeddings
        VECTOR_STORE["metadata"] = [
            {
                "path": file["path"],
                "name": file["name"],
                "text_chunk": content
            }
            for file, content in zip(files_with_content, contents_to_embed)
        ]

        msg = f"Indexação concluída. {len(VECTOR_STORE['embeddings'])} documentos foram vetorizados e armazenados na memória."
        await ctx.log(msg, level="info")
        return {"status": "success", "indexed_files": len(VECTOR_STORE['embeddings'])}

    except Exception as e:
        await ctx.log(f"Falha ao indexar diretório: {e}", level="error")
        raise

@mcp.tool
async def query_memory(query: str, ctx: Context) -> dict:
    """
    Responde a uma pergunta com base no conteúdo dos arquivos indexados.
    """
    await ctx.log(f"Recebida a consulta: '{query}'", level="info")

    if not VECTOR_STORE["embeddings"]:
        return {"answer": "A memória está vazia. Por favor, indexe um diretório primeiro.", "source_files": []}

    await ctx.log("Gerando embedding para a consulta...", level="info")
    query_embedding_result = await genai.embed_content_async(
        model="models/text-embedding-004",
        content=query,
        task_type="RETRIEVAL_QUERY"
    )
    query_embedding = query_embedding_result['embedding']

    similarities = [
        _calculate_cosine_similarity(query_embedding, doc_embedding)
        for doc_embedding in VECTOR_STORE["embeddings"]
    ]
    
    top_k = 3
    top_indices = np.argsort(similarities)[-top_k:][::-1]

    context_chunks = []
    source_files = set()
    for i in top_indices:
        if similarities[i] > 0.5: 
            metadata = VECTOR_STORE["metadata"][i]
            context_chunks.append(metadata["text_chunk"])
            source_files.add(metadata["name"])

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
