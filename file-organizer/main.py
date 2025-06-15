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

@cli.command()
def watch(
    watch_dir: str = typer.Argument(..., help="O diretório para monitorar por novos arquivos (ex: '~/Downloads')."),
    index_dir: str = typer.Argument(..., help="O diretório de referência para construir a memória de organização (ex: '~/Documents')."),
):
    """
    Inicia o modo de assistente, que monitora uma pasta e sugere organização para novos arquivos.
    """
    try:
        asyncio.run(main_watcher_loop(watch_dir, index_dir))
    except KeyboardInterrupt:
        print("\n👋 Assistente encerrado pelo usuário.")
    except Exception as e:
        print(f"\n🚨 Um erro inesperado ocorreu: {e}")

if __name__ == "__main__":
    cli()
