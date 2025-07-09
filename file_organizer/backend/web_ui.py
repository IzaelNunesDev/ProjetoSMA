# web_ui.py (VERSÃO CORRIGIDA)
from agents.executor_agent import _is_path_safe
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

from hub import hub_mcp
from fastmcp import Client
from watcher import start_watcher_thread
from checkpoint_manager import CheckpointManager

# Configuração do FastAPI e dos templates
app = FastAPI()

# Mount static files directory
app.mount("/static", StaticFiles(directory="file_organizer/backend/static"), name="static")
templates = Jinja2Templates(directory="templates")

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
    # Dispara o processamento em background para não travar o loop principal
    asyncio.create_task(process_file_suggestion(file_path))

async def process_file_suggestion(file_path: str):
    print(f"UI Handler: Novo arquivo detectado pelo watcher: {file_path}")
    try:
        async with Client(hub_mcp) as client:
            # CORRETO: O resultado é um objeto, não uma lista de partes.
            result_object = await client.call_tool('suggest_file_move', {'file_path': file_path})
            
            # CORRETO: O conteúdo estruturado já é um dicionário Python.
            suggestion_result = result_object.data
            
            if not suggestion_result:
                print(f"Error: 'suggest_file_move' retornou uma saída vazia para {file_path}")
                return

            if suggestion_result.get("status") == "success":
                suggestion = suggestion_result.get("suggestion")
                if suggestion:
                    try:
                        await manager.broadcast({
                            "type": "suggestion",
                            "data": suggestion
                        })
                    except Exception as e:
                        print(f"Erro ao enviar sugestão via broadcast: {e}")
            else:
                error_details = suggestion_result.get('details', 'Nenhum detalhe fornecido.')
                try:
                    await manager.broadcast({
                        "type": "log",
                        "level": "error",
                        "message": f"Falha ao gerar sugestão para {Path(file_path).name}: {error_details}"
                    })
                except Exception as e:
                    print(f"Erro ao enviar log de erro via broadcast: {e}")
    except Exception as e:
        import traceback
        print(f"Erro inesperado ao processar novo arquivo {file_path}: {e}")
        traceback.print_exc()

# --- ROTAS HTML (CORRIGIDO) ---
@app.get("/feed", response_class=HTMLResponse)
async def get_feed_page(request: Request):
    try:
        async with Client(hub_mcp) as client:
            # CORRETO: Tratar o resultado como um objeto.
            result_object = await client.call_tool("get_feed_for_agent", {"top_k": 50})
            # CORRETO: Acessar .data para obter o dicionário/lista Python.
            feed_items = result_object.data if result_object and result_object.data else []
        return templates.TemplateResponse(request, "feed.html", {"feed_items": feed_items, "request": request})
    except Exception as e:
        return HTMLResponse(f"<h1>Erro ao carregar o feed:</h1><p>{e}</p>", status_code=500)

@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    return templates.TemplateResponse(request, "index.html", {"request": request})

active_watchers = {}

# --- WebSocket (CORRIGIDO) ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    connection_observer = None
    try:
        while True:
            try:
                data = await websocket.receive_text()
                payload = json.loads(data)
                action = payload.get("action")

                if action == "start_watching":
                    directory = payload.get("directory")
                    if not directory or not Path(directory).is_dir():
                        await websocket.send_json({"type": "error", "message": "Caminho inválido"})
                        continue
                    
                    if directory in active_watchers and active_watchers[directory].is_alive():
                        await websocket.send_json({"type": "log", "level":"warning", "message": f"Já monitorando {directory}."})
                        continue
                        
                    if connection_observer and connection_observer.is_alive():
                        # Executar a parada e junção em uma thread separada para não bloquear
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, lambda: (connection_observer.stop(), connection_observer.join()))

                    observer = start_watcher_thread(directory, on_new_file_detected)
                    active_watchers[directory] = observer # Pode manter para evitar duplicatas globais
                    connection_observer = observer # Armazena na variável da conexão
                    await websocket.send_json({"type": "log", "level":"info", "message": f"️ Monitoramento iniciado em: {directory}"})
                    continue
                
                current_tool_name_to_call = None
                current_tool_params_to_call = {}

                async with Client(hub_mcp) as client:
                    if action == "organize":
                        current_tool_name_to_call = "organize_directory"
                        user_goal = payload.get("goal")
                        directory = payload.get("directory")
                        dry_run = payload.get("dry_run", False)
                        
                        # --- NOVO: detectar @caminho e ler conteúdo dos arquivos ---
                        example_file_contents = ""
                        if user_goal:
                            # Regex para encontrar padrões @caminho
                            matches = re.findall(r' @([\w\s\-/\.]+)', user_goal)
                            contents = []
                            for match in matches:
                                file_path = Path(match)
                                base_dir = Path(directory)
                                if not file_path.is_absolute():
                                    file_path = base_dir / file_path
                                
                                # Adicionar verificação de segurança
                                if _is_path_safe(file_path, base_dir) and file_path.exists() and file_path.is_file():
                                    try:
                                        # Limitar tamanho do conteúdo lido (ex: 10KB)
                                        content = file_path.read_text(encoding='utf-8', errors='ignore')[:10000]
                                        contents.append(f"--- CONTEÚDO DE {file_path} ---\n{content}\n-------------------------------------------")
                                    except Exception:
                                        pass
                                else:
                                    # Ignorar ou logar tentativa de acesso inválido
                                    await websocket.send_json({"type": "log", "level":"warning", "message": f"Acesso negado ou arquivo não encontrado: {match}"})
                            if contents:
                                example_file_contents = "\n".join(contents)
                                
                        current_tool_params_to_call = {
                            "dir_path": directory,
                            "user_goal": user_goal,
                            "dry_run": dry_run,
                            "example_file_contents": example_file_contents
                        }
                    elif action == "organize_experimental":
                        current_tool_name_to_call = "organize_experimental"
                        current_tool_params_to_call = {"directory_path": payload.get("directory")}
                    elif action == "index":
                        current_tool_name_to_call = "index_directory_for_memory"
                        current_tool_params_to_call = {"directory_path": payload.get("directory")}
                    elif action == "query":
                        current_tool_name_to_call = "query_files_in_memory"
                        current_tool_params_to_call = {"query": payload.get("query")}
                    elif action == "execute_plan":
                        current_tool_name_to_call = "execute_plan"
                        current_tool_params_to_call = {"plan": payload.get("plan")}
                    elif action == "maintenance":
                        sub_action = payload.get("sub_action")
                        directory = payload.get("directory")
                        if sub_action == "find_empty_folders":
                            current_tool_name_to_call = "find_empty_folders"
                            current_tool_params_to_call = {"directory_path": directory}
                        else:
                            await websocket.send_json({"type": "error", "message": f"Sub-ação de manutenção desconhecida: '{sub_action}'"})
                            continue
                    else:
                        await websocket.send_json({"type": "error", "message": f"Ação desconhecida: '{action}'"})
                        continue

                    if not current_tool_name_to_call or not all(p is not None for p in current_tool_params_to_call.values()):
                        await websocket.send_json({"type": "error", "message": "Parâmetros inválidos."})
                        continue

                    try:
                        # CORRETO: Não crie o contexto manualmente. O fastmcp injeta o contexto automaticamente no hub.
                        result_object = await client.call_tool(
                            current_tool_name_to_call,
                            current_tool_params_to_call
                        )
                        # CORRETO: O resultado está em .data
                        final_result_data = result_object.data
                        
                        if action == "organize_experimental":
                            await websocket.send_json({"type": "experimental_result", "data": final_result_data})
                        elif action == "organize" and final_result_data and final_result_data.get("status") == "plan_generated":
                            await websocket.send_json({"type": "plan_result", "data": final_result_data.get("plan")})
                        elif action == "query":
                            await websocket.send_json({"type": "query_result", "data": final_result_data})
                        else:
                            await websocket.send_json({"type": "result", "data": final_result_data})

                    except Exception as e:
                        await websocket.send_json({"type": "error", "message": f"Erro ao executar '{action}': {e}"})
            
            except WebSocketDisconnect:
                print("Cliente desconectado durante operação.")
                break
            except Exception as e:
                print(f"Erro no loop do WebSocket: {e}")
                try:
                    await websocket.send_json({"type": "error", "message": f"Erro interno: {e}"})
                except:
                    break
    
    except WebSocketDisconnect:
        print("Cliente desconectado.")
    except Exception as e:
        print(f"Erro no WebSocket endpoint: {e}")
    finally:
        if connection_observer and connection_observer.is_alive():
            print(f"Parando watcher para cliente desconectado.")
            connection_observer.stop()
            connection_observer.join()
        manager.disconnect(websocket)


# --- ENDPOINTS DE API (CORRIGIDO) ---
@app.post("/api/suggestion/approve")
async def approve_suggestion(request: Request):
    suggestion_data = await request.json()
    entry_id = suggestion_data.get('entry_id')
    async with Client(hub_mcp) as client:
        root_dir = str(Path(suggestion_data['from']).parent)
        
        # Ação para criar a pasta de destino
        dest_folder_action = {
            "action": "CREATE_FOLDER",
            "path": str(Path(suggestion_data["to"]).parent)
        }
        await client.call_tool('execute_planned_action', {'action': dest_folder_action, 'root_directory': root_dir})

        # Ação para mover o arquivo
        # CORRETO: Passando a referência da sugestão para o sistema de memória aprender
        move_action = {
            "action": "MOVE_FILE",
            "from": suggestion_data["from"],
            "to": suggestion_data["to"],
            "suggestion_entry_id": entry_id 
        }
        await client.call_tool('execute_planned_action', {'action': move_action, 'root_directory': root_dir})

        # A chamada para update_entry_score ainda é útil como um reforço explícito e imediato.
        if entry_id:
            await client.call_tool('update_entry_score', {'entry_id': entry_id, 'score_delta': 1.0})

        # Registrar a experiência positiva na memória (opcional, mas bom para análise)
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
    entry_id = suggestion_data.get('entry_id')
    async with Client(hub_mcp) as client:
        # Atualizar utility_score da sugestão rejeitada
        if entry_id:
            await client.call_tool('update_entry_score', {'entry_id': entry_id, 'score_delta': -1.0})
        
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
        # CORRETO: Tratar o resultado como um objeto.
        result_object = await client.call_tool('find_duplicates', {"directory": directory})
        duplicates = result_object.data if result_object and result_object.data else []
        return JSONResponse(content={"status": "success", "duplicates": duplicates})

@app.post("/api/maintenance/find_empty_folders")
async def api_find_empty_folders(request: Request):
    data = await request.json()
    directory = data.get('directory')
    if not directory:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Parâmetro 'directory' obrigatório"})
        
    async with Client(hub_mcp) as client:
        # CORRETO: Tratar o resultado como um objeto.
        result_object = await client.call_tool('find_empty_folders', {"directory_path": directory})
        result = result_object.data if result_object and result_object.data else {}
        return JSONResponse(content=result)

@app.post("/api/checkpoints/list")
async def api_list_checkpoints(request: Request):
    data = await request.json()
    directory = data.get('directory')
    print(f"API: Listando checkpoints para diretório: {directory}")
    if not directory:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Parâmetro 'directory' obrigatório"})
    try:
        checkpoints = CheckpointManager.list_checkpoints(directory)
        print(f"API: {len(checkpoints)} checkpoints encontrados")
        return JSONResponse(content={"status": "success", "checkpoints": checkpoints})
    except Exception as e:
        print(f"API: Erro ao listar checkpoints: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/api/checkpoints/restore/{commit_hash}")
async def api_restore_checkpoint(commit_hash: str, request: Request):
    data = await request.json()
    directory = data.get('directory')
    if not directory:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Parâmetro 'directory' obrigatório"})
    try:
        CheckpointManager.restore_checkpoint(directory, commit_hash)
        return JSONResponse(content={"status": "success"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
