# IoT Processing DAPR Example

A real-time IoT event processing application using DAPR building blocks.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Device Gateway                                    │
│              (Input Bindings - MQTT/HTTP)                           │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Event Processor                                   │
│              (Pub/Sub + State Store)                                │
└─────────────────────┬───────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌───────────┐  ┌───────────┐  ┌───────────┐
│  Device   │  │ Analytics │  │ Alerting  │
│  Actor    │  │  Service  │  │  Service  │
└───────────┘  └───────────┘  └───────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| device-gateway | 8000 | Ingests device telemetry via bindings |
| device-actor | 8001 | Per-device state and logic |
| analytics-service | 8002 | Real-time stream processing |
| alerting-service | 8003 | Threshold monitoring and alerts |

## DAPR Building Blocks Used

- **Input Bindings**: MQTT, HTTP for device ingestion
- **Output Bindings**: Email, SMS for alerts
- **Pub/Sub**: Device events, analytics events, alerts
- **State Management**: Device state, analytics aggregations
- **Actors**: Per-device state management
- **Configuration**: Alert thresholds, device configuration
- **Distributed Lock**: Exclusive analytics aggregation

## Running Locally

```bash
# Start infrastructure (Mosquitto MQTT broker, Redis)
docker-compose up -d

# Start all services
dapr run -f dapr.yaml
```

## Device Event Flow

```
1. Device → MQTT → Device Gateway → Pub/Sub
2. Device Actor updates state → checks thresholds
3. Analytics Service aggregates → stores metrics
4. Alerting Service → sends notifications if threshold exceeded
```

## API Endpoints

### Device Gateway
- `POST /devices/{id}/telemetry` - Send telemetry data
- `GET /devices/{id}` - Get device info

### Device Actor
- `GET /actors/DeviceActor/{id}/state` - Get device state
- `POST /actors/DeviceActor/{id}/configure` - Update device config

### Analytics
- `GET /analytics/devices/{id}` - Get device analytics
- `GET /analytics/summary` - Get fleet summary

### Alerts
- `GET /alerts` - List active alerts
- `POST /alerts/{id}/acknowledge` - Acknowledge alert
