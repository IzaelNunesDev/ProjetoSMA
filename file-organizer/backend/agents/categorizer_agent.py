import os
import json
import google.generativeai as genai
from fastmcp import FastMCP, Context
from typing import Optional, List, Dict

from dotenv import load_dotenv
from agents.memory_agent import query_memory
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

mcp = FastMCP(name="CategorizerAgent")

# Vamos usar um prompt dedicado para esta tarefa
CATEGORIZATION_PROMPT_TEMPLATE = """
Você é um especialista em organização de arquivos. Sua tarefa é categorizar uma lista de pastas e arquivos soltos.
Com base no objetivo do usuário, nos nomes dos itens e nas regras fornecidas, atribua uma categoria de destino para cada um.

**Regras Gerais de Organização (do usuário):**
{user_rules_context}

**Exemplos de Conteúdo Fornecidos pelo Usuário:**
{example_file_contents}

**Objetivo do Usuário:** {user_goal}
**Diretório Raiz:** {root_directory}

**Itens a serem categorizados:**
```json
{items_to_categorize}
```

Instruções:
Analise cada item (pasta ou arquivo) na lista.
Crie nomes de categoria concisos e lógicos (ex: "Projetos Python", "Documentos Acadêmicos", "Instaladores", "Imagens", "Outros").
Retorne APENAS um objeto JSON onde a chave é o caminho completo do item e o valor é a string da categoria de destino.
Se um item for lixo ou não tiver uma categoria clara, atribua a categoria "_a_revisar".
Exemplo de Saída:
```json
{{
  "C:\\Users\\User\\Downloads\\meu-projeto-node": "Projetos Frontend",
  "C:\\Users\\User\\Downloads\\relatorio_final.pdf": "Documentos",
  "C:\\Users\\User\\Downloads\\foto.jpg": "Imagens",
  "C:\\Users\\User\\Downloads\\arquivo_estranho.dat": "_a_revisar"
}}
```

Agora, gere o JSON de categorização para os itens fornecidos.
"""

@mcp.tool
async def categorize_items(
    user_goal: str,
    root_directory: str,
    directory_summaries: List[Dict],
    loose_files_metadata: List[Dict],
    ctx: Context,
    user_rules_context: str = "",
    example_file_contents: str = ""
) -> Dict[str, str]:
    """Usa um LLM para categorizar uma lista de pastas e arquivos."""
    items_to_categorize = [item['path'] for item in directory_summaries] + [item['path'] for item in loose_files_metadata]
    if not items_to_categorize:
        return {}

    await ctx.log(f"🧠 Categorizando {len(items_to_categorize)} itens...", level="info")

    # --- NOVO: Consultar o HiveMind por insights relevantes ---
    insights_str = ""
    try:
        query_result = await query_memory.fn(
            query=f"estratégias de categorização para '{root_directory}' {user_goal}",
            ctx=ctx,
            entry_type="INSIGHT",
            top_k=3
        )
        insights = query_result.get("results", [])
        if insights:
            insights_str = "\n\n".join(f"[Insight de {i['agent_name']} - Score: {i.get('utility_score',0)}]\n{i['content']}" for i in insights)
    except Exception as e:
        await ctx.log(f"Falha ao consultar insights do HiveMind: {e}", level="warning")

    prompt = CATEGORIZATION_PROMPT_TEMPLATE.format(
        user_rules_context=user_rules_context or "(nenhuma)",
        example_file_contents=(insights_str + "\n\n" + (example_file_contents or "(nenhum)")).strip(),
        user_goal=user_goal,
        root_directory=root_directory,
        items_to_categorize=json.dumps(items_to_categorize, indent=2)
    )

    model = genai.GenerativeModel('gemini-1.5-flash')
    try:
        response = await model.generate_content_async(prompt)
        
        json_str = response.text.strip()
        if json_str.startswith('```json'):
            json_str = json_str[7:-3].strip()
        
        categorization_map = json.loads(json_str)
        await ctx.log(f"✅ Itens categorizados com sucesso em {len(set(categorization_map.values()))} categorias.", level="info")
        return categorization_map
    except Exception as e:
        error_msg = f"Falha ao categorizar itens: {e}\nResposta recebida:\n{response.text}"
        await ctx.log(error_msg, level="error")
        raise ValueError(error_msg) from e
