"""Binary sensor platform for 3x-ui Monitor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, DEFAULT_NAME, DOMAIN
from .coordinator import ThreeXUICoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up 3x-ui binary sensors."""
    coordinator: ThreeXUICoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = [ThreeXUIXrayBinarySensor(coordinator)]

    known_inbound_ids: set[int] = set()

    for inbound in coordinator.data.inbounds:
        inbound_id = inbound.get("id")
        if inbound_id is not None:
            known_inbound_ids.add(inbound_id)
            entities.append(ThreeXUIInboundBinarySensor(coordinator, inbound_id))

    async_add_entities(entities)

    @callback
    def async_check_new_inbounds() -> None:
        new_entities: list[BinarySensorEntity] = []
        for inbound in coordinator.data.inbounds:
            inbound_id = inbound.get("id")
            if inbound_id is not None and inbound_id not in known_inbound_ids:
                known_inbound_ids.add(inbound_id)
                new_entities.append(
                    ThreeXUIInboundBinarySensor(coordinator, inbound_id)
                )
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(async_check_new_inbounds))


class ThreeXUIBaseBinaryEntity(CoordinatorEntity[ThreeXUICoordinator], BinarySensorEntity):
    """Base binary sensor entity for 3x-ui."""

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


class ThreeXUIXrayBinarySensor(ThreeXUIBaseBinaryEntity):
    """Binary sensor representing Xray-core status."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:shield-check"

    def __init__(self, coordinator: ThreeXUICoordinator) -> None:
        """Initialize Xray core binary sensor."""
        super().__init__(coordinator)
        self._attr_name = "Xray Core Status"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_xray_status"

    @property
    def is_on(self) -> bool:
        """Return true if Xray-core is running."""
        return self.coordinator.data.summary.get("xray_state") == "running"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return Xray details."""
        xray = self.coordinator.data.server_status.get("xray") or {}
        return {
            "version": xray.get("version"),
            "state": xray.get("state"),
            "error_msg": xray.get("errorMsg"),
        }


class ThreeXUIInboundBinarySensor(ThreeXUIBaseBinaryEntity):
    """Binary sensor for an individual inbound's running status."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: ThreeXUICoordinator, inbound_id: int) -> None:
        """Initialize the inbound binary sensor."""
        super().__init__(coordinator)
        self.inbound_id = inbound_id
        self._attr_unique_id = f"{coordinator.entry.entry_id}_inbound_{inbound_id}_status"

    def _get_inbound(self) -> dict[str, Any] | None:
        """Get inbound dict from coordinator data."""
        for item in self.coordinator.data.inbounds:
            if item.get("id") == self.inbound_id:
                return item
        return None

    @property
    def name(self) -> str:
        """Return inbound name based on remark."""
        inbound = self._get_inbound()
        remark = inbound.get("remark") if inbound else None
        return f"Inbound {remark or self.inbound_id} Status"

    @property
    def is_on(self) -> bool:
        """Return true if inbound is enabled and Xray is running."""
        inbound = self._get_inbound()
        if not inbound:
            return False
        is_enabled = inbound.get("enable", False)
        is_xray_running = self.coordinator.data.summary.get("xray_state") == "running"
        return bool(is_enabled and is_xray_running)

    @property
    def icon(self) -> str:
        """Return icon based on status."""
        return "mdi:check-network" if self.is_on else "mdi:close-network"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return metadata for this inbound."""
        inbound = self._get_inbound() or {}
        return {
            "inbound_id": self.inbound_id,
            "port": inbound.get("port"),
            "protocol": inbound.get("protocol"),
            "tag": inbound.get("tag"),
            "listen": inbound.get("listen"),
            "remark": inbound.get("remark"),
            "expiry_time": inbound.get("expiryTime"),
        }
