# watcher.py
import asyncio
from pathlib import Path
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Callable, Awaitable
from hub import hub_mcp

class AsyncWatcherEventHandler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop, callback: Callable[[str], Awaitable[None]]):
        self.loop = loop
        self.callback = callback

    def on_created(self, event):
        if not event.is_directory:
            # Chama a função de callback assíncrona de forma segura a partir da thread
            asyncio.run_coroutine_threadsafe(self.callback(event.src_path), self.loop)

    def on_deleted(self, event):
        """Handle file deletion events"""
        path = event.src_path
        asyncio.create_task(
            hub_mcp.call_tool(
                'handle_file_deleted', 
                path=path
            )
        )
    
    def on_modified(self, event):
        """Handle file modification events"""
        path = event.src_path
        asyncio.create_task(
            hub_mcp.call_tool(
                'handle_file_modified', 
                path=path
            )
        )

def start_watcher_thread(directory_path: str, callback: Callable[[str], Awaitable[None]]) -> Observer:
    """Cria e inicia um observador em uma thread, usando um callback assíncrono."""
    path = Path(directory_path).expanduser().resolve()
    if not path.is_dir():
        raise ValueError(f"O caminho fornecido não é um diretório válido: {path}")

    loop = asyncio.get_running_loop()
    event_handler = AsyncWatcherEventHandler(loop, callback)
    observer = Observer()
    observer.schedule(event_handler, str(path), recursive=False)
    
    # O observer já roda em sua própria thread quando chamamos start()
    observer.start() 
    print(f"👁️ Observador da thread iniciado para o diretório '{path}'...")
    return observer
