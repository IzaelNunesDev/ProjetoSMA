# app.py (MIGRADO DE web_ui.py)
import json
import asyncio
from pathlib import Path
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastmcp import FastMCP, Client

# Define o hub principal e a app aqui. Serão importados pelo main_hub.py
hub_mcp = FastMCP(name="HiveMindHub")
app = FastAPI()

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
    return templates.TemplateResponse(request, "feed.html", {"feed_items": [], "request": request})

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
                    await websocket.send_json({"type": "error", "message": "Caminho inválido"})
                    continue
                async with Client(hub_mcp) as client:
                    try:
                        result_object = await client.call_tool(
                            "analyze_directory_structure",
                            {"directory_path": directory}
                        )
                        await websocket.send_json({
                            "type": "analysis_result",
                            "data": result_object.data
                        })
                    except Exception as e:
                        await websocket.send_json({"type": "error", "message": f"Erro ao executar análise: {e}"})
            else:
                await websocket.send_json({"type": "error", "message": f"Ação desconhecida: {action}"})
    except WebSocketDisconnect:
        print("Cliente desconectado.")
    finally:
        manager.disconnect(websocket) 