import json
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastmcp import FastMCP, Client

# Importa o loader de agentes
from hivemind_core.agent_loader import load_agents_from_directory

# --- Lógica de Inicialização (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código que roda ANTES do servidor iniciar
    print("🤖 Carregando todos os agentes do Hive Mind...")
    await load_agents_from_directory('agents', hub_mcp)
    tools = await hub_mcp.get_tools()
    print(f"✅ Agentes carregados. Total de ferramentas no hub: {len(tools)}")
    yield
    # Código que roda DEPOIS do servidor parar (se necessário)
    print(" gracefully shutting down.")

# Define o hub principal e a app aqui. Serão importados pelo main_hub.py
hub_mcp = FastMCP(name="HiveMindHub")
app = FastAPI(lifespan=lifespan) # Associa a função lifespan à app

# Configuração de arquivos estáticos e templates
app.mount("/static", StaticFiles(directory="web_ui/static"), name="static")
templates = Jinja2Templates(directory="web_ui/templates")

class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Erro ao transmitir para o websocket: {e}")

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    return templates.TemplateResponse(request, "index.html", {"request": request})

@app.get("/feed", response_class=HTMLResponse)
async def get_feed_page(request: Request):
    feed_items = []
    try:
        # Chama a ferramenta 'get_feed' agora disponível no hub
        async with Client(hub_mcp) as client:
            result_object = await client.call_tool("get_feed", {"top_k": 50})
            if result_object and result_object.data:
                feed_items = result_object.data
    except Exception as e:
        print(f"Erro ao buscar feed: {e}")
    
    # O template já está pronto para receber os itens
    return templates.TemplateResponse(request, "feed.html", {"feed_items": feed_items, "request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            action = payload.get("action")

            if action == "analyze_structure":
                directory = payload.get("directory")
                if not directory or not Path(directory).is_dir():
                    await websocket.send_json({"type": "error", "message": "Caminho inválido ou não é um diretório."})
                    continue
                
                async with Client(hub_mcp) as client:
                    try:
                        # O contexto é injetado automaticamente pelo FastMCP
                        result_object = await client.call_tool(
                            "analyze_directory_structure",
                            {"directory_path": directory}
                        )
                        await websocket.send_json({
                            "type": "analysis_result",
                            "data": result_object.data
                        })
                    except Exception as e:
                        import traceback
                        print(traceback.format_exc())
                        await websocket.send_json({"type": "error", "message": f"Erro ao executar análise: {e}"})
            else:
                await websocket.send_json({"type": "error", "message": f"Ação desconhecida: {action}"})
    except WebSocketDisconnect:
        print("Cliente desconectado.")
    finally:
        manager.disconnect(websocket) 