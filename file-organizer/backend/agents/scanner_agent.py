import os
import fitz
from pathlib import Path
from fastmcp import FastMCP, Context
from datetime import datetime
from collections import defaultdict
import pytesseract
from PIL import Image
from magika import Magika

mcp = FastMCP(name="ScannerAgent")

# Initialize Magika instance
magika_instance = Magika()

CONTENT_LIMIT = 200
SUPPORTED_CONTENT_EXTS = {".txt", ".pdf", ".jpg", ".jpeg", ".png", ".tiff"}
EXCLUDED_DIRS = {
    "node_modules", "venv", ".venv", "__pycache__", ".git", ".vscode", 
    "target", "build", "dist", "out" 
}

PROJECT_STRUCTURE_TYPES = {
    "projeto_node",
    "projeto_python",
    "projeto_frontend"
}

def deduzir_tipo_de_arquivo(file: Path) -> str:
    """
    Usa Magika para detectar o tipo real do arquivo com base em seu conteúdo.
    """
    try:
        result = magika_instance.identify_path(file)
        return result.output.ct_label
    except Exception:
        return "desconhecido"

def deduzir_estrutura_de_pasta(path: Path) -> str:
    try:
        nomes = {p.name.lower() for p in path.iterdir() if p.is_dir() or p.is_file()}
    except (FileNotFoundError, PermissionError):
        return "inacessivel"

    if {"node_modules", "src", "package.json"}.issubset(nomes):
        return "projeto_node"
    if {"venv", "main.py", "requirements.txt"} & nomes or {".venv", "pyproject.toml"} & nomes:
        return "projeto_python"
    if {"pages", "hooks", "public", "next.config.js"} & nomes or {"src", "app", "routes"} & nomes:
        return "projeto_frontend"
    if {"vcpkg.json", "vcpkg-configuration.json", "ports", "vcpkg_installed"} & nomes:
        return "projeto_cpp_com_vcpkg"
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
    """
    Extrai conteúdo resumido de vários tipos de arquivo, incluindo OCR para imagens.
    """
    ext = file_path.suffix.lower()
    
    # Handle image files with OCR
    if ext in ['.jpg', '.jpeg', '.png', '.tiff']:
        try:
            return pytesseract.image_to_string(Image.open(file_path))[:CONTENT_LIMIT]
        except Exception:
            return ""
    
    # Handle text-based files
    if ext in [".txt", ".md", ".py", ".js", ".html", ".css"]: 
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")[:CONTENT_LIMIT]
        except Exception:
            return ""
    
    # Handle PDF files
    if ext == ".pdf":
        return extrair_texto_pdf(file_path)
        
    return ""


@mcp.tool
async def scan_directory(directory_path: str, ctx: Context, max_depth: int = 5, force_rescan: bool = False) -> list[dict]:
    """
    Escaneia um diretório incrementalmente, processando apenas arquivos novos ou modificados.
    """
    await ctx.log(f"Iniciando escaneamento incremental em: {directory_path}", level="info")

    root = Path(directory_path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Caminho fornecido não é um diretório válido.")

    root_depth = len(root.parts)

    # 1. Get current state from ChromaDB
    from agents.memory_agent import hive_mind_collection
    existing_files_data = hive_mind_collection.get(
        include=["metadatas"]
    )
    indexed_files = {meta['path']: meta for meta in existing_files_data['metadatas']}

    resultados = []

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        
        dir_atual = Path(dirpath)
        
        estrutura = deduzir_estrutura_de_pasta(dir_atual)
        
        if estrutura in PROJECT_STRUCTURE_TYPES or estrutura == "projeto_cpp_com_vcpkg":
            await ctx.log(f"🔎 Projeto '{estrutura}' detectado em '{dir_atual.relative_to(root)}'. Analisando apenas a raiz do projeto e ignorando subdiretórios.", level="info")
            dirnames.clear()
        
        current_depth = len(dir_atual.parts) - root_depth
        if current_depth >= max_depth:
            await ctx.log(f"Limite de profundidade ({max_depth}) atingido. Ignorando conteúdo de: {dir_atual.relative_to(root)}", level="debug")
            dirnames.clear()

        await ctx.log(f"📁 Analisando: {dir_atual.relative_to(root)} (Estrutura: {estrutura})", level="debug")
        
        for nome_arquivo in filenames:
            arquivo = dir_atual / nome_arquivo
            path_str = str(arquivo)
            ext = arquivo.suffix.lower()

            try:
                stat = arquivo.stat()
                current_mtime = stat.st_mtime
            except Exception:
                continue

            # Skip if file is already indexed and not modified
            if not force_rescan and path_str in indexed_files:
                last_mtime_iso = indexed_files[path_str].get("timestamp")
                if last_mtime_iso and datetime.fromisoformat(last_mtime_iso).timestamp() >= current_mtime:
                    continue  # File not modified, skip

            # Process new or modified file
            metadado = {
                "type": "file",
                "path": path_str,
                "name": nome_arquivo,
                "ext": ext,
                "size_kb": round(stat.st_size / 1024, 2),
                "modified_at": datetime.fromtimestamp(current_mtime).isoformat(),
                "content_summary": "",
                "estrutura_deduzida": estrutura,
                "tipo_deduzido": deduzir_tipo_de_arquivo(arquivo),
            }

            if ext in SUPPORTED_CONTENT_EXTS:
                conteudo = extrair_conteudo_resumido(arquivo)
                metadado["content_summary"] = conteudo[:CONTENT_LIMIT]

            resultados.append(metadado)

    await ctx.log(f"✅ Escaneamento incremental finalizado: {len(resultados)} arquivos novos/modificados encontrados.", level="info")
    return resultados


@mcp.tool
async def summarize_scan_results(scan_results: list[dict], ctx: Context) -> list[dict]:
    await ctx.log("📊 Resumindo resultados do escaneamento...", level="info")
    
    grouped_by_dir = defaultdict(list)
    for item in scan_results:
        if item.get("type") == "file":
            parent_dir = str(Path(item['path']).parent)
            grouped_by_dir[parent_dir].append(item)

    summary_list = []
    for dir_path, items in grouped_by_dir.items():
        file_count = len(items)
        
        extensions = sorted(list({item['ext'] for item in items if item.get('ext')}))
        structure = items[0]['estrutura_deduzida'] if items else 'desconhecida'
        
        types_str = ", ".join(extensions[:5])
        if len(extensions) > 5:
            types_str += ", ..."
        text_summary = f"Contém {file_count} arquivo(s). Tipos de arquivo incluem: {types_str}. "
        if structure != 'desconhecida' and structure != 'estrutura_desconhecida':
            text_summary += f"A estrutura da pasta foi deduzida como '{structure}'. "
        sample_files = [item['name'] for item in items[:3]]
        if sample_files:
            text_summary += f"Exemplos de arquivos: {', '.join(sample_files)}."

        summary_list.append({
            "path": dir_path,
            "file_count": file_count,
            "types": extensions,
            "estrutura_deduzida": structure,
            "summary": text_summary
        })

    await ctx.log(f"✅ Resumo concluído. {len(scan_results)} arquivos agrupados em {len(summary_list)} diretórios.", level="info")
    return summary_list

async def process_single_file(file_path: str, ctx: Context) -> dict | None:
    arquivo = Path(file_path)
    if not arquivo.is_file(): return None
    try:
        stat = arquivo.stat()
        current_mtime = stat.st_mtime
        metadado = {
            "type": "file",
            "path": str(arquivo),
            "name": arquivo.name,
            "ext": arquivo.suffix.lower(),
            "size_kb": round(stat.st_size / 1024, 2),
            "modified_at": datetime.fromtimestamp(current_mtime).isoformat(),
            "content_summary": "",
            "estrutura_deduzida": deduzir_estrutura_de_pasta(arquivo.parent),
            "tipo_deduzido": deduzir_tipo_de_arquivo(arquivo),
        }
        if arquivo.suffix.lower() in SUPPORTED_CONTENT_EXTS:
            conteudo = extrair_conteudo_resumido(arquivo)
            metadado["content_summary"] = conteudo[:CONTENT_LIMIT]
        return metadado
    except Exception as e:
        await ctx.log(f"Erro ao processar arquivo individual '{file_path}': {e}", level="error")
        return None
