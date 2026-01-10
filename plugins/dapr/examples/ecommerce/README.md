# E-Commerce DAPR Example

A complete e-commerce application demonstrating DAPR building blocks with saga patterns.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         API Gateway                                 │
│                    (BFF - Backend for Frontend)                     │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┬─────────────┐
        ▼             ▼             ▼             ▼
┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐
│  Order    │  │ Inventory │  │  Payment  │  │  Notify   │
│  Service  │  │  Service  │  │  Service  │  │  Service  │
└───────────┘  └───────────┘  └───────────┘  └───────────┘
     │              │              │              │
     └──────────────┴──────────────┴──────────────┘
                         │
              ┌──────────┴──────────┐
              │    DAPR Sidecar     │
              │  - State Store      │
              │  - Pub/Sub          │
              │  - Workflows        │
              │  - Secrets          │
              └─────────────────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| api-gateway | 8000 | BFF aggregating backend calls |
| order-service | 8001 | Order management with workflow orchestration |
| inventory-service | 8002 | Stock management with actors |
| payment-service | 8003 | Payment processing |
| notification-service | 8004 | Event-driven notifications |

## DAPR Building Blocks Used

- **Service Invocation**: API gateway → backend services
- **Pub/Sub**: Order events, payment events, notifications
- **State Management**: Order state, inventory stock
- **Workflows**: Order saga orchestration
- **Actors**: Per-product inventory actors
- **Secrets**: Payment gateway credentials
- **Bindings**: Email notifications (output binding)

## Running Locally

```bash
# Start all services
dapr run -f dapr.yaml

# Or start individually
dapr run --app-id order-service --app-port 8001 --resources-path ./components -- python -m uvicorn services.order.main:app --port 8001
```

## Order Saga Flow

```
1. CreateOrder → Reserve Inventory → Process Payment → Ship Order → Complete
                      │                    │
                      ▼                    ▼
              (On Failure)          (On Failure)
            Release Inventory    Refund Payment + Release Inventory
```

## API Endpoints

### Orders
- `POST /api/orders` - Create new order
- `GET /api/orders/{id}` - Get order details
- `GET /api/orders/{id}/status` - Get order workflow status

### Inventory
- `GET /api/inventory/{product_id}` - Check stock
- `POST /api/inventory/{product_id}/reserve` - Reserve stock
- `POST /api/inventory/{product_id}/release` - Release reservation

### Payments
- `POST /api/payments` - Process payment
- `POST /api/payments/{id}/refund` - Refund payment

## Deployment

```bash
# Deploy to Azure Container Apps
/dapr:deploy aca

# Deploy to AKS
/dapr:deploy aks
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Integration tests with DAPR
dapr run -f dapr.yaml -- pytest tests/integration/ -v
```
