"""
MCP (Model Context Protocol) Integration

Integrate external MCP servers with DAPR Agents.
MCP provides a standardized way to discover and use tools from external sources.

Key Features:
- Dynamic tool discovery from MCP servers
- Support for stdio and SSE transports
- Automatic tool schema mapping
- Multiple MCP server aggregation
"""

from dapr_agents import AssistantAgent
from dapr_agents.mcp import MCPClient, MCPServerConfig
from typing import List, Optional
import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# MCP Server Configurations
# =============================================================================

# Example MCP servers (customize for your needs)
MCP_SERVERS = [
    # Filesystem MCP server
    MCPServerConfig(
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/data"],
        transport="stdio"
    ),

    # PostgreSQL MCP server
    MCPServerConfig(
        name="postgres",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-postgres"],
        env={
            "POSTGRES_CONNECTION_STRING": os.getenv(
                "POSTGRES_CONNECTION_STRING",
                "postgresql://user:pass@localhost:5432/db"
            )
        },
        transport="stdio"
    ),

    # GitHub MCP server
    MCPServerConfig(
        name="github",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={
            "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_TOKEN", "")
        },
        transport="stdio"
    ),

    # Custom HTTP-based MCP server (SSE transport)
    # MCPServerConfig(
    #     name="custom-mcp",
    #     url="http://localhost:3001/mcp",
    #     transport="sse"
    # ),
]


# =============================================================================
# MCP Client Setup
# =============================================================================

class MCPToolProvider:
    """
    Provider for MCP-based tools.
    Connects to MCP servers and provides tools to agents.
    """

    def __init__(self, servers: List[MCPServerConfig]):
        self.servers = servers
        self.clients: dict = {}
        self.tools: list = []

    async def connect_all(self):
        """Connect to all configured MCP servers."""
        for server in self.servers:
            try:
                logger.info(f"Connecting to MCP server: {server.name}")
                client = MCPClient(server)
                await client.connect()
                self.clients[server.name] = client

                # Discover tools from this server
                server_tools = await client.list_tools()
                logger.info(f"Discovered {len(server_tools)} tools from {server.name}")
                self.tools.extend(server_tools)

            except Exception as e:
                logger.error(f"Failed to connect to {server.name}: {e}")

    async def disconnect_all(self):
        """Disconnect from all MCP servers."""
        for name, client in self.clients.items():
            try:
                await client.disconnect()
                logger.info(f"Disconnected from {name}")
            except Exception as e:
                logger.error(f"Error disconnecting from {name}: {e}")

    def get_tools(self) -> list:
        """Get all discovered tools."""
        return self.tools

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict):
        """Call a tool on a specific MCP server."""
        if server_name not in self.clients:
            raise ValueError(f"Unknown server: {server_name}")

        client = self.clients[server_name]
        return await client.call_tool(tool_name, arguments)


# =============================================================================
# Agent with MCP Tools
# =============================================================================

async def create_mcp_agent(
    name: str = "mcp-agent",
    servers: Optional[List[MCPServerConfig]] = None
) -> AssistantAgent:
    """
    Create an agent with MCP tools.

    Args:
        name: Agent name
        servers: List of MCP server configs (uses defaults if not provided)

    Returns:
        Configured AssistantAgent with MCP tools
    """
    provider = MCPToolProvider(servers or MCP_SERVERS)
    await provider.connect_all()

    agent = AssistantAgent(
        name=name,
        role="MCP-Enabled Assistant",
        instructions="""You have access to tools from multiple MCP servers.
        Use the appropriate tool for each task.
        Available capabilities include file operations, database queries, and more.""",
        tools=provider.get_tools(),
        model=os.getenv("LLM_MODEL", "gpt-4o")
    )

    # Store provider reference for cleanup
    agent._mcp_provider = provider

    return agent


# =============================================================================
# MCP with DAPR State for Session Management
# =============================================================================

from dapr.clients import DaprClient

class MCPSessionManager:
    """
    Manage MCP sessions with DAPR state persistence.
    Tracks tool usage and maintains session context.
    """

    def __init__(self, store_name: str = "statestore"):
        self.store_name = store_name

    async def save_session(self, session_id: str, data: dict):
        """Save session data to DAPR state."""
        async with DaprClient() as client:
            await client.save_state(
                store_name=self.store_name,
                key=f"mcp-session-{session_id}",
                value=data
            )

    async def load_session(self, session_id: str) -> Optional[dict]:
        """Load session data from DAPR state."""
        async with DaprClient() as client:
            state = await client.get_state(
                store_name=self.store_name,
                key=f"mcp-session-{session_id}"
            )
            return state.data if state.data else None

    async def log_tool_usage(self, session_id: str, tool_name: str, result: str):
        """Log tool usage for auditing."""
        async with DaprClient() as client:
            await client.publish_event(
                pubsub_name="pubsub",
                topic_name="mcp-tool-usage",
                data={
                    "session_id": session_id,
                    "tool_name": tool_name,
                    "result_preview": result[:200] if result else None
                }
            )


# =============================================================================
# FastAPI Service with MCP Agent
# =============================================================================

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid

app = FastAPI(title="MCP Agent Service")

# Global agent instance
mcp_agent: Optional[AssistantAgent] = None
session_manager = MCPSessionManager()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    response: str


@app.on_event("startup")
async def startup():
    global mcp_agent
    # Only connect to available servers
    available_servers = [
        s for s in MCP_SERVERS
        if s.name == "filesystem"  # Start with just filesystem
    ]
    mcp_agent = await create_mcp_agent(servers=available_servers)
    logger.info("MCP Agent initialized")


@app.on_event("shutdown")
async def shutdown():
    if mcp_agent and hasattr(mcp_agent, "_mcp_provider"):
        await mcp_agent._mcp_provider.disconnect_all()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the MCP-enabled agent."""
    session_id = request.session_id or str(uuid.uuid4())

    # Load session context if exists
    session_data = await session_manager.load_session(session_id)
    context = session_data.get("context", []) if session_data else []

    # Run agent
    response = await mcp_agent.run(request.message)

    # Save updated session
    context.append({"role": "user", "content": request.message})
    context.append({"role": "assistant", "content": response})
    await session_manager.save_session(session_id, {"context": context[-20:]})

    return ChatResponse(session_id=session_id, response=response)


@app.get("/tools")
async def list_tools():
    """List available MCP tools."""
    if not mcp_agent or not hasattr(mcp_agent, "_mcp_provider"):
        return {"tools": []}

    tools = mcp_agent._mcp_provider.get_tools()
    return {
        "tools": [
            {"name": t.name, "description": t.description}
            for t in tools
        ]
    }


# =============================================================================
# Example: Custom MCP Server
# =============================================================================

"""
## Creating a Custom MCP Server

You can create your own MCP server to expose tools. Here's a minimal example:

### Python MCP Server (using mcp package)

```python
from mcp import Server, Tool
from mcp.transports import StdioTransport

server = Server("my-custom-server")

@server.tool("get_weather")
async def get_weather(city: str) -> str:
    '''Get weather for a city.'''
    # Your implementation
    return f"Weather for {city}: Sunny, 72F"

@server.tool("search_products")
async def search_products(query: str, limit: int = 10) -> list:
    '''Search product catalog.'''
    # Your implementation
    return [{"name": "Product 1", "price": 99.99}]

if __name__ == "__main__":
    transport = StdioTransport()
    server.run(transport)
```

### Connecting to Your Server

```python
custom_server = MCPServerConfig(
    name="my-server",
    command="python",
    args=["my_mcp_server.py"],
    transport="stdio"
)
```

## MCP Tool Discovery

MCP tools are automatically discovered and converted to DAPR Agent tools.
The agent receives:
- Tool name
- Description (for LLM to decide when to use)
- Input schema (for validation)

## Best Practices

1. **Error Handling**: MCP tools should return structured errors
2. **Timeouts**: Configure appropriate timeouts for slow operations
3. **Retry Logic**: Implement retry for transient failures
4. **Logging**: Log tool calls for debugging
5. **Security**: Validate inputs in MCP servers
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
