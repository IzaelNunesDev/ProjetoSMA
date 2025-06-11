# web_ui.py
import json
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from hub import hub_mcp
from fastmcp import Client
from fastmcp.client.logging import LogMessage # <-- Importação corrigida

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

# Endpoint para servir a página principal
@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Endpoint do WebSocket para comunicação em tempo real
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    log_handler = WebSocketLogHandler(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            directory_path = payload.get("directory")
            user_goal = payload.get("goal")

            if not directory_path or not user_goal:
                await websocket.send_json({"type": "error", "message": "Diretório e objetivo são obrigatórios."})
                continue
            
            # Usando o cliente em memória para chamar a ferramenta do hub
            async with Client(hub_mcp, log_handler=log_handler.handle_log) as client:
                try:
                    result = await client.call_tool(
                        "organize_directory",
                        {
                            "directory_path": directory_path,
                            "user_goal": user_goal,
                            "auto_approve": True
                        }
                    )
                    
                    final_result = json.loads(result[0].text) if result else {"status": "error", "details": "Nenhum resultado retornado."}
                    await websocket.send_json({"type": "result", "data": final_result})

                except Exception as e:
                    await websocket.send_json({"type": "error", "message": f"Ocorreu um erro: {str(e)}"})

    except WebSocketDisconnect:
        print("Cliente desconectado.")
    except Exception as e:
        print(f"Erro inesperado na conexão WebSocket: {e}")
