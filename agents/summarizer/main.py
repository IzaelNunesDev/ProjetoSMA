import json
import google.generativeai as genai
from fastmcp import FastMCP, Context
from datetime import datetime
import uuid

mcp = FastMCP(name="SummarizerAgent")

# O pre-prompt para o LLM, derivado do manifesto.
SUMMARIZATION_PROMPT = """
Você é um assistente conciso. Sua tarefa é ler a seguinte análise de estrutura de diretório e resumi-la em uma única frase impactante.

Análise Original:
"{analysis_content}"

Seu resumo de uma frase:
"""

@mcp.tool
async def summarize_text(text_to_summarize: str, ctx: Context) -> str:
    """Usa um LLM para resumir um texto fornecido."""
    prompt = SUMMARIZATION_PROMPT.format(analysis_content=text_to_summarize)
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = await model.generate_content_async(prompt)
    return response.text.strip()

@mcp.tool
async def process_latest_posts(ctx: Context):
    """
    Busca os posts mais recentes, encontra o primeiro 'STRUCTURE_ANALYSIS' que ainda não foi resumido
    e cria um resumo para ele.
    """
    await ctx.log("SummarizerAgent: Verificando o feed por novas análises...", level="info")

    # 1. PERCEBER: Ler o feed do Hive Mind
    latest_posts = await ctx.call_tool("get_feed", {"top_k": 10})
    if not latest_posts:
        await ctx.log("SummarizerAgent: Feed está vazio. Nada a fazer.", level="info")
        return {"status": "noop", "details": "Feed vazio."}

    # 2. PENSAR: Encontrar um post para agir
    for post in latest_posts:
        if post.get("entry_type") == "STRUCTURE_ANALYSIS":
            original_entry_id = post["entry_id"]

            # Verificar se já existe um resumo para este post
            query_result = await ctx.call_tool("query_memory", {
                "query": f"resumo para a análise {original_entry_id}"
            })
            
            found_summary = False
            if query_result and query_result.get("results"):
                 found_summary = any(
                    res.get("references_entry_id") == original_entry_id
                    for res in query_result["results"]
                )

            if not found_summary:
                await ctx.log(f"SummarizerAgent: Encontrei uma nova análise para resumir: {original_entry_id}", level="info")
                
                # 3. AGIR: Gerar o resumo e postar no Hive Mind
                summary_content = await ctx.call_tool("summarize_text", {"text_to_summarize": post["content"]})
                
                await ctx.call_tool("post_entry", {"entry": {
                    "entry_id": str(uuid.uuid4()),
                    "agent_name": "SummarizerAgent",
                    "entry_type": "SUMMARY",
                    "timestamp": datetime.utcnow().isoformat(),
                    "content": summary_content,
                    "context": {"source_agent": post["agent_name"]},
                    "tags": ["summary", "collaboration"],
                    "utility_score": 0.0,
                    "references_entry_id": original_entry_id # <-- A Conexão!
                }})
                
                await ctx.log(f"SummarizerAgent: Resumo postado com sucesso.", level="info")
                return {"status": "success", "summary": summary_content}

    await ctx.log("SummarizerAgent: Nenhuma nova análise encontrada para resumir.", level="info")
    return {"status": "noop", "details": "Nenhuma nova análise."}


def get_agent_mcp():
    """Retorna a instância do FastMCP do agente para o loader."""
    return mcp
