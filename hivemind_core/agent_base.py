from fastmcp import FastMCP

class BaseAgent:
    def __init__(self, name: str):
        self.name = name
        self.mcp = FastMCP(name=name)

    def add_tool(self, func):
        self.mcp.add_tool(func)

    def get_tools(self):
        return self.mcp.get_tools() 