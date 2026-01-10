# Saga Patterns DAPR Example

Demonstrates different saga patterns for distributed transactions using DAPR Workflows.

## Saga Patterns Covered

### 1. Sequential Saga (Orchestration)
Traditional saga with sequential steps and compensation on failure.

```
Step1 → Step2 → Step3 → Complete
          │
          ▼ (on failure)
     Compensate2 → Compensate1
```

### 2. Parallel Saga
Execute independent steps in parallel, with coordinated compensation.

```
       ┌→ StepA ─┐
Start ─┼→ StepB ─┼→ Merge → Complete
       └→ StepC ─┘
```

### 3. Choreography Saga
Event-driven saga without central orchestrator.

```
Service A ──event──→ Service B ──event──→ Service C
    ▲                    │
    └───compensate───────┘ (on failure)
```

## Project Structure

```
saga-patterns/
├── dapr.yaml
├── components/
│   ├── statestore.yaml
│   └── pubsub.yaml
├── services/
│   ├── orchestrator/        # Saga coordinator
│   │   └── main.py          # Sequential & parallel sagas
│   ├── service-a/           # Participant A
│   │   └── main.py
│   ├── service-b/           # Participant B
│   │   └── main.py
│   └── service-c/           # Participant C
│       └── main.py
└── tests/
    └── test_sagas.py
```

## Running the Examples

```bash
# Start all services
dapr run -f dapr.yaml

# Test sequential saga
curl -X POST http://localhost:8000/saga/sequential \
  -H "Content-Type: application/json" \
  -d '{"order_id": "123", "amount": 100}'

# Test parallel saga
curl -X POST http://localhost:8000/saga/parallel \
  -H "Content-Type: application/json" \
  -d '{"batch_id": "456", "items": ["a", "b", "c"]}'

# Get saga status
curl http://localhost:8000/saga/{instance_id}/status
```

## Key Concepts

### Idempotency
All saga steps must be idempotent to handle retries safely:
```python
@activity
async def process_step(ctx, data: dict) -> dict:
    # Check if already processed
    existing = await get_state(data["id"])
    if existing:
        return existing  # Return cached result

    # Process and save state
    result = await do_work(data)
    await save_state(data["id"], result)
    return result
```

### Compensation
Each step should have a compensation function:
```python
@activity
async def reserve_inventory(ctx, data: dict) -> dict:
    # Forward operation
    return await inventory.reserve(data["items"])

@activity
async def compensate_inventory(ctx, reservation: dict) -> None:
    # Compensation operation (undo)
    await inventory.release(reservation["id"])
```

### Timeout Handling
Configure appropriate timeouts for long-running sagas:
```python
@workflow
def long_saga(ctx: DaprWorkflowContext, data: dict):
    # Set overall saga timeout
    deadline = ctx.current_utc_datetime + timedelta(hours=1)

    result = yield ctx.call_activity(
        long_operation,
        input=data,
        timeout=timedelta(minutes=5)
    )
```
