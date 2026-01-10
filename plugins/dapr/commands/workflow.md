---
description: Scaffold a new DAPR workflow with activities, error handling, and client code
---

# DAPR Workflow Scaffolding

Create a new DAPR workflow with all required components and best practices.

## Behavior

When the user runs `/dapr:workflow`:

1. **Gather Workflow Info**
   - Workflow name (from $ARGUMENTS or prompt)
   - Workflow pattern (sequential, parallel, saga, approval)
   - Number of activities
   - Brief description of each step

2. **Generate Workflow Code**

   ```python
   # workflows/{workflow_name}.py
   from dapr.ext.workflow import (
       WorkflowRuntime,
       DaprWorkflowContext,
       WorkflowActivityContext,
       RetryPolicy
   )
   from datetime import timedelta

   wf_runtime = WorkflowRuntime()

   # Retry policy
   retry_policy = RetryPolicy(
       max_number_of_attempts=3,
       first_retry_interval=timedelta(seconds=1),
       backoff_coefficient=2.0
   )

   @wf_runtime.workflow(name="{workflow_name}")
   def {workflow_name}_workflow(ctx: DaprWorkflowContext, input: dict):
       # Generated workflow logic
       pass

   @wf_runtime.activity(name="{activity_name}")
   def {activity_name}(ctx: WorkflowActivityContext, data: dict):
       # Generated activity logic
       pass
   ```

3. **Generate Client Code**

   ```python
   # clients/{workflow_name}_client.py
   from dapr.ext.workflow import DaprWorkflowClient

   async def start_{workflow_name}(input_data: dict):
       async with DaprWorkflowClient() as client:
           instance_id = await client.schedule_new_workflow(
               workflow="{workflow_name}",
               input=input_data
           )
           return instance_id
   ```

4. **Generate Tests**

   ```python
   # tests/test_{workflow_name}.py
   import pytest
   from workflows.{workflow_name} import *

   def test_{workflow_name}_activity():
       # Test activity logic
       pass
   ```

5. **Update Dependencies**
   - Add `dapr-ext-workflow` to requirements.txt if missing

## Arguments

- `$ARGUMENTS` - Workflow name and pattern:
  - `order-processing` - Basic workflow name
  - `order-processing --pattern saga` - With specific pattern
  - `order-processing --steps 5` - Number of steps

## Workflow Patterns

### Sequential (Default)
```
Step 1 → Step 2 → Step 3 → Done
```

### Parallel (Fan-Out/Fan-In)
```
         ┌→ Task A ─┐
Input ───┼→ Task B ─┼→ Aggregate → Done
         └→ Task C ─┘
```

### Saga (Compensating Transactions)
```
Step 1 → Step 2 → Step 3
   ↓        ↓        ↓
Comp 1 ← Comp 2 ← Comp 3 (on failure)
```

### Approval (Human in the Loop)
```
Submit → Wait for Event → Approved? → Process → Done
                              ↓
                         Rejected → Notify → Done
```

## Examples

```
/dapr:workflow order-processing
/dapr:workflow payment-saga --pattern saga
/dapr:workflow document-approval --pattern approval
/dapr:workflow batch-processing --pattern parallel --steps 3
```

## Generated Files

```
{project}/
├── workflows/
│   └── {workflow_name}.py      # Workflow definition
├── clients/
│   └── {workflow_name}_client.py  # Client for starting/querying
├── tests/
│   └── test_{workflow_name}.py    # Unit tests
└── components/
    └── statestore.yaml           # State store (if not exists)
```

## Saga Pattern Example

When `--pattern saga` is specified:

```python
@wf_runtime.workflow(name="order_saga")
def order_saga(ctx: DaprWorkflowContext, order: dict):
    compensations = []

    try:
        # Step 1: Reserve inventory
        reservation = yield ctx.call_activity(reserve_inventory, input=order)
        compensations.append(("cancel_reservation", reservation))

        # Step 2: Charge payment
        payment = yield ctx.call_activity(charge_payment, input=order)
        compensations.append(("refund_payment", payment))

        # Step 3: Ship order
        shipment = yield ctx.call_activity(create_shipment, input=order)

        return {"status": "success"}

    except Exception as e:
        # Compensate in reverse order
        for comp_name, comp_data in reversed(compensations):
            yield ctx.call_activity(comp_name, input=comp_data)

        return {"status": "failed", "error": str(e)}
```

## Approval Pattern Example

When `--pattern approval` is specified:

```python
@wf_runtime.workflow(name="approval_workflow")
def approval_workflow(ctx: DaprWorkflowContext, request: dict):
    # Send approval request
    yield ctx.call_activity(send_approval_request, input=request)

    # Wait for human response
    approval = yield ctx.wait_for_external_event("approval_response")

    if approval["approved"]:
        result = yield ctx.call_activity(process_approved, input=request)
        return {"status": "approved", "result": result}
    else:
        yield ctx.call_activity(notify_rejection, input=request)
        return {"status": "rejected"}
```

## Post-Generation Steps

After generating workflow:
1. Implement activity business logic
2. Configure state store component
3. Start workflow runtime
4. Test with sample input
