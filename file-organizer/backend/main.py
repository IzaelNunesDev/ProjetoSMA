import uvicorn

# Este script agora inicia o servidor web diretamente, contornando o problema com o Typer.

if __name__ == "__main__":
    # Importamos o app aqui para garantir que o módulo seja carregado apenas na execução.
    from web_ui import app
    
    host = "127.0.0.1"
    port = 8000
    
    print(f"🚀 Iniciando interface web em http://{host}:{port}")
    # Para executar, use: python main.py
    uvicorn.run(app, host=host, port=port)
