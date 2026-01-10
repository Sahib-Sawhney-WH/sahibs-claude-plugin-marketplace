# Agent Builder Skill

## Metadata
- **Name**: agent-builder
- **Trigger**: Auto-triggered when building AI agents with DAPR
- **Category**: AI Agent Development

## Description

Provides intelligent assistance for building AI agents with the DAPR Agents framework. Validates configuration, suggests patterns, and ensures best practices.

## Auto-Trigger Patterns

This skill activates when detecting:
- Creation of agent files (`*_agent.py`, `*agent*.py`)
- Import of `dapr_agents` or `dapr-agents`
- Agent configuration files
- Tool definitions with `@tool` decorator
- Workflow-backed agent patterns

## Capabilities

### 1. Agent Configuration Validation

Validates agent setup:
- Required imports present
- Agent name and role defined
- Instructions are comprehensive
- Model configuration is valid
- Tools are properly decorated

### 2. Pattern Recommendations

Suggests appropriate patterns based on use case:
- **AssistantAgent**: Basic interactive agents
- **DurableAgent**: Fault-tolerant long-running tasks
- **AgentService**: Headless REST API agents
- **Multi-Agent**: Complex orchestration

### 3. Tool Integration Check

Validates tool definitions:
- `@tool` decorator present
- Docstrings for LLM understanding
- Pydantic input validation
- Async for I/O operations
- Error handling

### 4. Memory Strategy Guidance

Recommends memory configuration:
- Short-term (conversation context)
- Long-term (DAPR state store)
- Vector memory (RAG scenarios)

### 5. LLM Configuration Check

Validates LLM setup:
- API key environment variables
- Model name configuration
- Temperature settings
- Token limits

## Validation Rules

### Agent Definition
```python
# Required elements:
from dapr_agents import AssistantAgent

agent = AssistantAgent(
    name="...",           # Required: unique identifier
    role="...",           # Required: agent's role
    instructions="...",   # Required: system prompt
    tools=[...],          # Optional: list of tools
    model="...",          # Optional: LLM model (default: gpt-4o)
)
```

### Tool Definition
```python
# Recommended pattern:
from dapr_agents import tool
from pydantic import BaseModel, Field

class ToolInput(BaseModel):
    """Input validation with descriptions."""
    param: str = Field(..., description="Parameter description")

@tool
async def my_tool(input: ToolInput) -> str:
    """
    Tool description for LLM.

    Args:
        input: Validated input parameters

    Returns:
        Tool result
    """
    # Implementation
    return result
```

### Workflow Agent
```python
# Durable agent pattern:
from dapr.ext.workflow import workflow, activity

@activity
async def agent_activity(ctx, data: dict) -> dict:
    """Durable activity with agent logic."""
    pass

@workflow
def agent_workflow(ctx: DaprWorkflowContext, data: dict):
    """Workflow orchestrating agent activities."""
    result = yield ctx.call_activity(agent_activity, input=data)
    return result
```

## Checklist

When building agents, ensure:

### Agent Setup
- [ ] Agent has unique `name`
- [ ] Clear `role` describing purpose
- [ ] Detailed `instructions` for LLM
- [ ] Appropriate `model` selected
- [ ] `temperature` set for use case

### Tools
- [ ] All tools have `@tool` decorator
- [ ] Docstrings explain tool purpose
- [ ] Complex inputs use Pydantic models
- [ ] Async used for I/O operations
- [ ] Errors handled gracefully

### Memory
- [ ] Short-term memory for context
- [ ] Long-term memory via DAPR state
- [ ] Vector memory if using RAG

### Security
- [ ] API keys in environment variables
- [ ] Input validation on tools
- [ ] No sensitive data in logs
- [ ] Rate limiting considered

### Durability (for DurableAgent)
- [ ] Activities are idempotent
- [ ] Workflow handles failures
- [ ] State is checkpointed
- [ ] Retry policies defined

## Common Issues

### 1. Missing Tool Docstrings
```python
# Bad: LLM won't know when to use
@tool
def my_tool(x: str) -> str:
    return x.upper()

# Good: Clear purpose
@tool
def my_tool(x: str) -> str:
    """Convert text to uppercase for formatting."""
    return x.upper()
```

### 2. Sync Tools with I/O
```python
# Bad: Blocks event loop
@tool
def fetch_data(url: str) -> str:
    return requests.get(url).text

# Good: Async for I/O
@tool
async def fetch_data(url: str) -> str:
    async with httpx.AsyncClient() as client:
        return (await client.get(url)).text
```

### 3. Hardcoded API Keys
```python
# Bad: Security risk
client = OpenAI(api_key="sk-...")

# Good: Environment variable
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

### 4. Missing Input Validation
```python
# Bad: No validation
@tool
def process(data: dict) -> str:
    return data["key"]  # May fail

# Good: Pydantic validation
class ProcessInput(BaseModel):
    key: str = Field(..., min_length=1)

@tool
def process(input: ProcessInput) -> str:
    return input.key
```

## Agent Patterns Reference

### Interactive Assistant
```python
agent = AssistantAgent(
    name="assistant",
    role="Helpful Assistant",
    instructions="Help users with their questions.",
    tools=[tool1, tool2],
    model="gpt-4o"
)
```

### Durable Research Agent
```python
@activity
async def research(ctx, topic: str) -> str:
    agent = AssistantAgent(...)
    return await agent.run(f"Research: {topic}")

@workflow
def research_workflow(ctx: DaprWorkflowContext, topic: str):
    result = yield ctx.call_activity(research, input=topic)
    return result
```

### REST API Agent
```python
@app.post("/chat")
async def chat(request: ChatRequest):
    response = await agent.run(request.message)
    return {"response": response}
```

### Multi-Agent System
```python
specialists = {
    "technical": technical_agent,
    "support": support_agent,
}

router = AssistantAgent(
    name="router",
    instructions="Route to appropriate specialist..."
)
```

## Environment Variables

Required for agent operation:

```bash
# LLM Configuration
OPENAI_API_KEY=sk-...           # OpenAI API key
AZURE_OPENAI_API_KEY=...        # Azure OpenAI key
AZURE_OPENAI_ENDPOINT=...       # Azure endpoint
LLM_MODEL=gpt-4o                # Default model

# DAPR Configuration
DAPR_HTTP_PORT=3500             # DAPR sidecar port
DAPR_GRPC_PORT=50001            # DAPR gRPC port

# State Store
STATE_STORE_NAME=statestore     # DAPR state store name

# Pub/Sub
PUBSUB_NAME=pubsub              # DAPR pub/sub name
```

## Templates

Use the `/dapr:agent` command to generate agent templates:

```bash
/dapr:agent assistant my-agent    # Basic assistant
/dapr:agent durable my-agent      # Workflow-backed
/dapr:agent service my-agent      # REST API agent
/dapr:agent multi my-system       # Multi-agent
```

## Related Resources

- Agent Templates: `templates/agents/`
- Pattern Templates: `templates/agents/patterns/`
- Tool Templates: `templates/agents/tools/`
- Integration Templates: `templates/integrations/`
