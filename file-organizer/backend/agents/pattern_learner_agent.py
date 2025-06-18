from typing import Dict, List
from pathlib import Path

class PatternLearnerAgent:
    def __init__(self, memory_agent):
        self.memory = memory_agent

    async def infer_patterns(self) -> Dict:
        """Analyze approved actions to learn organizational patterns"""
        experiences = await self.memory.get_feed_for_agent(tags=['approval'])
        patterns = {}
        
        for exp in experiences:
            # Example pattern extraction logic
            if 'mover' in exp['experience']:
                parts = exp['experience'].split()
                try:
                    src = parts[parts.index('mover')+1]
                    dest = parts[parts.index('para')+1]
                    
                    # Extract patterns from path
                    src_path = Path(src)
                    if src_path.suffix:
                        patterns.setdefault('extensions', {}).setdefault(
                            src_path.suffix.lower(), []
                        ).append(dest)
                    
                    # Extract patterns from filename
                    if any(char.isdigit() for char in src_path.stem):
                        patterns.setdefault('has_numbers', []).append(dest)
                        
                except (ValueError, IndexError):
                    continue
                    
        return patterns
