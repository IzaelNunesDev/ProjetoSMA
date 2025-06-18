from pathlib import Path
from typing import Tuple, Dict, List

RULES = {
    "Imagens": { "extensions": [".jpg", ".jpeg", ".png", ".gif", ".svg"] },
    "Documentos": { "extensions": [".pdf", ".docx", ".txt", ".md"] },
    "Instaladores": { "extensions": [".exe", ".msi", ".dmg"] },
    "Arquivos Compactados": { "extensions": [".zip", ".rar", ".7z"] }
}

async def apply_categorization_rules(items: List[Dict]) -> Tuple[Dict, List[Dict]]:
    categorized_by_rules = {}
    remaining_items = []
    
    for item in items:
        path = Path(item['path'])
        ext = path.suffix.lower()
        categorized = False
        for category, rule in RULES.items():
            if ext in rule.get("extensions", []):
                categorized_by_rules[item['path']] = category
                categorized = True
                break
        if not categorized:
            remaining_items.append(item)
            
    return categorized_by_rules, remaining_items
