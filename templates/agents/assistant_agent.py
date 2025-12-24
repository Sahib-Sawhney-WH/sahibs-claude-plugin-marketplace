"""
DAPR Assistant Agent Template

A basic LLM-powered agent with tool calling capabilities.
Uses the dapr-agents framework for intelligent task execution.

Usage:
    dapr run --app-id my-agent --app-port 8000 --resources-path ./components -- python assistant_agent.py
"""

from dapr_agents import AssistantAgent, tool
from dapr_agents.memory import ConversationMemory
from pydantic import BaseModel, Field
from simpleeval import simple_eval
import os
import logging

# Note: Install simpleeval with: pip install simpleeval

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Tool Input Schemas (Pydantic models for validation)
# =============================================================================

class SearchInput(BaseModel):
    """Input schema for search tool."""
    query: str = Field(..., description="The search query")
    max_results: int = Field(default=5, description="Maximum number of results")


class CalculateInput(BaseModel):
    """Input schema for calculator tool."""
    expression: str = Field(..., description="Mathematical expression to evaluate")


# =============================================================================
# Tool Definitions
# =============================================================================

@tool
def search(input: SearchInput) -> str:
    """Search for information on a topic.

    Use this tool when you need to find information about something.
    Returns a list of relevant results.

    Args:
        input: Search parameters including query and max results

    Returns:
        Search results as a formatted string
    """
    logger.info(f"Searching for: {input.query}")
    # TODO: Implement actual search logic (e.g., web search, database query)
    return f"Found {input.max_results} results for '{input.query}':\n1. Result 1\n2. Result 2\n..."


@tool
def calculate(input: CalculateInput) -> str:
    """Evaluate a mathematical expression.

    Use this tool for any mathematical calculations.
    Supports basic arithmetic, exponents, and common functions.

    Args:
        input: The mathematical expression to evaluate

    Returns:
        The result of the calculation
    """
    logger.info(f"Calculating: {input.expression}")
    try:
        # Safe evaluation of mathematical expressions
        allowed_functions = {"abs": abs, "round": round, "min": min, "max": max}
        # Using simpleeval for safe expression evaluation (prevents code injection)
        result = simple_eval(input.expression, functions=allowed_functions)
        return f"Result: {result}"
    except Exception as e:
        return f"Error: Could not evaluate expression. {str(e)}"


@tool
def get_current_time() -> str:
    """Get the current date and time.

    Use this tool when asked about the current time or date.

    Returns:
        Current date and time as a formatted string
    """
    from datetime import datetime
    now = datetime.now()
    return f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}"


# =============================================================================
# Agent Configuration
# =============================================================================

def create_agent() -> AssistantAgent:
    """Create and configure the assistant agent."""

    # Configure memory (optional - enables conversation history)
    memory = ConversationMemory(
        max_messages=50,  # Keep last 50 messages
        state_store="statestore"  # Dapr state store for persistence
    )

    # Create the agent
    agent = AssistantAgent(
        name="assistant",
        role="Helpful Assistant",
        instructions="""You are a helpful AI assistant powered by DAPR.

Your capabilities:
- Search for information using the search tool
- Perform calculations using the calculate tool
- Tell the current time using get_current_time

Guidelines:
- Be concise and helpful
- Use tools when appropriate
- Explain your reasoning when asked
- If you're unsure, say so rather than guessing
""",
        tools=[search, calculate, get_current_time],
        memory=memory,
        model=os.getenv("LLM_MODEL", "gpt-4o"),  # Default to GPT-4o
        temperature=0.7,
        max_tokens=1000
    )

    return agent


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Run the assistant agent interactively."""
    agent = create_agent()
    logger.info(f"Agent '{agent.name}' initialized with {len(agent.tools)} tools")

    print("\n" + "=" * 50)
    print(f"  DAPR Assistant Agent: {agent.name}")
    print("=" * 50)
    print("Type 'quit' or 'exit' to stop")
    print("Type 'clear' to clear conversation history")
    print("=" * 50 + "\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit"]:
                print("Goodbye!")
                break

            if user_input.lower() == "clear":
                agent.memory.clear()
                print("Conversation history cleared.")
                continue

            # Run the agent
            response = agent.run(user_input)
            print(f"\nAssistant: {response}\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
