import typer
import uvicorn
from web_ui import app # Importamos o app FastAPI

cli = typer.Typer()

@cli.command()
def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
):
    """
    Inicia a interface web do Agente Organizador de Arquivos.
    """
    print(f"🚀 Iniciando interface web em http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    cli()
