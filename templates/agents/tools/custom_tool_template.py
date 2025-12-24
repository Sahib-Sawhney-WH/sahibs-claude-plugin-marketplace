"""
Custom Tool Template

Template for creating custom tools for DAPR Agents.
Tools enable agents to interact with external systems and perform actions.

Usage:
    1. Define your tool function with @tool decorator
    2. Add Pydantic input validation
    3. Implement tool logic
    4. Register with your agent
"""

from dapr_agents import tool, AssistantAgent
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import httpx
from datetime import datetime
from simpleeval import simple_eval

# Note: Install simpleeval with: pip install simpleeval

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Tool Input Models (Pydantic validation)
# =============================================================================

class SearchInput(BaseModel):
    """Input schema for search tool."""
    query: str = Field(..., description="The search query")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results")
    category: Optional[str] = Field(default=None, description="Filter by category")


class DatabaseQueryInput(BaseModel):
    """Input schema for database query tool."""
    table: str = Field(..., description="Table name to query")
    filters: dict = Field(default_factory=dict, description="Query filters")
    limit: int = Field(default=50, ge=1, le=1000)


class EmailInput(BaseModel):
    """Input schema for sending emails."""
    to: List[str] = Field(..., description="Recipient email addresses")
    subject: str = Field(..., max_length=200)
    body: str = Field(..., description="Email body content")
    html: bool = Field(default=False, description="Send as HTML email")


# =============================================================================
# Basic Tool Examples
# =============================================================================

@tool
def get_current_datetime() -> str:
    """
    Get the current date and time.

    Returns:
        Current datetime in ISO format
    """
    return datetime.now().isoformat()


@tool
def calculate_expression(expression: str) -> str:
    """
    Safely evaluate a mathematical expression.

    Args:
        expression: Mathematical expression like "2 + 2" or "sqrt(16)"

    Returns:
        Result of the calculation
    """
    import math

    # Define safe operations
    safe_functions = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
    }
    safe_names = {
        "pi": math.pi,
        "e": math.e,
    }

    try:
        # Using simpleeval for safe expression evaluation (prevents code injection)
        result = simple_eval(expression, functions=safe_functions, names=safe_names)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"


# =============================================================================
# Async Tool Examples
# =============================================================================

@tool
async def fetch_url(url: str) -> str:
    """
    Fetch content from a URL.

    Args:
        url: The URL to fetch

    Returns:
        Response text (truncated to 5000 chars)
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30)
        response.raise_for_status()
        content = response.text[:5000]
        return content


@tool
async def search_api(input: SearchInput) -> str:
    """
    Search an external API with validated input.

    Args:
        input: Validated search parameters

    Returns:
        Search results as JSON string
    """
    # Example: Replace with your actual API endpoint
    async with httpx.AsyncClient() as client:
        params = {
            "q": input.query,
            "limit": input.max_results,
        }
        if input.category:
            params["category"] = input.category

        # Placeholder - replace with actual API
        logger.info(f"Searching for: {input.query}")
        return f"Search results for '{input.query}' (placeholder)"


# =============================================================================
# Tool with Complex Input
# =============================================================================

@tool
async def query_database(input: DatabaseQueryInput) -> str:
    """
    Query a database with filters.

    Args:
        input: Database query parameters

    Returns:
        Query results
    """
    logger.info(f"Querying table {input.table} with filters: {input.filters}")

    # Placeholder - integrate with actual database
    return f"Query results from {input.table} (placeholder)"


@tool
async def send_email(input: EmailInput) -> str:
    """
    Send an email (placeholder implementation).

    Args:
        input: Email parameters

    Returns:
        Send status
    """
    logger.info(f"Sending email to {input.to}: {input.subject}")

    # Placeholder - integrate with email service
    return f"Email sent to {', '.join(input.to)}"


# =============================================================================
# Tool with Side Effects and State
# =============================================================================

class NoteStorage:
    """Simple in-memory note storage."""

    def __init__(self):
        self.notes: dict = {}

    def save(self, key: str, content: str):
        self.notes[key] = {
            "content": content,
            "created": datetime.now().isoformat()
        }

    def get(self, key: str) -> Optional[dict]:
        return self.notes.get(key)

    def list_all(self) -> List[str]:
        return list(self.notes.keys())


# Global storage instance
note_storage = NoteStorage()


@tool
def save_note(key: str, content: str) -> str:
    """
    Save a note with a key.

    Args:
        key: Unique identifier for the note
        content: Note content

    Returns:
        Confirmation message
    """
    note_storage.save(key, content)
    return f"Note saved with key: {key}"


@tool
def get_note(key: str) -> str:
    """
    Retrieve a note by key.

    Args:
        key: Note identifier

    Returns:
        Note content or error message
    """
    note = note_storage.get(key)
    if note:
        return f"Content: {note['content']} (created: {note['created']})"
    return f"No note found with key: {key}"


@tool
def list_notes() -> str:
    """
    List all saved note keys.

    Returns:
        List of note keys
    """
    keys = note_storage.list_all()
    if keys:
        return f"Notes: {', '.join(keys)}"
    return "No notes saved"


# =============================================================================
# Creating an Agent with Tools
# =============================================================================

def create_agent_with_tools():
    """Example of creating an agent with custom tools."""

    agent = AssistantAgent(
        name="tool-demo",
        role="Tool Demo Agent",
        instructions="""You are a helpful assistant with access to various tools.
        Use the appropriate tool for each task.
        Always explain what you're doing before using a tool.""",
        tools=[
            get_current_datetime,
            calculate_expression,
            fetch_url,
            save_note,
            get_note,
            list_notes,
        ],
        model="gpt-4o"
    )

    return agent


# =============================================================================
# Tool Best Practices
# =============================================================================

"""
## Tool Design Best Practices

1. **Clear Descriptions**: Write detailed docstrings - LLMs use these to decide when to use tools

2. **Input Validation**: Use Pydantic models for complex inputs with proper Field descriptions

3. **Error Handling**: Return informative error messages, don't raise exceptions

4. **Async for I/O**: Use async for network requests, database queries, file operations

5. **Idempotency**: Design tools to be safe to retry

6. **Logging**: Log tool invocations for debugging

7. **Security**: Validate and sanitize all inputs, especially for database/system calls

## Tool Naming Convention

- Use verb_noun format: `get_user`, `send_email`, `calculate_total`
- Be specific: `search_products` not just `search`
- Match the action: `create_`, `update_`, `delete_`, `get_`, `list_`

## Complex Tool Pattern

For tools with many parameters:

```python
class ComplexInput(BaseModel):
    '''Document all fields clearly.'''
    required_field: str = Field(..., description="This field is required")
    optional_field: Optional[str] = Field(default=None, description="Optional with default")
    validated_field: int = Field(default=10, ge=1, le=100, description="With validation")

@tool
async def complex_tool(input: ComplexInput) -> str:
    '''Tool description for the LLM.'''
    # Implementation
    pass
```
"""


if __name__ == "__main__":
    # Demo the agent
    import asyncio

    agent = create_agent_with_tools()

    async def demo():
        result = await agent.run("What time is it? Also calculate 15 * 7 + 23")
        print(result)

    asyncio.run(demo())
