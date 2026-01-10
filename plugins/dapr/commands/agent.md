---
description: Create and scaffold DAPR AI agents with the dapr-agents framework
---

# DAPR Agent Generator

Create intelligent, durable AI agents powered by LLMs using the DAPR Agents framework.

## Behavior

When the user runs `/dapr:agent`:

1. **Determine Agent Type**
   - Assistant: Basic LLM-powered agent with tools
   - Durable: Workflow-backed agent with fault tolerance
   - Service: Headless agent exposed via REST API
   - Multi: Multi-agent orchestration system

2. **Generate Agent Code**
   - Create agent class with LLM integration
   - Add tool definitions with @tool decorator
   - Configure memory management
   - Set up Dapr components

3. **Create Supporting Files**
   - requirements.txt with dapr-agents dependencies
   - Component YAML for state/conversation
   - Dockerfile for containerization

## Arguments

| Argument | Description |
|----------|-------------|
| `assistant <name>` | Create a basic AssistantAgent |
| `durable <name>` | Create a workflow-backed DurableAgent |
| `service <name>` | Create a headless AgentService |
| `multi <name>` | Create a multi-agent system |
| `--tools` | Comma-separated list of tools to include |
| `--memory` | Memory type: short-term, long-term, vector |
| `--llm` | LLM provider: openai, azure, anthropic, ollama |

## Examples

### Basic Assistant Agent
```
/dapr:agent assistant weather-bot
```

Creates an agent that can:
- Process user queries
- Call tools dynamically
- Maintain conversation context

### Durable Agent with Tools
```
/dapr:agent durable order-processor --tools "inventory,payment,shipping"
```

Creates a fault-tolerant agent with:
- Workflow-backed execution
- Automatic retry on failures
- Persistent state across restarts

### Headless Agent Service
```
/dapr:agent service research-agent --memory vector
```

Creates a REST API agent with:
- HTTP endpoints for queries
- Vector memory for RAG
- Long-running task support

### Multi-Agent System
```
/dapr:agent multi customer-support --agents "triage,technical,billing"
```

Creates coordinated agents with:
- Pub/sub communication
- Workflow orchestration
- Specialized agent roles

## Generated Structure

### Assistant Agent
```
weather-bot/
├── agent.py                 # AssistantAgent implementation
├── tools.py                 # Tool definitions
├── requirements.txt         # dapr-agents dependencies
├── components/
│   ├── statestore.yaml      # Memory persistence
│   └── conversation.yaml    # LLM component
└── Dockerfile
```

### Durable Agent
```
order-processor/
├── agent.py                 # DurableAgent with workflow
├── workflow.py              # Agent workflow definition
├── tools.py                 # Tool definitions
├── activities.py            # Workflow activities
├── requirements.txt
├── components/
│   ├── statestore.yaml
│   ├── conversation.yaml
│   └── resiliency.yaml      # Retry policies
└── Dockerfile
```

### Multi-Agent System
```
customer-support/
├── dapr.yaml                # Multi-app configuration
├── agents/
│   ├── triage/
│   │   └── agent.py
│   ├── technical/
│   │   └── agent.py
│   └── billing/
│       └── agent.py
├── orchestrator/
│   └── workflow.py          # Agent orchestration
├── components/
│   ├── statestore.yaml
│   ├── pubsub.yaml          # Agent communication
│   └── conversation.yaml
└── requirements.txt
```

## Agent Types

### AssistantAgent
Basic agent with LLM integration and tool calling:
```python
from dapr_agents import AssistantAgent, tool

@tool
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: Sunny, 72°F"

agent = AssistantAgent(
    name="weather-bot",
    role="Weather Assistant",
    instructions="Help users with weather queries",
    tools=[get_weather]
)
```

### DurableAgent
Workflow-backed agent with fault tolerance:
```python
from dapr_agents import DurableAgent

agent = DurableAgent(
    name="order-processor",
    role="Order Processing Agent",
    workflow_name="order_workflow"
)
```

### AgentService
Headless agent as REST service:
```python
from dapr_agents import AgentService

service = AgentService(
    agent=agent,
    port=8000,
    enable_memory=True
)
service.start()
```

## Running the Agent

```bash
# Run with DAPR sidecar
dapr run --app-id weather-bot --app-port 8000 --resources-path ./components -- python agent.py

# Or with dapr.yaml for multi-agent
dapr run -f dapr.yaml
```

## LLM Configuration

Set environment variables for your LLM provider:

### OpenAI
```bash
export OPENAI_API_KEY="sk-..."
```

### Azure OpenAI
```bash
export AZURE_OPENAI_API_KEY="..."
export AZURE_OPENAI_ENDPOINT="https://..."
export AZURE_OPENAI_DEPLOYMENT="gpt-4"
```

### Ollama (Local)
```bash
export OLLAMA_MODEL="llama3"
```

## Memory Options

### Short-term (In-memory)
Default conversation history, cleared on restart.

### Long-term (Dapr State)
Persistent memory using Dapr state store.

### Vector (RAG)
Semantic memory with vector embeddings for retrieval-augmented generation.
