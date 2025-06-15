# watcher.py
import asyncio
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm

from agents.watcher_agent import start_watcher
from hub import hub_mcp
from fastmcp import FastMCP, Context

console = Console()

async def main_watcher_loop(watch_path: str, index_path: str):
    """
    Loop principal que observa um diretório, obtém sugestões para novos arquivos e as executa após a confirmação.
    """
    loop = asyncio.get_running_loop()
    queue = asyncio.Queue()
    watch_path_obj = Path(watch_path).expanduser().resolve()
    index_path_obj = Path(index_path).expanduser().resolve()

    console.print(f"[bold green]Iniciando o assistente de organização automática.[/]")
    console.print(f"[bold]Diretório a ser observado:[/] [cyan]{watch_path_obj}[/]")
    console.print(f"[bold]Usando o índice de:[/] [cyan]{index_path_obj}[/]")

    # 1. Indexar o diretório de referência primeiro
    console.print(f"\n[bold yellow]Atualizando o índice de memória com base em '{index_path_obj}'...[/]")
    # Criando um contexto dummy para o hub
    hub_mcp = FastMCP(name="WatcherHub")
    ctx = Context(mcp=hub_mcp, tool_name="main_watcher")

    index_result = await hub_mcp.tools['index_directory_for_memory'].fn(directory_path=str(index_path_obj), ctx=ctx)
    if index_result.get("status") == "error":
        console.print(f"[bold red]Erro ao indexar o diretório: {index_result.get('details')}[/]")
        return
    console.print("[bold green]Índice de memória atualizado com sucesso![/]")

    # 2. Iniciar o observador de arquivos
    observer = start_watcher(str(watch_path_obj), queue, loop)

    try:
        while True:
            # 3. Aguardar por um novo arquivo na fila
            file_path = await queue.get()
            console.print(f"\n[bold magenta]Novo arquivo detectado:[/] [default]{file_path}[/]")

            # 4. Obter sugestão do hub
            console.print("[yellow]Analisando o arquivo e buscando sugestões...[/]")
            suggestion_result = await hub_mcp.tools['suggest_organization_for_file'].fn(file_path=file_path, ctx=ctx)

            if suggestion_result.get("status") == "success":
                suggestion = suggestion_result.get("suggestion", {})
                from_path = suggestion.get("from")
                to_path = suggestion.get("to")
                reason = suggestion.get("reason")

                if not from_path or not to_path:
                    console.print("[yellow]Não foi possível gerar uma sugestão clara.[/]")
                    continue

                console.print(f"[bold green]Sugestão da IA:[/]")
                console.print(f"  [bold]Mover:[/] [cyan]{from_path}[/]")
                console.print(f"  [bold]Para:[/]  [cyan]{to_path}[/]")
                console.print(f"  [bold]Motivo:[/] [italic]{reason}[/]")

                # 5. Confirmar e executar
                if Confirm.ask("\n[bold yellow]Você aprova esta sugestão?[/]"):
                    console.print("[bold]Executando ação...[/]")
                    # A sugestão já contém a ação de mover o arquivo
                    action = {
                        "action": "MOVE_FILE",
                        "from": from_path,
                        "to": to_path
                    }
                    # A pasta de destino pode não existir
                    dest_folder = Path(to_path).parent
                    if not dest_folder.exists():
                         await hub_mcp.tools['execute_planned_action'].fn(action={'action': 'CREATE_FOLDER', 'path': str(dest_folder)}, root_directory=str(index_path_obj), ctx=ctx)

                    exec_result = await hub_mcp.tools['execute_planned_action'].fn(action=action, root_directory=str(watch_path_obj), ctx=ctx)
                    if exec_result.get("status") == "success":
                        console.print(f"[bold green]✅ Arquivo movido com sucesso para {to_path}[/]")
                    else:
                        console.print(f"[bold red]❌ Falha ao mover o arquivo: {exec_result.get('details')}[/]")
                else:
                    console.print("[yellow]Ação cancelada pelo usuário.[/]")

            elif suggestion_result.get("status") == "no_suggestion":
                 console.print("[yellow]Nenhuma sugestão encontrada, o arquivo pode ser único.[/]")
            else:
                error_details = suggestion_result.get("details", "Erro desconhecido.")
                console.print(f"[bold red]Erro ao obter sugestão: {error_details}[/]")

            queue.task_done()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Desligando o observador...[/]")
    finally:
        observer.stop()
        observer.join()
        console.print("[bold red]Assistente encerrado.[/]")
