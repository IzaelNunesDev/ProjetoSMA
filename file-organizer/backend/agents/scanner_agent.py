import os
import fitz
from pathlib import Path
from fastmcp import FastMCP, Context
from datetime import datetime
from collections import defaultdict

mcp = FastMCP(name="ScannerAgent")

CONTENT_LIMIT = 200
SUPPORTED_CONTENT_EXTS = {".txt", ".pdf"}
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
    ext = file.suffix.lower()
    if ext in [".exe", ".msi", ".dll", ".so", ".a", ".lib"]: 
        return "binario_ou_biblioteca"
    elif ext in [".zip", ".rar", ".7z", ".tar", ".gz"]:
        return "compactado"
    elif ext in [".pdf", ".docx", ".txt", ".md"]:
        return "documento"
    elif ext in [".mp4", ".mp3", ".mkv", ".avi", ".mov"]:
        return "mídia"
    elif ext in [".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico"]:
        return "imagem"
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
    if file_path.suffix.lower() in [".txt", ".md", ".py", ".js", ".html", ".css"]: 
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")[:CONTENT_LIMIT]
        except Exception:
            return ""
    elif file_path.suffix.lower() == ".pdf":
        return extrair_texto_pdf(file_path)
    return ""


@mcp.tool
async def scan_directory(directory_path: str, ctx: Context, max_depth: int = 5) -> list[dict]:
    await ctx.log(f"Iniciando escaneamento inteligente em: {directory_path}", level="info")

    root = Path(directory_path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Caminho fornecido não é um diretório válido.")

    resultados = []
    root_depth = len(root.parts)

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

    await ctx.log(f"✅ Escaneamento inteligente finalizado: {len(resultados)} arquivos relevantes analisados.", level="info")
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
