import typer
import uvicorn
import asyncio
from web_ui import app # Importamos o app FastAPI
from watcher import main_watcher_loop

cli = typer.Typer(help="Um assistente de IA para organizar seus arquivos.")

@cli.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="O endereço de host para expor a interface."),
    port: int = typer.Option(8000, help="A porta para expor a interface."),
):
    """
    Inicia a interface web do Agente Organizador de Arquivos.
    """
    print(f"🚀 Iniciando interface web em http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)



if __name__ == "__main__":
    cli()
