"""
DAPR Conversation Client Template
Building Block: Conversation (LLM Integration)

Features:
- Converse with LLMs (OpenAI, Azure OpenAI, Anthropic)
- Tool/function calling
- PII scrubbing
- Context management
- Streaming responses
"""
import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union

from dapr.clients import DaprClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LLM component name (from component YAML)
LLM_NAME = "{{LLM_NAME}}"


class Message:
    """Represents a conversation message."""

    def __init__(
        self,
        role: str,
        content: str,
        name: Optional[str] = None,
        tool_call_id: Optional[str] = None
    ):
        self.role = role
        self.content = content
        self.name = name
        self.tool_call_id = tool_call_id

    def to_dict(self) -> Dict[str, Any]:
        msg = {"role": self.role, "content": self.content}
        if self.name:
            msg["name"] = self.name
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        return msg


class Tool:
    """Represents a callable tool/function."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class ConversationClient:
    """
    Client for DAPR Conversation building block.

    Enables LLM interactions with tool calling and PII handling.
    """

    def __init__(
        self,
        llm_name: str = LLM_NAME,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        scrub_pii: bool = False
    ):
        """
        Initialize conversation client.

        Args:
            llm_name: DAPR LLM component name
            temperature: Model temperature (0.0-1.0)
            max_tokens: Maximum response tokens
            scrub_pii: Enable PII scrubbing
        """
        self.llm_name = llm_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.scrub_pii = scrub_pii
        self.tools: Dict[str, Tool] = {}
        self.context_id: Optional[str] = None

    def register_tool(self, tool: Tool) -> None:
        """Register a tool for function calling."""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    async def chat(
        self,
        messages: List[Message],
        context_id: Optional[str] = None,
        tools_enabled: bool = True
    ) -> str:
        """
        Send a conversation and get a response.

        Args:
            messages: List of conversation messages
            context_id: Optional context for multi-turn conversations
            tools_enabled: Allow tool/function calling

        Returns:
            LLM response text

        Example:
            response = await client.chat([
                Message("system", "You are a helpful assistant."),
                Message("user", "What's the weather in Seattle?")
            ])
        """
        async with DaprClient() as client:
            # Build request
            request = {
                "inputs": [{"messages": [m.to_dict() for m in messages]}],
                "temperature": self.temperature,
                "scrubPii": self.scrub_pii
            }

            if context_id or self.context_id:
                request["contextId"] = context_id or self.context_id

            if tools_enabled and self.tools:
                request["tools"] = [t.to_dict() for t in self.tools.values()]
                request["toolChoice"] = "auto"

            # Make API call
            response = await client.converse(
                name=self.llm_name,
                inputs=request
            )

            # Handle tool calls if present
            if hasattr(response, "tool_calls") and response.tool_calls:
                return await self._handle_tool_calls(messages, response, context_id)

            # Store context for future calls
            if hasattr(response, "context_id"):
                self.context_id = response.context_id

            return response.outputs[0].content if response.outputs else ""

    async def _handle_tool_calls(
        self,
        messages: List[Message],
        response: Any,
        context_id: Optional[str]
    ) -> str:
        """Handle tool/function calls from the LLM."""
        tool_results = []

        for tool_call in response.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            logger.info(f"Tool call: {tool_name}({tool_args})")

            if tool_name in self.tools:
                # Execute the tool
                result = await self.tools[tool_name].handler(**tool_args)
                tool_results.append(Message(
                    role="tool",
                    content=json.dumps(result),
                    tool_call_id=tool_call.id,
                    name=tool_name
                ))
            else:
                logger.warning(f"Unknown tool: {tool_name}")

        # Add tool results and continue conversation
        new_messages = messages + [
            Message("assistant", response.outputs[0].content if response.outputs else "")
        ] + tool_results

        return await self.chat(new_messages, context_id, tools_enabled=False)

    async def simple_chat(self, user_message: str, system_prompt: Optional[str] = None) -> str:
        """
        Simple single-turn conversation.

        Args:
            user_message: User's message
            system_prompt: Optional system prompt

        Returns:
            LLM response

        Example:
            response = await client.simple_chat("Hello, how are you?")
        """
        messages = []
        if system_prompt:
            messages.append(Message("system", system_prompt))
        messages.append(Message("user", user_message))

        return await self.chat(messages)


# =============================================================================
# Tool Definition Helpers
# =============================================================================

def create_tool(
    name: str,
    description: str,
    handler: Callable,
    parameters: Optional[Dict[str, Any]] = None
) -> Tool:
    """
    Create a tool for function calling.

    Args:
        name: Tool name
        description: What the tool does
        handler: Async function to execute
        parameters: JSON Schema for parameters

    Example:
        get_weather = create_tool(
            name="get_weather",
            description="Get current weather for a location",
            handler=fetch_weather,
            parameters={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                    "units": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                },
                "required": ["location"]
            }
        )
    """
    return Tool(
        name=name,
        description=description,
        parameters=parameters or {"type": "object", "properties": {}},
        handler=handler
    )


# =============================================================================
# FastAPI Integration Example
# =============================================================================

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Conversation AI Service")

# Initialize client with tools
conversation = ConversationClient(scrub_pii=True)


# Example tool handlers
async def get_weather(location: str, units: str = "celsius") -> dict:
    """Fetch weather for a location (mock implementation)."""
    # Replace with actual weather API call
    return {
        "location": location,
        "temperature": 22 if units == "celsius" else 72,
        "units": units,
        "conditions": "Partly cloudy"
    }


async def search_products(query: str, max_results: int = 5) -> dict:
    """Search product catalog (mock implementation)."""
    # Replace with actual product search
    return {
        "query": query,
        "results": [
            {"id": "1", "name": f"Product matching '{query}'", "price": 29.99}
        ]
    }


# Register tools
conversation.register_tool(create_tool(
    name="get_weather",
    description="Get the current weather for a location",
    handler=get_weather,
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name"},
            "units": {"type": "string", "enum": ["celsius", "fahrenheit"], "default": "celsius"}
        },
        "required": ["location"]
    }
))

conversation.register_tool(create_tool(
    name="search_products",
    description="Search the product catalog",
    handler=search_products,
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "default": 5}
        },
        "required": ["query"]
    }
))


class ChatRequest(BaseModel):
    message: str
    system_prompt: Optional[str] = None
    context_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    context_id: Optional[str] = None


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the AI assistant."""
    try:
        messages = []
        if request.system_prompt:
            messages.append(Message("system", request.system_prompt))
        messages.append(Message("user", request.message))

        response = await conversation.chat(
            messages=messages,
            context_id=request.context_id
        )

        return ChatResponse(
            response=response,
            context_id=conversation.context_id
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/simple-chat")
async def simple_chat(message: str):
    """Simple chat endpoint."""
    response = await conversation.simple_chat(message)
    return {"response": response}


# =============================================================================
# CLI Usage Example
# =============================================================================

if __name__ == "__main__":
    async def main():
        client = ConversationClient()

        # Register a weather tool
        client.register_tool(create_tool(
            name="get_weather",
            description="Get weather for a location",
            handler=get_weather,
            parameters={
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                },
                "required": ["location"]
            }
        ))

        # Simple chat
        response = await client.simple_chat(
            "Hello! What's the weather like in Seattle?",
            system_prompt="You are a helpful assistant. Use tools when needed."
        )
        print(f"Assistant: {response}")

        # Multi-turn conversation
        messages = [
            Message("system", "You are a helpful shopping assistant."),
            Message("user", "I'm looking for headphones under $100")
        ]
        response = await client.chat(messages)
        print(f"Shopping Assistant: {response}")

    asyncio.run(main())
