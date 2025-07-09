import uvicorn
from hivemind_core.agent_loader import load_agents_from_directory
from web_ui.app import app
from fastmcp import FastMCP

# MCP central do hub
hub_mcp = FastMCP(name="HiveMindHub")

def startup():
    print("🤖 Carregando todos os agentes do Hive Mind...")
    load_agents_from_directory('agents', hub_mcp)
    print(f"✅ Agentes carregados. Total de ferramentas no hub: {len(hub_mcp.get_tools())}")

if __name__ == "__main__":
    startup()
    print(f"🚀 Iniciando interface web do Hive Mind em http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000) 