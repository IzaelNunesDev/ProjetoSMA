import uvicorn
import sys
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path para garantir que os imports funcionem
# de forma consistente em qualquer ambiente.
sys.path.insert(0, str(Path(__file__).parent.absolute()))

if __name__ == "__main__":
    print(f"🚀 Iniciando interface web do Hive Mind em http://127.0.0.1:8000")
    # O Uvicorn irá carregar o objeto 'app' do módulo 'web_ui.app'.
    # A lógica de startup agora está dentro de 'web_ui.app' usando 'lifespan'.
    uvicorn.run("web_ui.app:app", host="127.0.0.1", port=8000, reload=True) 