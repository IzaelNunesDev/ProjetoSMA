# agents/scanner_agent.py (VERSÃO INTELIGENTE)

import os
from pathlib import Path
import fitz
from fastmcp import FastMCP, Context

mcp = FastMCP(name="ScannerAgent")

def _extract_text_from_pdf(file_path: Path) -> str:
    """Extrai texto de um arquivo PDF."""
    try:
        with fitz.open(file_path) as doc:
            text = "".join(page.get_text() for page in doc)
        return text
    except Exception as e:
        # Retorna uma string vazia se houver erro na leitura do PDF
        return f"Erro ao ler PDF: {e}"

@mcp.tool
async def scan_directory(directory_path: str, ctx: Context) -> list[dict]:
    """
    Escaneia um diretório de forma inteligente.
    - Se um subdiretório tiver muitos arquivos, ele o trata como um único item.
    - Extrai conteúdo apenas de arquivos .pdf e .txt.
    """
    await ctx.log(f"🔍 Análise inteligente iniciada em: {directory_path}", level="info")
    
    # --- NOVOS PARÂMETROS DE CONFIGURAÇÃO ---
    MAX_FILES_PER_DIR = 100  # Se um diretório tiver mais que isso, não lemos os arquivos dentro dele.
    SUPPORTED_CONTENT_EXTS = ['.pdf', '.txt']
    CONTENT_SUMMARY_LIMIT = 200
    # ----------------------------------------

    files_and_folders_metadata = []
    try:
        root_path = Path(directory_path).expanduser().resolve()
        if not root_path.is_dir():
            raise ValueError("O caminho especificado não é um diretório válido.")

        # Percorremos os diretórios de forma controlada
        for dirpath, dirnames, filenames in os.walk(root_path):
            current_dir_path = Path(dirpath)
            
            # --- LÓGICA DE DIRETÓRIO GRANDE ---
            if len(filenames) > MAX_FILES_PER_DIR:
                await ctx.log(f"Pasta '{current_dir_path.name}' é grande ({len(filenames)} arquivos). Tratando como um único item.", level="info")
                files_and_folders_metadata.append({
                    "type": "directory", # Novo campo para diferenciar
                    "path": str(current_dir_path),
                    "name": current_dir_path.name,
                    "file_count": len(filenames),
                })
                # Impede que os.walk entre nos subdiretórios desta pasta grande
                dirnames[:] = [] 
                continue # Pula para o próximo item no walk
            # -----------------------------------

            # Processa os arquivos no diretório atual (pois não é grande)
            for filename in filenames:
                file_path = current_dir_path / filename
                file_ext = file_path.suffix.lower()
                
                metadata = {
                    "type": "file", # Novo campo para diferenciar
                    "path": str(file_path),
                    "name": filename,
                    "size_kb": round(file_path.stat().st_size / 1024, 2),
                    "ext": file_ext,
                    "modified_at": file_path.stat().st_mtime,
                    "content_summary": ""
                }

                if file_ext in SUPPORTED_CONTENT_EXTS:
                    content = ""
                    if file_ext == '.pdf':
                        content = _extract_text_from_pdf(file_path)
                    elif file_ext == '.txt':
                        try:
                            content = file_path.read_text(encoding='utf-8', errors='ignore')
                        except Exception:
                            pass # Ignora erros de leitura de txt
                    
                    metadata["content_summary"] = content[:CONTENT_SUMMARY_LIMIT]

                files_and_folders_metadata.append(metadata)
        
        await ctx.log(f"Análise concluída. {len(files_and_folders_metadata)} itens (arquivos e pastas grandes) encontrados.", level="info")
        return files_and_folders_metadata
    except Exception as e:
        await ctx.log(f"Falha ao escanear o diretório: {e}", level="error")
        raise