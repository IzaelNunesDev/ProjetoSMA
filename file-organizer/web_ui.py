import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from main_orchestrator import hub_mcp  # Importamos nosso hub já configurado
from fastmcp import Client
from fastmcp.client.logging import LogMessage

# Configuração do FastAPI e dos templates
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Classe para lidar com os logs e enviá-los via WebSocket
class WebSocketLogHandler:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def handle(self, message: LogMessage):
        """Envia a mensagem de log formatada para o cliente via WebSocket."""
        await self.websocket.send_json({
            "type": "log",
            "level": message.level,
            "message": message.data
        })

# Endpoint para servir a página principal do chat
@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Endpoint do WebSocket para comunicação em tempo real
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            # 1. Espera a mensagem do usuário (com o diretório e o objetivo)
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            directory_path = payload.get("directory")
            user_goal = payload.get("goal")

            if not directory_path or not user_goal:
                await websocket.send_json({"type": "error", "message": "Diretório e objetivo são obrigatórios."})
                continue
            
            # 2. Cria o handler de log para esta conexão WebSocket específica
            log_handler = WebSocketLogHandler(websocket)
            
            # 3. Usa um cliente MCP em memória para chamar a ferramenta do nosso hub
            # Passamos o nosso handler de log para o cliente.
            # O Context dentro da ferramenta 'organize_directory' usará este handler.
            async with Client(hub_mcp, log_handler=log_handler.handle) as client:
                try:
                    # 4. Chama a ferramenta de orquestração
                    result = await client.call_tool(
                        "organize_directory",
                        {
                            "directory_path": directory_path,
                            "user_goal": user_goal,
                            "auto_approve": True # Para a UI, vamos aprovar automaticamente
                        }
                    )
                    
                    # 5. Envia o resultado final
                    final_result = json.loads(result[0].text) if result else {"status": "error", "details": "Nenhum resultado."}
                    await websocket.send_json({"type": "result", "data": final_result})

                except Exception as e:
                    await websocket.send_json({"type": "error", "message": f"Ocorreu um erro: {str(e)}"})

    except WebSocketDisconnect:
        print("Cliente desconectado.")
