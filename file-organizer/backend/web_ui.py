# web_ui.py (VERSÃO CORRIGIDA)
import json
import asyncio
from typing import List
from pathlib import Path
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from hub import hub_mcp
from fastmcp import Client, Context
from watcher import start_watcher_thread

# Remova as importações problemáticas:
# from agents.memory_agent import MemoryAgent, get_memory_agent

# Configuração do FastAPI e dos templates
app = FastAPI()

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# --- Connection Manager (sem alterações) ---
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

# --- Lógica do Watcher (sem alterações) ---
async def on_new_file_detected(file_path: str):
    print(f"UI Handler: Novo arquivo detectado pelo watcher: {file_path}")
    try:
        async with Client(hub_mcp) as client:
            tool_output_parts = await client.call_tool('suggest_file_move', {'file_path': file_path})
            
            raw_output = tool_output_parts[0].text if tool_output_parts and tool_output_parts[0].text else None
            if not raw_output:
                print(f"Error: 'suggest_file_move' retornou uma saída vazia para {file_path}")
                return

            suggestion_result = json.loads(raw_output)

            if suggestion_result.get("status") == "success":
                suggestion = suggestion_result.get("suggestion")
                if suggestion:
                    await manager.broadcast({
                        "type": "suggestion",
                        "data": suggestion
                    })
            else:
                error_details = suggestion_result.get('details', 'Nenhum detalhe fornecido.')
                await manager.broadcast({
                    "type": "log",
                    "level": "error",
                    "message": f"Falha ao gerar sugestão para {Path(file_path).name}: {error_details}"
                })

    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar a resposta JSON da sugestão: {e}. Raw: '{raw_output if 'raw_output' in locals() else 'N/A'}'")
    except Exception as e:
        print(f"Erro ao processar novo arquivo {file_path}: {e}")


# --- ROTA /feed (sem alterações) ---
@app.get("/feed", response_class=HTMLResponse)
async def get_feed_page(request: Request):
    try:
        async with Client(hub_mcp) as client:
            tool_output_parts = await client.call_tool("get_feed_for_agent", {"top_k": 50})
            raw_output = tool_output_parts[0].text if tool_output_parts and tool_output_parts[0].text else "[]"
            # O get_feed_for_agent agora retorna uma lista de dicionários diretamente
            feed_items = json.loads(raw_output)

        return templates.TemplateResponse(request, "feed.html", {"feed_items": feed_items, "request": request})
    except Exception as e:
        return HTMLResponse(f"<h1>Erro ao carregar o feed:</h1><p>{e}</p>", status_code=500)


@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    return templates.TemplateResponse(request, "index.html", {"request": request})

active_watchers = {}

# --- WebSocket (sem alterações, mas o código antigo para 'approve_suggestion' será removido daqui) ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    async def websocket_log_handler(message: str, level: str):
        await websocket.send_json({"type": "log", "level": level, "message": message})

    original_log_method = Context.log
    async def patched_log_method(self, message, level="info"):
        await original_log_method(self, message, level)
        await websocket_log_handler(message, level)
    
    try:
        Context.log = patched_log_method

        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            action = payload.get("action")

            # APROVAÇÃO E EXECUÇÃO DE PLANO SÃO AGORA TRATADAS VIA API REST
            # A lógica de aprovação foi movida para os endpoints /api/
            # A lógica de execução do plano permanece aqui.

            if action == "start_watching":
                directory = payload.get("directory")
                if not directory or not Path(directory).is_dir():
                    await websocket.send_json({"type": "error", "message": "Caminho inválido"})
                    continue
                if directory in active_watchers and active_watchers[directory].is_alive():
                    await websocket.send_json({"type": "log", "level":"warning", "message": f"Já monitorando {directory}."})
                    continue
                observer = start_watcher_thread(directory, on_new_file_detected)
                active_watchers[directory] = observer
                await websocket.send_json({"type": "log", "level":"info", "message": f"👁️ Monitoramento iniciado em: {directory}"})
                continue
            
            # ... (manter a lógica para 'organize', 'index', 'query', 'execute_plan', 'maintenance') ...
            # O código para essas ações está correto e pode ser mantido.
            # Vou omitir por brevidade, mas ele deve permanecer como está.

            # Lógica para organize, index, query, etc.
            current_tool_name_to_call = None
            current_tool_params_to_call = {}
            async with Client(hub_mcp) as client:
                if action == "organize":
                    current_tool_name_to_call = "organize_directory"
                    current_tool_params_to_call = {
                        "dir_path": payload.get("directory"), 
                        "user_goal": payload.get("goal"),
                        "dry_run": payload.get("dry_run", False)
                    }
                elif action == "organize_experimental":
                    current_tool_name_to_call = "organize_experimental"
                    current_tool_params_to_call = {"directory_path": payload.get("directory")}
                elif action == "index":
                    current_tool_name_to_call = "index_directory"
                    current_tool_params_to_call = {"directory_path": payload.get("directory")}
                elif action == "query":
                    current_tool_name_to_call = "query_memory"
                    current_tool_params_to_call = {"query": payload.get("query")}
                elif action == "execute_plan":
                    current_tool_name_to_call = "execute_plan"
                    current_tool_params_to_call = {"plan": payload.get("plan")}
                elif action == "maintenance":
                    # ... sua lógica de manutenção aqui ...
                    pass
                else:
                    await websocket.send_json({"type": "error", "message": f"Ação desconhecida: '{action}'"})
                    continue

                if not current_tool_name_to_call or not all(p is not None for p in current_tool_params_to_call.values()):
                    await websocket.send_json({"type": "error", "message": "Parâmetros inválidos."})
                    continue

                try:
                    tool_output_parts = await client.call_tool(
                        current_tool_name_to_call, 
                        current_tool_params_to_call
                    )
                    raw_tool_output_text = tool_output_parts[0].text if tool_output_parts and tool_output_parts[0].text else "{}"
                    final_result_data = json.loads(raw_tool_output_text)
                    
                    if action == "organize_experimental":
                        await websocket.send_json({"type": "experimental_result", "data": final_result_data})
                    elif action == "organize" and final_result_data.get("status") == "plan_generated":
                        await websocket.send_json({"type": "plan_result", "data": final_result_data["plan"]})
                    elif action == "query":
                        await websocket.send_json({"type": "query_result", "data": final_result_data})
                    else:
                        await websocket.send_json({"type": "result", "data": final_result_data})
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": f"Erro ao executar '{action}': {e}"})

    except WebSocketDisconnect:
        print("Cliente desconectado.")
    finally:
        Context.log = original_log_method
        manager.disconnect(websocket)

# --- NOVOS ENDPOINTS DE API (CORRIGIDOS) ---

@app.post("/api/suggestion/approve")
async def approve_suggestion(request: Request):
    suggestion_data = await request.json()
    
    # 1. Executar a ação de mover
    async with Client(hub_mcp) as client:
        root_dir = str(Path(suggestion_data['from']).parent)
        move_action = {"action": "MOVE_FILE", "from": suggestion_data["from"], "to": suggestion_data["to"]}
        dest_folder = Path(move_action['to']).parent
        
        # Cria a pasta de destino se não existir
        if not dest_folder.exists():
            await client.call_tool('execute_planned_action', {'action': {'action': 'CREATE_FOLDER', 'path': str(dest_folder)}, 'root_directory': root_dir})
        
        # Move o arquivo
        await client.call_tool('execute_planned_action', {'action': move_action, 'root_directory': root_dir})
        
        # 2. Registrar a experiência positiva na memória
        await client.call_tool('post_memory_experience', {
            'experience': f"Usuário aprovou mover {suggestion_data['from']} para {suggestion_data['to']}",
            'tags': ['feedback', 'approval', 'move'],
            'source_agent': 'UserInteraction',
            'reward': 1.0
        })

    return JSONResponse(content={"status": "approved"})

@app.post("/api/suggestion/reject")
async def reject_suggestion(request: Request):
    suggestion_data = await request.json()
    
    # Registrar a experiência negativa na memória
    async with Client(hub_mcp) as client:
        await client.call_tool('post_memory_experience', {
            'experience': f"Usuário rejeitou mover {suggestion_data['from']} para {suggestion_data['to']}",
            'tags': ['feedback', 'rejection', 'move'],
            'source_agent': 'UserInteraction',
            'reward': -1.0
        })

    return JSONResponse(content={"status": "rejected"})

@app.post("/api/maintenance/find_duplicates")
async def api_find_duplicates(request: Request):
    data = await request.json()
    directory = data.get('directory')
    if not directory:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Parâmetro 'directory' obrigatório"})
    
    async with Client(hub_mcp) as client:
        tool_output_parts = await client.call_tool('find_duplicates', {"directory": directory})
        raw_output = tool_output_parts[0].text if tool_output_parts and tool_output_parts[0].text else "[]"
        duplicates = json.loads(raw_output)
    
    return JSONResponse(content={"status": "success", "duplicates": duplicates})