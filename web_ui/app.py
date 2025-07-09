# web_ui/app.py (VERSÃO SIMPLIFICADA E FOCADA)

import json
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastmcp import FastMCP, Client, Context
from hivemind_core.agent_loader import load_agents_from_directory

# --- Lógica de Inicialização (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(" HIVE MIND STARTUP ".center(50, "="))
    print("Carregando todos os agentes...")
    await load_agents_from_directory(hub_mcp)
    tools = await hub_mcp.get_tools()
    print(f"Agentes carregados. {len(tools)} ferramentas disponíveis no hub.")
    print("=" * 50)
    yield
    print("HIVE MIND SHUTDOWN".center(50, "="))

hub_mcp = FastMCP(name="HiveMindHub")
app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="web_ui/static"), name="static")
templates = Jinja2Templates(directory="web_ui/templates")

@app.get("/", response_class=HTMLResponse)
async def get_index_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/feed", response_class=HTMLResponse)
async def get_feed_page(request: Request):
    feed_items = []
    try:
        async with Client(hub_mcp) as client:
            result_object = await client.call_tool("get_feed", {"top_k": 50})
            if result_object and result_object.data:
                feed_items = result_object.data
    except Exception as e:
        print(f"Erro ao buscar feed: {e}")
    return templates.TemplateResponse("feed.html", {"feed_items": feed_items, "request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Criar um contexto de log para este websocket específico
    async def log_handler(message: str, level: str):
        await websocket.send_json({"type": "log", "level": level, "message": message})
    # O Context não aceita mais o log_handler, ele deve ser passado para o Client.
    ctx = Context(hub_mcp)

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            action = payload.get("action")

            # CORREÇÃO 2: O contexto (ctx) é passado diretamente para o call_tool.
            async with Client(hub_mcp, log_handler=log_handler) as client:
                if action == "generate_plan":
                    directory = payload.get("directory")
                    goal = payload.get("goal")
                    if not (directory and Path(directory).is_dir()):
                        await websocket.send_json({"type": "error", "message": "Caminho do diretório é inválido."})
                        continue
                    
                    # Log para depuração
                    await log_handler(f"Chamando 'generate_organization_plan' com diretório: {directory}", "debug")
                    
                    # CORREÇÃO FINAL: Argumentos são desempacotados como keywords.
                    # CORREÇÃO FINAL: O 'ctx' é injetado automaticamente pelo framework.
                    # Apenas os argumentos da ferramenta são passados.
                    result_object = await client.call_tool(
                        "generate_organization_plan",
                        directory_path=directory,
                        user_goal=goal
                    )
                    await websocket.send_json({"type": "plan_result", "data": result_object.data})

                elif action == "process_feed":
                    await client.call_tool("process_latest_posts", ctx=ctx)
                    await websocket.send_json({"type": "log", "level": "info", "message": "SummarizerAgent processou o feed. Atualize a página do feed para ver os resultados."})
                else:
                    await websocket.send_json({"type": "error", "message": f"Ação desconhecida: {action}"})
    
    except WebSocketDisconnect:
        print("Cliente desconectado.")
    except Exception as e:
        print(f"Erro no websocket: {e}") 