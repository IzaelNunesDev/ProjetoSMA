# web_ui.py (VERSÃO FINAL)
import json
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from hub import hub_mcp
from fastmcp import Client
try:
    from fastmcp.messages_generated import LogMessage
except ImportError:
    from fastmcp.client.logging import LogMessage

# Configuração do FastAPI e dos templates
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Classe para lidar com os logs e enviá-los via WebSocket
class WebSocketLogHandler:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def handle_log(self, message: LogMessage):
        """Envia a mensagem de log formatada para o cliente via WebSocket."""
        try:
            await self.websocket.send_json({
                "type": "log",
                "level": message.level,
                "message": message.data
            })
        except WebSocketDisconnect:
            print("Tentativa de log em WebSocket desconectado.")
        except Exception as e:
            print(f"Erro ao enviar log via WebSocket: {e}")

@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    log_handler = WebSocketLogHandler(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            action = payload.get("action")
            tool_name = ""
            tool_params = {}

            if action == "organize":
                tool_name = "organize_directory"
                tool_params = {
                    "directory_path": payload.get("directory"),
                    "user_goal": payload.get("goal"),
                    "auto_approve": True
                }
            elif action == "index":
                tool_name = "index_directory_for_memory"
                tool_params = {"directory_path": payload.get("directory")}
            elif action == "query":
                tool_name = "query_files_in_memory"
                tool_params = {"query": payload.get("query")}
            else:
                await websocket.send_json({"type": "error", "message": "Ação desconhecida."})
                continue
            
            # Validação simples de input
            if not all(tool_params.values()):
                 await websocket.send_json({"type": "error", "message": "Todos os campos para a ação selecionada são obrigatórios."})
                 continue
            
            async with Client(hub_mcp, log_handler=log_handler.handle_log) as client:
                try:
                    result = await client.call_tool(tool_name, tool_params)

                    if result and result[0]:
                        final_result_text = result[0].text
                    else:
                        final_result_text = '{"status": "error", "details": "A ferramenta não retornou resultado."}'
                    
                    final_result_text = result[0].text if result and not result[0].isError else '{"status": "error", "details": "Nenhum resultado retornado."}'
                    final_result = json.loads(final_result_text)
                    
                    result_type = "query_result" if action == "query" else "result"
                    await websocket.send_json({"type": result_type, "data": final_result})

                except Exception as e:
                    await websocket.send_json({"type": "error", "message": f"Ocorreu um erro: {str(e)}"})

    except WebSocketDisconnect:
        print("Cliente desconectado.")
    except Exception as e:
        error_msg = f"Erro inesperado na conexão WebSocket: {e}"
        print(error_msg)
        try:
            await websocket.send_json({"type": "error", "message": error_msg})
        except Exception:
            pass # Ignora erros se o websocket já estiver fechado
