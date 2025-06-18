from fastmcp import FastMCP, Context
from typing import Dict, List
from datetime import datetime
import chromadb

mcp = FastMCP(name="MemoryAgent")

class MemoryStore:
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection("memories")
    
    async def add_memory(self, memory: Dict) -> bool:
        try:
            self.collection.add(
                documents=[memory['experience']],
                metadatas=[{
                    'timestamp': memory['timestamp'],
                    'tags': memory['tags'],
                    'source_agent': memory['source_agent'],
                    'reward': memory['reward']
                }],
                ids=[str(datetime.utcnow().timestamp())]
            )
            return True
        except Exception:
            return False
    
    async def query_memories(self, query: Dict) -> List[Dict]:
        results = self.collection.query(
            where=query,
            limit=100
        )
        return [{
            'experience': doc,
            **meta
        } for doc, meta in zip(results['documents'], results['metadatas'])]

class MemoryAgent:
    def __init__(self):
        self.memory_store = MemoryStore()
    
    async def post_memory_experience(self, experience: str, tags: List[str] = None, 
                                   source_agent: str = None, reward: float = 0.0) -> bool:
        memory = {
            'timestamp': datetime.utcnow().isoformat(),
            'experience': experience,
            'tags': tags or [],
            'source_agent': source_agent,
            'reward': reward
        }
        return await self.memory_store.add_memory(memory)
    
    async def get_feed_for_agent(self, tags: List[str] = None) -> List[Dict]:
        query = {}
        if tags:
            query['tags'] = {'$in': tags}
        return await self.memory_store.query_memories(query)

def get_memory_agent():
    return MemoryAgent()
