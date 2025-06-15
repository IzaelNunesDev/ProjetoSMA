# web_ui.py (VERSÃO FINAL)
import json
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from hub import hub_mcp
from fastmcp import Client
try:
    from fastmcp.messages_generated import LogMessage
except ImportError:
    from fastmcp.client.logging import LogMessage

# Configuração do FastAPI e dos templates
app = FastAPI()

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    return templates.TemplateResponse(request, "index.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    log_handler = WebSocketLogHandler(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            action = payload.get("action")
            current_tool_name_to_call = None
            current_tool_params_to_call = {}

            async with Client(hub_mcp, log_handler=log_handler.handle_log) as client:
                if action == "organize":
                    current_tool_name_to_call = "organize_directory"
                    current_tool_params_to_call = {
                        "directory_path": payload.get("directory"),
                        "user_goal": payload.get("goal"),
                        "auto_approve": True
                    }
                elif action == "index":
                    current_tool_name_to_call = "index_directory_for_memory"
                    current_tool_params_to_call = {"directory_path": payload.get("directory")}
                elif action == "query":
                    user_query_text = payload.get("query")
                    if not user_query_text:
                        await websocket.send_json({"type": "error", "message": "A consulta não pode estar vazia."})
                        continue

                    try:
                        count_query_tool_output_parts = await client.call_tool(
                            "query_indexed_files_count", # Tool on ExecutorAgent
                            {"query_text": user_query_text}
                        )

                        raw_count_query_output_text = None
                        if count_query_tool_output_parts and count_query_tool_output_parts[0] and count_query_tool_output_parts[0].text:
                            raw_count_query_output_text = count_query_tool_output_parts[0].text
                        
                        if raw_count_query_output_text:
                            count_query_final_result_data = json.loads(raw_count_query_output_text)
                            if count_query_final_result_data.get("status") == "answered":
                                await websocket.send_json({"type": "query_result", "data": count_query_final_result_data})
                                await client.log(f"Query answered by query_indexed_files_count: {user_query_text}", level="info")
                                continue # Skip semantic search, process next websocket message
                            else:
                                await client.log(f"query_indexed_files_count returned status '{count_query_final_result_data.get("status")}'. Proceeding to semantic search.", level="debug")
                        else:
                            await client.log("query_indexed_files_count returned no text output. Proceeding to semantic search.", level="warning")

                    except json.JSONDecodeError as e_json_count_query:
                        await client.log(f"JSONDecodeError from query_indexed_files_count: {e_json_count_query}. Raw: {raw_count_query_output_text if 'raw_count_query_output_text' in locals() else 'N/A'}. Proceeding to semantic search.", level="error")
                    except Exception as e_qc:
                        await client.log(f"Error calling query_indexed_files_count: {e_qc}. Proceeding to semantic search.", level="error")
                    
                    current_tool_name_to_call = "query_files_in_memory" # Semantic search tool
                    current_tool_params_to_call = {"query": user_query_text}
                else:
                    await websocket.send_json({"type": "error", "message": "Ação desconhecida."})
                    continue
                
                if not current_tool_name_to_call:
                    await client.log("Internal error: Tool name not set before call attempt.", level="error")
                    await websocket.send_json({"type": "error", "message": "Erro interno: nome da ferramenta não definido."})
                    continue

                if not all(current_tool_params_to_call.values()): # Check params for the specific tool
                    await websocket.send_json({"type": "error", "message": f"Todos os campos para a ação '{action}' são obrigatórios."})
                    continue
            
                try:
                    tool_output_parts = await client.call_tool(current_tool_name_to_call, current_tool_params_to_call)

                    raw_tool_output_text = None
                    if tool_output_parts and tool_output_parts[0] and tool_output_parts[0].text:
                        raw_tool_output_text = tool_output_parts[0].text
                    
                    final_result_data = {}
                    if raw_tool_output_text:
                        try:
                            final_result_data = json.loads(raw_tool_output_text)
                        except json.JSONDecodeError:
                            final_result_data = {
                                "status": "error", 
                                "details": "A resposta da ferramenta não é um JSON válido.",
                                "raw_output": raw_tool_output_text
                            }
                    else:
                        final_result_data = {
                            "status": "error", 
                            "details": "A ferramenta não retornou resultado ou o resultado está vazio."
                        }
                    
                    if action == "index" and final_result_data.get("status") == "success":
                        indexed_count = final_result_data.get("indexed_files") # Assuming this key exists in the response
                        if isinstance(indexed_count, int):
                            try:
                                await client.call_tool(
                                    "update_indexed_files_count", # Tool on ExecutorAgent
                                    {"count": indexed_count}
                                )
                                await client.log(f"Successfully called update_indexed_files_count with {indexed_count} files.", level="info")
                            except Exception as e_update_count:
                                await client.log(f"Error calling update_indexed_files_count: {e_update_count}", level="error")
                        elif indexed_count is not None:
                            await client.log(f"'indexed_files' value '{indexed_count}' from '{current_tool_name_to_call}' is not an integer. Cannot update count.", level="warning")
                        else:
                            await client.log(f"'indexed_files' key not found or null in response from '{current_tool_name_to_call}'. Cannot update count.", level="warning")

                    result_type = "query_result" if action == "query" and current_tool_name_to_call == "query_files_in_memory" else "result"
                    if action == "query" and current_tool_name_to_call == "query_files_in_memory":
                         result_type = "query_result"
                    elif action == "query": # Query was answered by count tool, already sent and continued.
                        pass # Should not reach here due to 'continue' above
                    else:
                        result_type = "result"

                    await websocket.send_json({"type": result_type, "data": final_result_data})

                except Exception as e_tool_call:
                    await client.log(f"Error calling tool {current_tool_name_to_call}: {str(e_tool_call)}", level="error")
                    await websocket.send_json({"type": "error", "message": f"Ocorreu um erro ao executar a ação: {str(e_tool_call)}"})

    except WebSocketDisconnect:
        print("Cliente desconectado.")
    except Exception as e:
        error_msg = f"Erro inesperado na conexão WebSocket: {e}"
        print(error_msg)
        try:
            await websocket.send_json({"type": "error", "message": error_msg})
        except Exception:
            pass # Ignora erros se o websocket já estiver fechado
