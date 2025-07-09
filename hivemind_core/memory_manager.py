# hivemind_core/memory_manager.py (MIGRADO DE agents/memory_agent.py)
import os
import uuid
import json
import numpy as np
from datetime import datetime
from typing import List, Dict, TypedDict, Optional
import google.generativeai as genai
from fastmcp import FastMCP, Context
from agents.file_organizer.scanner import scan_directory, process_single_file
from hivemind_core.prompt_manager import prompt_manager
import chromadb
from chromadb.config import Settings

from dotenv import load_dotenv
load_dotenv()
if os.getenv("GEMINI_API_KEY"):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

client = chromadb.PersistentClient(
    path="chroma_db",
    settings=Settings(anonymized_telemetry=False)
)

hive_mind_collection = client.get_or_create_collection(
    name="file_organizer_mind",
    metadata={"hnsw:space": "cosine"}
)

mcp = FastMCP(name="MemoryAgent")

class MemoryEntry(TypedDict):
    entry_id: str
    agent_name: str
    entry_type: str
    timestamp: str
    content: str
    context: dict
    tags: List[str]
    utility_score: float
    references_entry_id: Optional[str]

# --- Funções MCP migradas ---
# (Copiar todas as funções decoradas com @mcp.tool do arquivo original) 