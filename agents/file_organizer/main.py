# agents/file_organizer/main.py (VERSÃO FINAL PARA VISUALIZAÇÃO)

import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import google.generativeai as genai
from fastmcp import FastMCP, Context

# Importando os utilitários de scanner diretamente para este módulo
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from magika import Magika

# --- Início dos Utilitários de Scanner (Lógica do antigo scanner_agent) ---
magika_instance = Magika()
CONTENT_LIMIT = 250
SUPPORTED_CONTENT_EXTS = {".txt", ".pdf", ".md", ".py", ".js", ".json", ".html", ".css", ".jpg", ".jpeg", ".png", ".tiff"}
EXCLUDED_DIRS = {"node_modules", "venv", ".venv", "__pycache__", ".git", ".vscode", "target", "build", "dist", "out"}

def _extract_content(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    content = ""
    try:
        if ext in ['.jpg', '.jpeg', '.png', '.tiff']:
            content = pytesseract.image_to_string(Image.open(file_path), lang='por+eng')
        elif ext == ".pdf":
            with fitz.open(file_path) as doc:
                content = "".join(page.get_text() for page in doc)
        elif ext in SUPPORTED_CONTENT_EXTS:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return "" # Retorna vazio se houver qualquer erro na extração
    return content[:CONTENT_LIMIT]
# --- Fim dos Utilitários de Scanner ---


# --- Início dos Utilitários de Regras (Lógica do antigo rules_agent) ---
RULES = {
    "Imagens": {"extensions": [".jpg", ".jpeg", ".png", ".gif", ".svg", ".bmp", ".tiff"]},
    "Documentos": {"extensions": [".pdf", ".docx", ".doc", ".txt", ".md", ".odt"]},
    "Instaladores": {"extensions": [".exe", ".msi", ".dmg"]},
    "Arquivos Compactados": {"extensions": [".zip", ".rar", ".7z", ".tar.gz"]}
}

def _apply_rules(items: List[Dict]) -> Tuple[Dict[str, str], List[Dict]]:
    categorized_by_rules = {}
    remaining_items = []
    for item in items:
        path = Path(item['path'])
        ext = ''.join(path.suffixes).lower() # Lida com ex: .tar.gz
        categorized = False
        for category, rule in RULES.items():
            if ext in rule.get("extensions", []):
                categorized_by_rules[item['path']] = category
                categorized = True
                break
        if not categorized:
            remaining_items.append(item)
    return categorized_by_rules, remaining_items
# --- Fim dos Utilitários de Regras ---

# --- Configuração do Agente ---
mcp = FastMCP(name="FileOrganizerAgent")

@mcp.tool
async def _scan_directory(directory_path: str, ctx: Context) -> list[dict]:
    """Escaneia um diretório, extraindo metadados e resumos de conteúdo."""
    await ctx.log(f"Iniciando escaneamento em: {directory_path}", level="info")
    root = Path(directory_path).expanduser().resolve()
    resultados = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        current_dir = Path(dirpath)
        
        for name in filenames:
            file_path = current_dir / name
            try:
                stat = file_path.stat()
                metadata = {
                    "path": str(file_path), "name": name,
                    "ext": ''.join(file_path.suffixes).lower(),
                    "content_summary": "", # Desabilitado para testes rápidos
                }
                resultados.append(metadata)
            except Exception as e:
                await ctx.log(f"Não foi possível ler o arquivo {file_path}: {e}", level="warning")
                continue
    return resultados

@mcp.tool
async def _categorize_with_llm(user_goal: str, items_to_categorize: list, ctx: Context) -> Dict[str, str]:
    """Usa um LLM para categorizar itens não cobertos por regras.""" 