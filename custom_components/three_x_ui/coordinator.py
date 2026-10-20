"""DataUpdateCoordinator for 3x-ui Monitor."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    CONF_URL,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    TIMEOUT_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ThreeXUIData:
    """Structure for 3x-ui aggregated data."""

    server_status: dict[str, Any] = field(default_factory=dict)
    inbounds: list[dict[str, Any]] = field(default_factory=list)
    outbounds: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


class ThreeXUICoordinator(DataUpdateCoordinator[ThreeXUIData]):
    """Class to manage fetching 3x-ui data from the API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.url = entry.data[CONF_URL].rstrip("/")
        self.token = entry.data[CONF_TOKEN]
        self.verify_ssl = entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
        
        # Determine scan interval from options or initial config
        scan_interval_sec = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.title}",
            update_interval=timedelta(seconds=scan_interval_sec),
        )

        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp ClientSession with proper SSL configuration."""
        if self._session is None or self._session.closed:
            self._session = async_create_clientsession(
                self.hass,
                verify_ssl=self.verify_ssl,
            )
        return self._session

    async def _async_update_data(self) -> ThreeXUIData:
        """Fetch all necessary data from the 3x-ui endpoints."""
        session = await self._get_session()
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        try:
            async with asyncio.timeout(TIMEOUT_SECONDS):
                server_status = await self._fetch_server_status(session, headers)
                inbounds = await self._fetch_inbounds(session, headers)
                outbounds = await self._fetch_outbounds_safe(session, headers)
        except aiohttp.ClientResponseError as err:
            if err.status in (401, 403):
                raise ConfigEntryAuthFailed(
                    f"Authentication failed for {self.url}: {err.message}"
                ) from err
            raise UpdateFailed(f"HTTP error communicating with 3x-ui: {err.status} {err.message}") from err
        except (TimeoutError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Timeout communicating with 3x-ui at {self.url}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Network error communicating with 3x-ui: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching 3x-ui data")
            raise UpdateFailed(f"Unexpected error: {err}") from err

        summary = self._calculate_summary(server_status, inbounds)

        return ThreeXUIData(
            server_status=server_status,
            inbounds=inbounds,
            outbounds=outbounds,
            summary=summary,
        )

    async def _fetch_server_status(
        self, session: aiohttp.ClientSession, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Fetch system status from /panel/api/server/status."""
        endpoint = f"{self.url}/panel/api/server/status"
        async with session.get(endpoint, headers=headers) as resp:
            if resp.status in (401, 403):
                raise ConfigEntryAuthFailed("Invalid API Token")
            if resp.status != 200:
                raise UpdateFailed(f"Server status returned HTTP {resp.status}")
            data = await resp.json()
            if not data.get("success"):
                raise UpdateFailed(f"Server status error: {data.get('msg', 'Unknown error')}")
            return data.get("obj") or {}

    async def _fetch_inbounds(
        self, session: aiohttp.ClientSession, headers: dict[str, str]
    ) -> list[dict[str, Any]]:
        """Fetch list of inbounds from /panel/api/inbounds/list."""
        endpoint = f"{self.url}/panel/api/inbounds/list"
        async with session.get(endpoint, headers=headers) as resp:
            if resp.status in (401, 403):
                raise ConfigEntryAuthFailed("Invalid API Token")
            if resp.status != 200:
                raise UpdateFailed(f"Inbounds list returned HTTP {resp.status}")
            data = await resp.json()
            if not data.get("success"):
                raise UpdateFailed(f"Inbounds error: {data.get('msg', 'Unknown error')}")
            return data.get("obj") or []

    async def _fetch_outbounds_safe(
        self, session: aiohttp.ClientSession, headers: dict[str, str]
    ) -> list[dict[str, Any]]:
        """Safely fetch Xray template outbounds from /panel/api/xray/.
        
        Does not fail the coordinator if outbounds endpoint is not accessible.
        """
        endpoint = f"{self.url}/panel/api/xray/"
        try:
            async with session.post(endpoint, headers=headers) as resp:
                if resp.status != 200:
                    _LOGGER.debug("Outbounds endpoint returned HTTP %s, skipping outbounds", resp.status)
                    return []
                data = await resp.json()
                if not data.get("success"):
                    return []
                obj = data.get("obj") or {}
                raw_setting = obj.get("xraySetting")
                if not raw_setting:
                    return []

                # xraySetting can be a JSON string or already parsed dict
                if isinstance(raw_setting, str):
                    parsed_setting = json.loads(raw_setting)
                elif isinstance(raw_setting, dict):
                    parsed_setting = raw_setting
                else:
                    return []

                raw_outbounds = parsed_setting.get("outbounds") or []
                clean_outbounds = []
                for item in raw_outbounds:
                    if isinstance(item, dict):
                        clean_outbounds.append({
                            "tag": item.get("tag", "unnamed"),
                            "protocol": item.get("protocol", "unknown"),
                            "sendThrough": item.get("sendThrough", ""),
                        })
                return clean_outbounds
        except Exception as err:
            _LOGGER.debug("Could not fetch outbounds from 3x-ui: %s", err)
            return []

    def _calculate_summary(
        self, server_status: dict[str, Any], inbounds: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Aggregate summary metrics across inbounds and server status."""
        total_up = 0
        total_down = 0
        total_clients = 0
        active_clients = 0
        active_inbounds = 0

        for inbound in inbounds:
            total_up += inbound.get("up", 0)
            total_down += inbound.get("down", 0)
            if inbound.get("enable"):
                active_inbounds += 1

            client_stats = inbound.get("clientStats") or []
            total_clients += len(client_stats)
            for client in client_stats:
                if client.get("enable", True):
                    active_clients += 1

        xray_info = server_status.get("xray") or {}
        xray_state = xray_info.get("state", "stopped")

        # Memory calculations
        mem = server_status.get("mem") or {}
        mem_current = mem.get("current", 0)
        mem_total = mem.get("total", 0)
        mem_percent = round((mem_current / mem_total * 100), 1) if mem_total > 0 else 0.0

        # Disk calculations
        disk = server_status.get("disk") or {}
        disk_current = disk.get("current", 0)
        disk_total = disk.get("total", 0)
        disk_percent = round((disk_current / disk_total * 100), 1) if disk_total > 0 else 0.0

        return {
            "total_up": total_up,
            "total_down": total_down,
            "total_clients": total_clients,
            "active_clients": active_clients,
            "total_inbounds": len(inbounds),
            "active_inbounds": active_inbounds,
            "xray_state": xray_state,
            "mem_percent": mem_percent,
            "disk_percent": disk_percent,
        }
