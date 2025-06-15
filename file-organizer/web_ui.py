# web_ui.py
import json
import asyncio
from typing import List
from pathlib import Path
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from hub import hub_mcp
from fastmcp import Client
from watcher import start_watcher_thread

# Configuração do FastAPI e dos templates
app = FastAPI()

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# --- NOVO: Connection Manager ---
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

# --- NOVO: Lógica para rodar o watcher em segundo plano ---
async def on_new_file_detected(file_path: str):
    print(f"UI Handler: Novo arquivo detectado pelo watcher: {file_path}")
    try:
        async with Client(hub_mcp) as client:
            tool_output = await client.call_tool('suggest_file_move', {'file_path': file_path})
            
            raw_output = tool_output[0].text if tool_output and tool_output[0].text else None
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
                print(f"Falha ao obter sugestão: {error_details}")

    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar a resposta JSON da sugestão: {e}. Raw: '{raw_output if 'raw_output' in locals() else 'N/A'}'")
    except Exception as e:
        print(f"Erro ao processar novo arquivo {file_path}: {e}")

@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    return templates.TemplateResponse(request, "index.html")

# Dicionário para armazenar observers ativos por diretório
active_watchers = {}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            action = payload.get("action")

            if action == "approve_suggestion":
                suggestion_data = payload.get("suggestion")
                root_dir = str(Path(suggestion_data['from']).parent)
                
                async with Client(hub_mcp) as client:
                    move_action = {"action": "MOVE_FILE", "from": suggestion_data["from"], "to": suggestion_data["to"]}
                    dest_folder = Path(move_action['to']).parent
                    if not dest_folder.exists():
                        await client.call_tool('execute_planned_action', {'action': {'action': 'CREATE_FOLDER', 'path': str(dest_folder)}, 'root_directory': root_dir})

                    await client.call_tool('execute_planned_action', {'action': move_action, 'root_directory': root_dir})
                    await websocket.send_json({"type": "log", "level": "info", "message": f"Arquivo movido para {suggestion_data['to']}"})
                continue

            elif action == "start_watching":
                directory = payload.get("directory")
                if not directory or not Path(directory).is_dir():
                    await websocket.send_json({"type": "error", "message": f"Caminho inválido ou não é um diretório: {directory}"})
                    continue

                if directory in active_watchers and active_watchers[directory].is_alive():
                    await websocket.send_json({"type": "log", "level":"warning", "message": f"Já estou monitorando {directory}."})
                    continue

                try:
                    observer = start_watcher_thread(directory, on_new_file_detected)
                    active_watchers[directory] = observer
                    await websocket.send_json({"type": "log", "level":"info", "message": f"👁️ Monitoramento iniciado em: {directory}"})
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": f"Falha ao iniciar monitoramento: {e}"})
                continue

            elif action == "maintenance":
                sub_action = payload.get("sub_action")
                directory = payload.get("directory")

                if not directory or not Path(directory).is_dir():
                    await websocket.send_json({"type": "error", "message": f"Caminho inválido ou não é um diretório: {directory}"})
                    continue
                
                tool_to_call = ""
                if sub_action == "find_empty_folders":
                    tool_to_call = "find_empty_folders"
                
                if not tool_to_call:
                    await websocket.send_json({"type": "error", "message": f"Ação de manutenção desconhecida: '{sub_action}'"})
                    continue

                try:
                    async with Client(hub_mcp) as client:
                        tool_output_parts = await client.call_tool(tool_to_call, {"directory_path": directory})
                        raw_tool_output_text = tool_output_parts[0].text if tool_output_parts and tool_output_parts[0].text else "{}"
                        final_result_data = json.loads(raw_tool_output_text)
                        await websocket.send_json({"type": "result", "data": final_result_data})
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": f"Ocorreu um erro ao executar '{sub_action}': {e}"})
                continue

            # Lógica antiga para organize, index, query
            current_tool_name_to_call = None
            current_tool_params_to_call = {}
            async with Client(hub_mcp) as client:
                if action == "organize":
                    current_tool_name_to_call = "organize_directory"
                    current_tool_params_to_call = {"directory_path": payload.get("directory"), "user_goal": payload.get("goal"), "auto_approve": True}
                elif action == "index":
                    current_tool_name_to_call = "index_directory_for_memory"
                    current_tool_params_to_call = {"directory_path": payload.get("directory")}
                elif action == "query":
                    current_tool_name_to_call = "query_files_in_memory"
                    current_tool_params_to_call = {"query": payload.get("query")}
                else:
                    await websocket.send_json({"type": "error", "message": f"Ação desconhecida: '{action}'"})
                    continue

                if not all(p is not None for p in current_tool_params_to_call.values()):
                    await websocket.send_json({"type": "error", "message": f"Todos os campos para a ação '{action}' são obrigatórios."})
                    continue

                try:
                    tool_output_parts = await client.call_tool(current_tool_name_to_call, current_tool_params_to_call)
                    raw_tool_output_text = tool_output_parts[0].text if tool_output_parts and tool_output_parts[0].text else "{}"
                    final_result_data = json.loads(raw_tool_output_text)
                    
                    result_type = "query_result" if action == "query" else "result"
                    await websocket.send_json({"type": result_type, "data": final_result_data})

                except Exception as e:
                    await websocket.send_json({"type": "error", "message": f"Ocorreu um erro ao executar '{action}': {e}"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Cliente desconectado.")
    except Exception as e:
        error_msg = f"Erro inesperado na conexão WebSocket: {e}"
        print(error_msg)
        try:
            if websocket.client_state.name == 'CONNECTED':
                await websocket.send_json({"type": "error", "message": error_msg})
        except Exception:
            pass # Ignora erros se o websocket já estiver fechado
