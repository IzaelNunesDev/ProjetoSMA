# watcher.py
import asyncio
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Callable, Awaitable
from hub import hub_mcp
from fastmcp import Client

class AsyncWatcherEventHandler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop, callback: Callable[[str], Awaitable[None]]):
        self.loop = loop
        self.callback = callback

    def _schedule_hub_task(self, tool_name: str, path: str):
        async def task():
            async with Client(hub_mcp) as client:
                await client.call_tool(tool_name, path=path)
        asyncio.run_coroutine_threadsafe(task(), self.loop)

    def on_created(self, event):
        if not event.is_directory:
            asyncio.run_coroutine_threadsafe(self.callback(event.src_path), self.loop)

    def on_deleted(self, event):
        if not event.is_directory:
            self._schedule_hub_task('handle_file_deleted', event.src_path)
    
    def on_modified(self, event):
        if not event.is_directory:
            self._schedule_hub_task('handle_file_modified', event.src_path)

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
