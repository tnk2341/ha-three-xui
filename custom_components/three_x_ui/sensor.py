"""Sensor platform for 3x-ui Monitor."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

try:
    from homeassistant.const import UnitOfInformation
    UNIT_BYTES = UnitOfInformation.BYTES
except ImportError:
    UNIT_BYTES = "B"

try:
    from homeassistant.const import UnitOfTime
    UNIT_SECONDS = UnitOfTime.SECONDS
except ImportError:
    UNIT_SECONDS = "s"

PERCENTAGE = "%"

from .const import CONF_NAME, DEFAULT_NAME, DOMAIN
from .coordinator import ThreeXUICoordinator, ThreeXUIData

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ThreeXUISensorDescription(SensorEntityDescription):
    """Class describing 3x-ui sensor entities."""

    value_fn: Callable[[ThreeXUIData], Any]
    extra_fn: Callable[[ThreeXUIData], dict[str, Any]] | None = None


SERVER_SENSORS: tuple[ThreeXUISensorDescription, ...] = (
    ThreeXUISensorDescription(
        key="cpu_usage",
        name="CPU Usage",
        icon="mdi:cpu-64-bit",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.server_status.get("cpu"),
    ),
    ThreeXUISensorDescription(
        key="mem_percent",
        name="Memory Usage",
        icon="mdi:memory",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.summary.get("mem_percent"),
    ),
    ThreeXUISensorDescription(
        key="mem_used",
        name="Memory Used",
        icon="mdi:memory",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UNIT_BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: (data.server_status.get("mem") or {}).get("current"),
    ),
    ThreeXUISensorDescription(
        key="mem_total",
        name="Memory Total",
        icon="mdi:memory",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UNIT_BYTES,
        suggested_display_precision=1,
        value_fn=lambda data: (data.server_status.get("mem") or {}).get("total"),
    ),
    ThreeXUISensorDescription(
        key="disk_percent",
        name="Disk Usage",
        icon="mdi:harddisk",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.summary.get("disk_percent"),
    ),
    ThreeXUISensorDescription(
        key="disk_used",
        name="Disk Used",
        icon="mdi:harddisk",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UNIT_BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: (data.server_status.get("disk") or {}).get("current"),
    ),
    ThreeXUISensorDescription(
        key="disk_total",
        name="Disk Total",
        icon="mdi:harddisk",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UNIT_BYTES,
        suggested_display_precision=1,
        value_fn=lambda data: (data.server_status.get("disk") or {}).get("total"),
    ),
    ThreeXUISensorDescription(
        key="uptime",
        name="Server Uptime",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UNIT_SECONDS,
        value_fn=lambda data: data.server_status.get("uptime"),
    ),
    ThreeXUISensorDescription(
        key="tcp_count",
        name="TCP Connections",
        icon="mdi:lan-connect",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.server_status.get("tcpCount"),
    ),
    ThreeXUISensorDescription(
        key="udp_count",
        name="UDP Connections",
        icon="mdi:lan-pending",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.server_status.get("udpCount"),
    ),
    ThreeXUISensorDescription(
        key="total_upload",
        name="Total Upload",
        icon="mdi:upload-network",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UNIT_BYTES,
        value_fn=lambda data: data.summary.get("total_up", 0),
    ),
    ThreeXUISensorDescription(
        key="total_download",
        name="Total Download",
        icon="mdi:download-network",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UNIT_BYTES,
        value_fn=lambda data: data.summary.get("total_down", 0),
    ),
    ThreeXUISensorDescription(
        key="total_clients",
        name="Total Clients",
        icon="mdi:account-group",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.summary.get("total_clients", 0),
        extra_fn=lambda data: {"active_clients": data.summary.get("active_clients", 0)},
    ),
    ThreeXUISensorDescription(
        key="active_inbounds",
        name="Active Inbounds",
        icon="mdi:network",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.summary.get("active_inbounds", 0),
        extra_fn=lambda data: {"total_inbounds": data.summary.get("total_inbounds", 0)},
    ),
    ThreeXUISensorDescription(
        key="outbounds_list",
        name="Outbounds Configured",
        icon="mdi:routes",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: len(data.outbounds),
        extra_fn=lambda data: {"outbounds": data.outbounds},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up 3x-ui sensor platform."""
    coordinator: ThreeXUICoordinator = hass.data[DOMAIN][entry.entry_id]

    # Add core server metrics
    entities: list[SensorEntity] = [
        ThreeXUIServerSensor(coordinator, description)
        for description in SERVER_SENSORS
    ]

    # Track discovered inbound IDs to dynamically register new inbounds
    known_inbound_ids: set[int] = set()

    def create_inbound_sensors(inbound_id: int) -> list[SensorEntity]:
        return [
            ThreeXUIInboundClientsSensor(coordinator, inbound_id),
            ThreeXUIInboundTrafficSensor(coordinator, inbound_id, is_upload=True),
            ThreeXUIInboundTrafficSensor(coordinator, inbound_id, is_upload=False),
        ]

    for inbound in coordinator.data.inbounds:
        inbound_id = inbound.get("id")
        if inbound_id is not None:
            known_inbound_ids.add(inbound_id)
            entities.extend(create_inbound_sensors(inbound_id))

    async_add_entities(entities)

    # Listen for coordinator updates to discover newly created inbounds
    @callback
    def async_check_new_inbounds() -> None:
        new_entities: list[SensorEntity] = []
        for inbound in coordinator.data.inbounds:
            inbound_id = inbound.get("id")
            if inbound_id is not None and inbound_id not in known_inbound_ids:
                known_inbound_ids.add(inbound_id)
                new_entities.extend(create_inbound_sensors(inbound_id))
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(async_check_new_inbounds))


class ThreeXUIBaseEntity(CoordinatorEntity[ThreeXUICoordinator]):
    """Base entity for 3x-ui."""

    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        xray = self.coordinator.data.server_status.get("xray") or {}
        sw_version = xray.get("version", "Unknown")
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=self.coordinator.entry.data.get(CONF_NAME, DEFAULT_NAME),
            manufacturer="MHSanaei",
            model="3x-ui Panel",
            sw_version=sw_version,
            configuration_url=self.coordinator.url,
        )


class ThreeXUIServerSensor(ThreeXUIBaseEntity, SensorEntity):
    """Representation of a 3x-ui Server Sensor."""

    entity_description: ThreeXUISensorDescription

    def __init__(
        self,
        coordinator: ThreeXUICoordinator,
        description: ThreeXUISensorDescription,
    ) -> None:
        """Initialize the server sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return native value of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes if configured."""
        if self.entity_description.extra_fn:
            return self.entity_description.extra_fn(self.coordinator.data)
        return None


class ThreeXUIInboundClientsSensor(ThreeXUIBaseEntity, SensorEntity):
    """Sensor for individual inbound clients count."""

    _attr_icon = "mdi:account-multiple"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ThreeXUICoordinator, inbound_id: int) -> None:
        """Initialize the clients sensor for an inbound."""
        super().__init__(coordinator)
        self.inbound_id = inbound_id
        self._attr_unique_id = f"{coordinator.entry.entry_id}_inbound_{inbound_id}_clients"

    def _get_inbound(self) -> dict[str, Any] | None:
        """Get inbound dictionary from coordinator data."""
        for item in self.coordinator.data.inbounds:
            if item.get("id") == self.inbound_id:
                return item
        return None

    @property
    def name(self) -> str:
        """Return dynamic entity name based on inbound remark."""
        inbound = self._get_inbound()
        remark = inbound.get("remark") if inbound else None
        return f"Inbound {remark or self.inbound_id} Clients"

    @property
    def native_value(self) -> int:
        """Return total clients count on this inbound."""
        inbound = self._get_inbound()
        if not inbound:
            return 0
        stats = inbound.get("clientStats") or []
        return len(stats)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes like active clients and client emails."""
        inbound = self._get_inbound() or {}
        stats = inbound.get("clientStats") or []
        active = sum(1 for c in stats if c.get("enable", True))
        emails = [c.get("email") for c in stats if c.get("email")]
        return {
            "inbound_id": self.inbound_id,
            "protocol": inbound.get("protocol"),
            "port": inbound.get("port"),
            "active_clients": active,
            "clients": emails,
        }


class ThreeXUIInboundTrafficSensor(ThreeXUIBaseEntity, SensorEntity):
    """Sensor for individual inbound traffic (Upload or Download)."""

    _attr_device_class = SensorDeviceClass.DATA_SIZE
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UNIT_BYTES

    def __init__(
        self, coordinator: ThreeXUICoordinator, inbound_id: int, is_upload: bool
    ) -> None:
        """Initialize the inbound traffic sensor."""
        super().__init__(coordinator)
        self.inbound_id = inbound_id
        self.is_upload = is_upload
        direction = "upload" if is_upload else "download"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_inbound_{inbound_id}_{direction}"
        self._attr_icon = "mdi:arrow-up-bold-box-outline" if is_upload else "mdi:arrow-down-bold-box-outline"

    def _get_inbound(self) -> dict[str, Any] | None:
        """Get inbound dictionary from coordinator data."""
        for item in self.coordinator.data.inbounds:
            if item.get("id") == self.inbound_id:
                return item
        return None

    @property
    def name(self) -> str:
        """Return entity name based on inbound remark and traffic direction."""
        inbound = self._get_inbound()
        remark = inbound.get("remark") if inbound else None
        dir_name = "Upload" if self.is_upload else "Download"
        return f"Inbound {remark or self.inbound_id} {dir_name}"

    @property
    def native_value(self) -> int:
        """Return traffic value in bytes."""
        inbound = self._get_inbound()
        if not inbound:
            return 0
        key = "up" if self.is_upload else "down"
        return inbound.get(key, 0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return metadata for this inbound."""
        inbound = self._get_inbound() or {}
        return {
            "inbound_id": self.inbound_id,
            "protocol": inbound.get("protocol"),
            "port": inbound.get("port"),
            "tag": inbound.get("tag"),
        }
