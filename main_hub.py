import uvicorn
import sys
from pathlib import Path
import asyncio

# Adiciona a raiz do projeto ao sys.path para garantir que os imports funcionem
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from hivemind_core.agent_loader import load_agents_from_directory
from web_ui.app import app, hub_mcp # Importa app e hub da UI

async def startup():
    print("🤖 Carregando todos os agentes do Hive Mind...")
    await load_agents_from_directory('agents', hub_mcp)
    tools = hub_mcp.tools
    print(f"✅ Agentes carregados. Total de ferramentas no hub: {len(tools)}")

if __name__ == "__main__":
    asyncio.run(startup())
    print(f"🚀 Iniciando interface web do Hive Mind em http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000) 