# agents/summarizer/main.py (VERSÃO CORRIGIDA)

import json
import google.generativeai as genai
from fastmcp import FastMCP, Context
from datetime import datetime
import uuid

mcp = FastMCP(name="SummarizerAgent")

# ## MUDANÇA PRINCIPAL 1: Prompt mais relevante ##
SUMMARIZATION_PROMPT = """
Você é um gerente de projetos que analisa planos. Leia o seguinte post sobre um plano de organização de arquivos e resuma a intenção geral em uma única frase.
Post Original:
"{analysis_content}"

Seu resumo de uma frase (ex: "O plano visa agrupar documentos fiscais e projetos de clientes para o diretório 'Downloads'."):
"""

@mcp.tool
async def summarize_text(text_to_summarize: str, ctx: Context) -> str:
    prompt = SUMMARIZATION_PROMPT.format(analysis_content=text_to_summarize)
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = await model.generate_content_async(prompt)
    return response.text.strip()

@mcp.tool
async def process_latest_posts(ctx: Context):
    await ctx.log("SummarizerAgent: Verificando o feed por novos planos...", level="info")

    feed_result = await ctx.hub.call_tool("get_feed", {"top_k": 10})
    latest_posts = feed_result.data if feed_result and feed_result.data else []

    if not latest_posts:
        await ctx.log("SummarizerAgent: Feed está vazio.", level="info")
        return {"status": "noop", "details": "Feed vazio."}

    for post in latest_posts:
        # ## MUDANÇA PRINCIPAL 2: Procurar pelo entry_type correto ##
        if post.get("entry_type") == "ORGANIZATION_PLAN":
            original_entry_id = post["entry_id"]

            # Verifica se já existe um resumo para este post
            query_result = await ctx.hub.call_tool("query_memory", {"query": f"resumo para o plano {original_entry_id}"})
            
            found_summary = False
            if query_result.data and query_result.data.get("results"):
                 found_summary = any(
                    res.get("references_entry_id") == original_entry_id
                    for res in query_result.data["results"]
                )

            if not found_summary:
                await ctx.log(f"SummarizerAgent: Novo plano encontrado para resumir: {original_entry_id}", level="info")
                
                summary_result = await ctx.hub.call_tool("summarize_text", {"text_to_summarize": post["content"]})
                summary_content = summary_result.data
                
                await ctx.hub.call_tool("post_entry", {"entry": {
                    "entry_id": str(uuid.uuid4()), "agent_name": "SummarizerAgent",
                    "entry_type": "SUMMARY", "timestamp": datetime.utcnow().isoformat(),
                    "content": summary_content, "context": {"source_agent": post["agent_name"]},
                    "tags": ["summary", "collaboration"], "utility_score": 0.0,
                    "references_entry_id": original_entry_id
                }})
                
                await ctx.log(f"SummarizerAgent: Resumo postado com sucesso.", level="info")
                return {"status": "success", "summary": summary_content}

    await ctx.log("SummarizerAgent: Nenhum plano novo encontrado para resumir.", level="info")
    return {"status": "noop", "details": "Nenhum plano novo."}

def get_agent_mcp():
    return mcp
