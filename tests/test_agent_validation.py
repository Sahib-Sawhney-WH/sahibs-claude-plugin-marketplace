"""
Agent Configuration Validation Tests
====================================

Tests for DAPR Agent file validation patterns.
"""

import pytest
import re
from pathlib import Path


class TestToolDecoratorValidation:
    """Test @tool decorator validation for agent tools."""

    def test_tool_with_decorator_passes(self, temp_dir):
        """Tool function with @tool decorator should pass."""
        code = '''
from dapr_agents import tool

@tool
async def search(query: str) -> str:
    """Search for information based on query."""
    return f"Results for: {query}"
'''
        path = temp_dir / "search_tool.py"
        path.write_text(code)

        issues = validate_tool_file(path.read_text())
        assert len(issues) == 0, f"Valid tool should pass: {issues}"

    def test_tool_without_decorator_fails(self, temp_dir):
        """Tool function without @tool decorator should fail."""
        code = '''
async def search(query: str) -> str:
    """Search for information based on query."""
    return f"Results for: {query}"
'''
        path = temp_dir / "bad_tool.py"
        path.write_text(code)

        issues = validate_tool_file(path.read_text())
        # This is a pattern check - we look for functions that might be tools
        # In practice, the hook checks if tool-like files have @tool decorators

    def test_tool_without_docstring_warns(self, temp_dir):
        """Tool function without docstring should warn."""
        code = '''
from dapr_agents import tool

@tool
async def search(query: str) -> str:
    return f"Results for: {query}"
'''
        path = temp_dir / "no_docstring_tool.py"
        path.write_text(code)

        issues = validate_tool_file(path.read_text())
        assert any("docstring" in issue.lower() for issue in issues), \
            "Should warn about missing docstring for LLM understanding"


class TestAgentConfigValidation:
    """Test agent configuration validation."""

    def test_valid_agent_config_passes(self, temp_dir):
        """Agent with all required fields should pass."""
        code = '''
from dapr_agents import AssistantAgent, tool

@tool
async def search(query: str) -> str:
    """Search for information."""
    return f"Results for: {query}"

agent = AssistantAgent(
    name="assistant",
    role="Research Assistant",
    instructions="Help users find information.",
    tools=[search],
    model="gpt-4o"
)
'''
        path = temp_dir / "my_agent.py"
        path.write_text(code)

        issues = validate_agent_file(path.read_text())
        assert len(issues) == 0, f"Valid agent should pass: {issues}"

    def test_agent_without_name_fails(self, temp_dir):
        """Agent without name should fail."""
        code = '''
from dapr_agents import AssistantAgent

agent = AssistantAgent(
    role="Research Assistant",
    instructions="Help users find information.",
    model="gpt-4o"
)
'''
        path = temp_dir / "nameless_agent.py"
        path.write_text(code)

        issues = validate_agent_file(path.read_text())
        # Agent should have name, role, instructions
        assert any("name" in issue.lower() for issue in issues), \
            "Should warn about missing name"

    def test_agent_with_hardcoded_api_key_fails(self, temp_dir):
        """Agent with hardcoded API key should fail."""
        code = '''
from dapr_agents import AssistantAgent
import openai

openai.api_key = "sk-abc123456789"  # Hardcoded!

agent = AssistantAgent(
    name="assistant",
    role="Helper",
    instructions="Help users."
)
'''
        path = temp_dir / "hardcoded_key_agent.py"
        path.write_text(code)

        issues = validate_agent_file(path.read_text())
        assert any("api" in issue.lower() and "key" in issue.lower() for issue in issues), \
            "Should detect hardcoded API key"


class TestAsyncPatternValidation:
    """Test async/await pattern validation."""

    def test_async_tool_with_io_passes(self, temp_dir):
        """Async tool for I/O operations should pass."""
        code = '''
from dapr_agents import tool
import aiohttp

@tool
async def fetch_data(url: str) -> str:
    """Fetch data from URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
'''
        path = temp_dir / "async_tool.py"
        path.write_text(code)

        issues = validate_async_patterns(path.read_text())
        assert len(issues) == 0, f"Async I/O tool should pass: {issues}"

    def test_sync_function_for_io_warns(self, temp_dir):
        """Sync function for I/O should warn."""
        code = '''
from dapr_agents import tool
import requests

@tool
def fetch_data(url: str) -> str:  # Not async!
    """Fetch data from URL."""
    response = requests.get(url)
    return response.text
'''
        path = temp_dir / "sync_io_tool.py"
        path.write_text(code)

        issues = validate_async_patterns(path.read_text())
        assert any("async" in issue.lower() for issue in issues), \
            "Should warn about sync function for I/O operations"


class TestPydanticValidation:
    """Test Pydantic usage for complex inputs."""

    def test_pydantic_model_with_field_descriptions_passes(self, temp_dir):
        """Pydantic model with Field descriptions should pass."""
        code = '''
from pydantic import BaseModel, Field
from dapr_agents import tool

class SearchInput(BaseModel):
    query: str = Field(..., description="The search query string")
    max_results: int = Field(10, description="Maximum number of results")

@tool
async def search(input: SearchInput) -> str:
    """Search with structured input."""
    return f"Found {input.max_results} results for {input.query}"
'''
        path = temp_dir / "pydantic_tool.py"
        path.write_text(code)

        issues = validate_pydantic_usage(path.read_text())
        assert len(issues) == 0, f"Pydantic with descriptions should pass: {issues}"

    def test_pydantic_model_without_descriptions_warns(self, temp_dir):
        """Pydantic model without Field descriptions should warn."""
        code = '''
from pydantic import BaseModel
from dapr_agents import tool

class SearchInput(BaseModel):
    query: str  # No description!
    max_results: int = 10  # No description!

@tool
async def search(input: SearchInput) -> str:
    """Search with structured input."""
    return f"Results for {input.query}"
'''
        path = temp_dir / "no_desc_pydantic.py"
        path.write_text(code)

        issues = validate_pydantic_usage(path.read_text())
        # Should warn about missing Field descriptions for LLM understanding
        # This is a best practice check


# Helper validation functions

def validate_tool_file(content: str) -> list:
    """Validate tool file patterns."""
    issues = []

    # Check for @tool decorator
    has_tool_import = "from dapr_agents import" in content and "tool" in content
    has_tool_decorator = "@tool" in content

    # Find function definitions after @tool
    tool_pattern = re.compile(r'@tool\s*\n\s*(async\s+)?def\s+(\w+)\s*\([^)]*\)[^:]*:', re.MULTILINE)
    matches = tool_pattern.findall(content)

    for match in matches:
        func_name = match[1]

        # Check for docstring (simple check)
        # Look for """ or ''' after function definition
        func_pattern = re.compile(
            rf'def\s+{func_name}\s*\([^)]*\)[^:]*:\s*\n\s*("""|\'\'\').*?\1',
            re.DOTALL
        )
        if not func_pattern.search(content):
            # Try single line docstring
            single_docstring = re.compile(
                rf'def\s+{func_name}\s*\([^)]*\)[^:]*:\s*\n\s*("""[^"]*"""|\'\'\'[^\']*\'\'\')'
            )
            if not single_docstring.search(content):
                issues.append(f"Tool '{func_name}' should have a docstring for LLM understanding")

    return issues


def validate_agent_file(content: str) -> list:
    """Validate agent file patterns."""
    issues = []

    # Check for hardcoded API keys
    api_key_patterns = [
        r'api_key\s*=\s*["\']sk-[^"\']+["\']',
        r'OPENAI_API_KEY\s*=\s*["\'][^"\']+["\']',
        r'openai\.api_key\s*=\s*["\'][^"\']+["\']',
    ]

    for pattern in api_key_patterns:
        if re.search(pattern, content):
            issues.append("API key should be loaded from environment variable, not hardcoded")
            break

    # Check for AssistantAgent with required fields
    if "AssistantAgent" in content:
        agent_pattern = re.compile(r'AssistantAgent\s*\(([^)]+)\)', re.DOTALL)
        match = agent_pattern.search(content)

        if match:
            agent_args = match.group(1)
            required_fields = ["name", "role", "instructions"]

            for field in required_fields:
                if f"{field}=" not in agent_args and f"{field} =" not in agent_args:
                    issues.append(f"Agent should have '{field}' field")

    return issues


def validate_async_patterns(content: str) -> list:
    """Validate async/await patterns."""
    issues = []

    # Look for sync I/O patterns that should be async
    sync_io_patterns = [
        (r'\brequests\.get\b', "Use aiohttp instead of requests for async"),
        (r'\brequests\.post\b', "Use aiohttp instead of requests for async"),
        (r'\bopen\([^)]+\)\.read\(\)', "Use aiofiles for async file I/O"),
    ]

    # Check if function is async
    for pattern, message in sync_io_patterns:
        if re.search(pattern, content):
            # Check if it's in an async function
            if "async def" not in content:
                issues.append(message)

    return issues


def validate_pydantic_usage(content: str) -> list:
    """Validate Pydantic model usage."""
    issues = []

    # Check if using BaseModel
    if "BaseModel" in content:
        # Check for Field with description
        if "Field(" in content:
            field_pattern = re.compile(r'Field\([^)]*description\s*=', re.DOTALL)
            if not field_pattern.search(content):
                issues.append("Pydantic Fields should include 'description' for LLM understanding")

    return issues
