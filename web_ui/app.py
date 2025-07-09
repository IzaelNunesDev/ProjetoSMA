# app.py (MIGRADO DE web_ui.py)
import json
import asyncio
import warnings
from typing import List
from pathlib import Path
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import re

# Suprimir warnings de deprecação
warnings.filterwarnings("ignore", category=DeprecationWarning)

from agents.file_organizer.executor import _is_path_safe
from fastmcp import Client
from file_organizer.backend.watcher import start_watcher_thread
from file_organizer.backend.checkpoint_manager import CheckpointManager
from main_hub import hub_mcp

# Configuração do FastAPI e dos templates
app = FastAPI()

# Mount static files directory
app.mount("/static", StaticFiles(directory="web_ui/static"), name="static")
templates = Jinja2Templates(directory="web_ui/templates")

# --- Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

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

# --- Lógica do Watcher (CORRIGIDO) ---
async def on_new_file_detected(file_path: str):
    asyncio.create_task(process_file_suggestion(file_path))

async def process_file_suggestion(file_path: str):
    print(f"UI Handler: Novo arquivo detectado pelo watcher: {file_path}")
    # Aqui, você deve importar ou receber o hub_mcp do main_hub.py
    # Exemplo: from main_hub import hub_mcp
    # Por enquanto, placeholder:
    from fastmcp import FastMCP
    hub_mcp = FastMCP(name="HiveMindHub")
    try:
        async with Client(hub_mcp) as client:
            result_object = await client.call_tool('suggest_file_move', {'file_path': file_path})
            suggestion_result = result_object.data
            if not suggestion_result:
                print(f"Error: 'suggest_file_move' retornou uma saída vazia para {file_path}")
                return
            if suggestion_result.get("status") == "success":
                suggestion = suggestion_result.get("suggestion")
                if suggestion:
                    try:
                        await manager.broadcast({"type": "suggestion", "data": suggestion})
                    except Exception as e:
                        print(f"Erro ao enviar sugestão via broadcast: {e}")
            else:
                error_details = suggestion_result.get('details', 'Nenhum detalhe fornecido.')
                try:
                    await manager.broadcast({"type": "log", "level": "error", "message": f"Falha ao gerar sugestão para {Path(file_path).name}: {error_details}"})
                except Exception as e:
                    print(f"Erro ao enviar log de erro via broadcast: {e}")
    except Exception as e:
        import traceback
        print(f"Erro inesperado ao processar novo arquivo {file_path}: {e}")
        traceback.print_exc()

# --- ROTAS HTML (CORRIGIDO) ---
@app.get("/feed", response_class=HTMLResponse)
async def get_feed_page(request: Request):
    from fastmcp import FastMCP
    hub_mcp = FastMCP(name="HiveMindHub")
    try:
        async with Client(hub_mcp) as client:
            result_object = await client.call_tool("get_feed_for_agent", {"top_k": 50})
            feed_items = result_object.data if result_object and result_object.data else []
        return templates.TemplateResponse(request, "feed.html", {"feed_items": feed_items, "request": request})
    except Exception as e:
        return HTMLResponse(f"<h1>Erro ao carregar o feed:</h1><p>{e}</p>", status_code=500)

@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    return templates.TemplateResponse(request, "index.html", {"request": request})

# (O restante do código segue igual, ajustando imports para a nova estrutura) 