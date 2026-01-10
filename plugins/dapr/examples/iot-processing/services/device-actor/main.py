"""Device Actor Service - Per-device state and telemetry processing with DAPR Actors."""

from fastapi import FastAPI
from pydantic import BaseModel
from dapr.clients import DaprClient
from dapr.actor import Actor, ActorInterface, ActorProxy, actormethod
from dapr.ext.fastapi import DaprActor
from datetime import datetime, timedelta
import os
import logging
import statistics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Device Actor Service")
actor_runtime = DaprActor(app)


# =============================================================================
# Models
# =============================================================================

class TelemetryData(BaseModel):
    temperature: float | None = None
    humidity: float | None = None
    pressure: float | None = None
    battery: float | None = None
    timestamp: str = None


class DeviceConfig(BaseModel):
    temp_threshold_high: float = 30.0
    temp_threshold_low: float = 10.0
    humidity_threshold_high: float = 80.0
    report_interval_seconds: int = 60


class DeviceState(BaseModel):
    device_id: str
    last_seen: str | None = None
    config: DeviceConfig = DeviceConfig()
    readings: list[TelemetryData] = []  # Last N readings
    status: str = "unknown"  # online, offline, alert
    alerts: list[str] = []


# =============================================================================
# Device Actor Interface
# =============================================================================

class DeviceActorInterface(ActorInterface):
    @actormethod(name="ProcessTelemetry")
    async def process_telemetry(self, data: dict) -> dict: ...

    @actormethod(name="GetState")
    async def get_state(self) -> dict: ...

    @actormethod(name="Configure")
    async def configure(self, config: dict) -> dict: ...

    @actormethod(name="GetAnalytics")
    async def get_analytics(self) -> dict: ...


# =============================================================================
# Device Actor Implementation
# =============================================================================

class DeviceActor(Actor, DeviceActorInterface):
    """Actor managing state for a single IoT device."""

    MAX_READINGS = 100  # Keep last 100 readings

    def __init__(self, ctx, actor_id):
        super().__init__(ctx, actor_id)
        self._state: DeviceState | None = None

    async def _on_activate(self) -> None:
        """Load device state when actor activates."""
        logger.info(f"Activating device actor: {self.id.id}")
        state = await self._state_manager.try_get_state("device_state")
        if state:
            self._state = DeviceState(**state)
        else:
            self._state = DeviceState(device_id=self.id.id)
            await self._save_state()

        # Register timer for offline detection
        await self.register_timer(
            "offline_check",
            self._check_offline,
            state=None,
            due_time=timedelta(seconds=120),
            period=timedelta(seconds=60)
        )

    async def _on_deactivate(self) -> None:
        """Save state when actor deactivates."""
        await self._save_state()

    async def _save_state(self) -> None:
        """Persist device state."""
        await self._state_manager.set_state("device_state", self._state.model_dump())
        await self._state_manager.save_state()

    async def _check_offline(self, state) -> None:
        """Timer callback to check if device is offline."""
        if self._state.last_seen:
            last_seen = datetime.fromisoformat(self._state.last_seen)
            if datetime.utcnow() - last_seen > timedelta(minutes=5):
                if self._state.status != "offline":
                    self._state.status = "offline"
                    await self._publish_alert("device_offline", f"Device {self.id.id} is offline")
                    await self._save_state()

    async def _publish_alert(self, alert_type: str, message: str) -> None:
        """Publish an alert event."""
        async with DaprClient() as client:
            await client.publish_event(
                pubsub_name="pubsub",
                topic_name="alerts",
                data={
                    "device_id": self.id.id,
                    "type": alert_type,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    async def _check_thresholds(self, data: TelemetryData) -> list[str]:
        """Check telemetry against thresholds."""
        alerts = []
        config = self._state.config

        if data.temperature is not None:
            if data.temperature > config.temp_threshold_high:
                alerts.append(f"High temperature: {data.temperature}°C")
            elif data.temperature < config.temp_threshold_low:
                alerts.append(f"Low temperature: {data.temperature}°C")

        if data.humidity is not None:
            if data.humidity > config.humidity_threshold_high:
                alerts.append(f"High humidity: {data.humidity}%")

        if data.battery is not None and data.battery < 20:
            alerts.append(f"Low battery: {data.battery}%")

        return alerts

    async def process_telemetry(self, data: dict) -> dict:
        """Process incoming telemetry data."""
        telemetry = TelemetryData(**data)
        telemetry.timestamp = datetime.utcnow().isoformat()

        # Update state
        self._state.last_seen = telemetry.timestamp
        self._state.status = "online"
        self._state.readings.append(telemetry)

        # Keep only last N readings
        if len(self._state.readings) > self.MAX_READINGS:
            self._state.readings = self._state.readings[-self.MAX_READINGS:]

        # Check thresholds
        alerts = await self._check_thresholds(telemetry)
        if alerts:
            self._state.status = "alert"
            self._state.alerts = alerts
            for alert in alerts:
                await self._publish_alert("threshold_exceeded", alert)

        await self._save_state()

        # Publish to analytics
        async with DaprClient() as client:
            await client.publish_event(
                pubsub_name="pubsub",
                topic_name="device-telemetry",
                data={
                    "device_id": self.id.id,
                    **telemetry.model_dump()
                }
            )

        return {
            "processed": True,
            "device_id": self.id.id,
            "status": self._state.status,
            "alerts": alerts
        }

    async def get_state(self) -> dict:
        """Get current device state."""
        return self._state.model_dump()

    async def configure(self, config: dict) -> dict:
        """Update device configuration."""
        self._state.config = DeviceConfig(**config)
        await self._save_state()
        logger.info(f"Device {self.id.id} configured: {config}")
        return {"success": True, "config": self._state.config.model_dump()}

    async def get_analytics(self) -> dict:
        """Get analytics for this device."""
        if not self._state.readings:
            return {"device_id": self.id.id, "analytics": None}

        temps = [r.temperature for r in self._state.readings if r.temperature is not None]
        humidities = [r.humidity for r in self._state.readings if r.humidity is not None]

        return {
            "device_id": self.id.id,
            "reading_count": len(self._state.readings),
            "temperature": {
                "min": min(temps) if temps else None,
                "max": max(temps) if temps else None,
                "avg": statistics.mean(temps) if temps else None,
                "stddev": statistics.stdev(temps) if len(temps) > 1 else None
            },
            "humidity": {
                "min": min(humidities) if humidities else None,
                "max": max(humidities) if humidities else None,
                "avg": statistics.mean(humidities) if humidities else None
            },
            "last_seen": self._state.last_seen,
            "status": self._state.status
        }


# =============================================================================
# Register Actor
# =============================================================================

@app.on_event("startup")
async def startup():
    await actor_runtime.register_actor(DeviceActor)
    logger.info("Device actor service started")


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "device-actor"}


@app.get("/dapr/config")
async def dapr_config():
    """DAPR actor configuration."""
    return {
        "entities": ["DeviceActor"],
        "actorIdleTimeout": "1h",
        "actorScanInterval": "30s"
    }


@app.post("/devices/{device_id}/telemetry")
async def receive_telemetry(device_id: str, data: TelemetryData):
    """Receive telemetry and forward to device actor."""
    proxy = ActorProxy.create(
        actor_type="DeviceActor",
        actor_id=device_id,
        actor_interface=DeviceActorInterface
    )
    result = await proxy.ProcessTelemetry(data.model_dump())
    return result


@app.get("/devices/{device_id}/state")
async def get_device_state(device_id: str):
    """Get device state from actor."""
    proxy = ActorProxy.create(
        actor_type="DeviceActor",
        actor_id=device_id,
        actor_interface=DeviceActorInterface
    )
    return await proxy.GetState()


@app.get("/devices/{device_id}/analytics")
async def get_device_analytics(device_id: str):
    """Get device analytics from actor."""
    proxy = ActorProxy.create(
        actor_type="DeviceActor",
        actor_id=device_id,
        actor_interface=DeviceActorInterface
    )
    return await proxy.GetAnalytics()


@app.post("/devices/{device_id}/configure")
async def configure_device(device_id: str, config: DeviceConfig):
    """Update device configuration."""
    proxy = ActorProxy.create(
        actor_type="DeviceActor",
        actor_id=device_id,
        actor_interface=DeviceActorInterface
    )
    return await proxy.Configure(config.model_dump())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8001")))
