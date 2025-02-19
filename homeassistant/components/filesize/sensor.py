"""Sensor for monitoring the size of a file."""
from __future__ import annotations

import datetime
import logging
import os
import pathlib

import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as PARENT_PLATFORM_SCHEMA,
    SensorEntity,
)
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_FILE_PATH, DATA_MEGABYTES
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import CONF_FILE_PATHS, DOMAIN

_LOGGER = logging.getLogger(__name__)

ICON = "mdi:file"

PLATFORM_SCHEMA = PARENT_PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_FILE_PATHS): vol.All(cv.ensure_list, [cv.isfile])}
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the file size sensor."""
    _LOGGER.warning(
        # Filesize config flow added in 2022.4 and should be removed in 2022.6
        "Configuration of the Filesize sensor platform in YAML is deprecated and "
        "will be removed in Home Assistant 2022.6; Your existing configuration "
        "has been imported into the UI automatically and can be safely removed "
        "from your configuration.yaml file"
    )
    for path in config[CONF_FILE_PATHS]:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data={CONF_FILE_PATH: path},
            )
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the platform from config entry."""

    path = entry.data[CONF_FILE_PATH]
    get_path = await hass.async_add_executor_job(pathlib.Path, path)
    fullpath = str(get_path.absolute())

    if get_path.exists() and get_path.is_file():
        async_add_entities([FilesizeEntity(fullpath, entry.entry_id)], True)


class FilesizeEntity(SensorEntity):
    """Encapsulates file size information."""

    _attr_native_unit_of_measurement = DATA_MEGABYTES
    _attr_icon = ICON

    def __init__(self, path: str, entry_id: str) -> None:
        """Initialize the data object."""
        self._path = path  # Need to check its a valid path
        self._attr_name = path.split("/")[-1]
        self._attr_unique_id = entry_id

    def update(self) -> None:
        """Update the sensor."""
        try:
            statinfo = os.stat(self._path)
        except OSError as error:
            _LOGGER.error("Can not retrieve file statistics %s", error)
            self._attr_native_value = None
            return

        size = statinfo.st_size
        last_updated = datetime.datetime.fromtimestamp(statinfo.st_mtime).isoformat()
        self._attr_native_value = round(size / 1e6, 2) if size else None
        self._attr_extra_state_attributes = {
            "path": self._path,
            "last_updated": last_updated,
            "bytes": size,
        }
