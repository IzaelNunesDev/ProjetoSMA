# backend/agents/scanner_agent.py (versão aprimorada com deduções)

import os
import fitz
from pathlib import Path
from fastmcp import FastMCP, Context
from datetime import datetime

mcp = FastMCP(name="ScannerAgent")

CONTENT_LIMIT = 200
MAX_PREVIEW_PAGES_PDF = 1
SUPPORTED_CONTENT_EXTS = {".txt", ".pdf"}


def deduzir_tipo_de_arquivo(file: Path) -> str:
    ext = file.suffix.lower()
    if ext in [".exe", ".msi", ".dll"]:
        return "instalador"
    elif ext in [".zip", ".rar", ".7z"]:
        return "compactado"
    elif ext in [".pdf", ".docx", ".txt"]:
        return "documento"
    elif ext in [".mp4", ".mp3", ".mkv"]:
        return "mídia"
    return "desconhecido"


def deduzir_estrutura_de_pasta(path: Path) -> str:
    try:
        nomes = {p.name.lower() for p in path.iterdir() if p.is_dir() or p.is_file()}
    except Exception:
        return "estrutura_desconhecida"

    if {"node_modules", "src", "package.json"} & nomes:
        return "projeto_node"
    if {"venv", "main.py", "requirements.txt"} & nomes:
        return "projeto_python"
    if {"pages", "hooks", "public"} & nomes:
        return "projeto_frontend"
    if any("tp" in nome or "relat" in nome for nome in nomes):
        return "trabalho_academico"
    return "estrutura_desconhecida"


def extrair_texto_pdf(file_path: Path) -> str:
    try:
        with fitz.open(file_path) as doc:
            return doc[0].get_text() if doc.page_count else ""
    except Exception:
        return ""


def extrair_conteudo_resumido(file_path: Path) -> str:
    if file_path.suffix.lower() == ".txt":
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")[:CONTENT_LIMIT]
        except Exception:
            return ""
    elif file_path.suffix.lower() == ".pdf":
        return extrair_texto_pdf(file_path)
    return ""


@mcp.tool
async def scan_directory(directory_path: str, ctx: Context) -> list[dict]:
    await ctx.log(f"Iniciando escaneamento em: {directory_path}", level="info")

    root = Path(directory_path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Caminho fornecido não é um diretório válido.")

    resultados = []

    for dirpath, dirnames, filenames in os.walk(root):
        dir_atual = Path(dirpath)
        estrutura = deduzir_estrutura_de_pasta(dir_atual)
        await ctx.log(f"📁 Analisando: {dir_atual.name} → Estrutura deduzida: {estrutura}", level="debug")

        for nome_arquivo in filenames:
            arquivo = dir_atual / nome_arquivo
            ext = arquivo.suffix.lower()

            try:
                stat = arquivo.stat()
            except Exception:
                continue

            metadado = {
                "type": "file",
                "path": str(arquivo),
                "name": nome_arquivo,
                "ext": ext,
                "size_kb": round(stat.st_size / 1024, 2),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "content_summary": "",
                "estrutura_deduzida": estrutura,
                "tipo_deduzido": deduzir_tipo_de_arquivo(arquivo),
            }

            if ext in SUPPORTED_CONTENT_EXTS:
                conteudo = extrair_conteudo_resumido(arquivo)
                metadado["content_summary"] = conteudo[:CONTENT_LIMIT]

            resultados.append(metadado)

    await ctx.log(f"✅ Escaneamento finalizado: {len(resultados)} arquivos analisados.", level="info")
    return resultados
