"""Update platform for Supervisor."""
from __future__ import annotations

from typing import Any

from awesomeversion import AwesomeVersion, AwesomeVersionStrategy

from homeassistant.components.update import (
    UpdateEntity,
    UpdateEntityDescription,
    UpdateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ICON, ATTR_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import (
    ADDONS_COORDINATOR,
    async_update_addon,
    async_update_core,
    async_update_os,
    async_update_supervisor,
)
from .const import (
    ATTR_CHANGELOG,
    ATTR_VERSION,
    ATTR_VERSION_LATEST,
    DATA_KEY_ADDONS,
    DATA_KEY_CORE,
    DATA_KEY_OS,
    DATA_KEY_SUPERVISOR,
)
from .entity import (
    HassioAddonEntity,
    HassioCoreEntity,
    HassioOSEntity,
    HassioSupervisorEntity,
)
from .handler import HassioAPIError

ENTITY_DESCRIPTION = UpdateEntityDescription(
    name="Update",
    key=ATTR_VERSION_LATEST,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Supervisor update based on a config entry."""
    coordinator = hass.data[ADDONS_COORDINATOR]

    entities = [
        SupervisorSupervisorUpdateEntity(
            coordinator=coordinator,
            entity_description=ENTITY_DESCRIPTION,
        ),
        SupervisorCoreUpdateEntity(
            coordinator=coordinator,
            entity_description=ENTITY_DESCRIPTION,
        ),
    ]

    for addon in coordinator.data[DATA_KEY_ADDONS].values():
        entities.append(
            SupervisorAddonUpdateEntity(
                addon=addon,
                coordinator=coordinator,
                entity_description=ENTITY_DESCRIPTION,
            )
        )

    if coordinator.is_hass_os:
        entities.append(
            SupervisorOSUpdateEntity(
                coordinator=coordinator,
                entity_description=ENTITY_DESCRIPTION,
            )
        )

    async_add_entities(entities)


class SupervisorAddonUpdateEntity(HassioAddonEntity, UpdateEntity):
    """Update entity to handle updates for the Supervisor add-ons."""

    _attr_supported_features = UpdateEntityFeature.INSTALL | UpdateEntityFeature.BACKUP

    @property
    def title(self) -> str | None:
        """Return the title of the update."""
        return self.coordinator.data[DATA_KEY_ADDONS][self._addon_slug][ATTR_NAME]

    @property
    def latest_version(self) -> str | None:
        """Latest version available for install."""
        return self.coordinator.data[DATA_KEY_ADDONS][self._addon_slug][
            ATTR_VERSION_LATEST
        ]

    @property
    def current_version(self) -> str | None:
        """Version currently in use."""
        return self.coordinator.data[DATA_KEY_ADDONS][self._addon_slug][ATTR_VERSION]

    @property
    def release_summary(self) -> str | None:
        """Release summary for the add-on."""
        return self.coordinator.data[DATA_KEY_ADDONS][self._addon_slug][ATTR_CHANGELOG]

    @property
    def entity_picture(self) -> str | None:
        """Return the icon of the add-on if any."""
        if not self.available:
            return None
        if self.coordinator.data[DATA_KEY_ADDONS][self._addon_slug][ATTR_ICON]:
            return f"/api/hassio/addons/{self._addon_slug}/icon"
        return None

    async def async_install(
        self,
        version: str | None = None,
        backup: bool | None = False,
        **kwargs: Any,
    ) -> None:
        """Install an update."""
        try:
            await async_update_addon(self.hass, slug=self._addon_slug, backup=backup)
        except HassioAPIError as err:
            raise HomeAssistantError(f"Error updating {self.title}: {err}") from err
        else:
            await self.coordinator.force_info_update_supervisor()


class SupervisorOSUpdateEntity(HassioOSEntity, UpdateEntity):
    """Update entity to handle updates for the Home Assistant Operating System."""

    _attr_supported_features = (
        UpdateEntityFeature.INSTALL | UpdateEntityFeature.SPECIFIC_VERSION
    )
    _attr_title = "Home Assistant Operating System"

    @property
    def latest_version(self) -> str:
        """Return native value of entity."""
        return self.coordinator.data[DATA_KEY_OS][ATTR_VERSION_LATEST]

    @property
    def current_version(self) -> str:
        """Return native value of entity."""
        return self.coordinator.data[DATA_KEY_OS][ATTR_VERSION]

    @property
    def entity_picture(self) -> str | None:
        """Return the iconof the entity."""
        return "https://brands.home-assistant.io/homeassistant/icon.png"

    @property
    def release_url(self) -> str | None:
        """URL to the full release notes of the latest version available."""
        version = AwesomeVersion(self.latest_version)
        if version.dev or version.strategy == AwesomeVersionStrategy.UNKNOWN:
            return "https://github.com/home-assistant/operating-system/commits/dev"
        return (
            f"https://github.com/home-assistant/operating-system/releases/tag/{version}"
        )

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Install an update."""
        try:
            await async_update_os(self.hass, version)
        except HassioAPIError as err:
            raise HomeAssistantError(
                f"Error updating Home Assistant Operating System: {err}"
            ) from err


class SupervisorSupervisorUpdateEntity(HassioSupervisorEntity, UpdateEntity):
    """Update entity to handle updates for the Home Assistant Supervisor."""

    _attr_supported_features = UpdateEntityFeature.INSTALL
    _attr_title = "Home Assistant Supervisor"

    @property
    def latest_version(self) -> str:
        """Return native value of entity."""
        return self.coordinator.data[DATA_KEY_SUPERVISOR][ATTR_VERSION_LATEST]

    @property
    def current_version(self) -> str:
        """Return native value of entity."""
        return self.coordinator.data[DATA_KEY_SUPERVISOR][ATTR_VERSION]

    @property
    def release_url(self) -> str | None:
        """URL to the full release notes of the latest version available."""
        version = AwesomeVersion(self.latest_version)
        if version.dev or version.strategy == AwesomeVersionStrategy.UNKNOWN:
            return "https://github.com/home-assistant/supervisor/commits/main"
        return f"https://github.com/home-assistant/supervisor/releases/tag/{version}"

    @property
    def entity_picture(self) -> str | None:
        """Return the iconof the entity."""
        return "https://brands.home-assistant.io/hassio/icon.png"

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Install an update."""
        try:
            await async_update_supervisor(self.hass)
        except HassioAPIError as err:
            raise HomeAssistantError(
                f"Error updating Home Assistant Supervisor: {err}"
            ) from err


class SupervisorCoreUpdateEntity(HassioCoreEntity, UpdateEntity):
    """Update entity to handle updates for Home Assistant Core."""

    _attr_supported_features = (
        UpdateEntityFeature.INSTALL
        | UpdateEntityFeature.SPECIFIC_VERSION
        | UpdateEntityFeature.BACKUP
    )
    _attr_title = "Home Assistant Core"

    @property
    def latest_version(self) -> str:
        """Return native value of entity."""
        return self.coordinator.data[DATA_KEY_CORE][ATTR_VERSION_LATEST]

    @property
    def current_version(self) -> str:
        """Return native value of entity."""
        return self.coordinator.data[DATA_KEY_CORE][ATTR_VERSION]

    @property
    def entity_picture(self) -> str | None:
        """Return the iconof the entity."""
        return "https://brands.home-assistant.io/homeassistant/icon.png"

    @property
    def release_url(self) -> str | None:
        """URL to the full release notes of the latest version available."""
        version = AwesomeVersion(self.latest_version)
        if version.dev:
            return "https://github.com/home-assistant/core/commits/dev"
        return f"https://{'rc' if version.beta else 'www'}.home-assistant.io/latest-release-notes/"

    async def async_install(
        self, version: str | None, backup: bool, **kwargs: Any
    ) -> None:
        """Install an update."""
        try:
            await async_update_core(self.hass, version=version, backup=backup)
        except HassioAPIError as err:
            raise HomeAssistantError(
                f"Error updating Home Assistant Core {err}"
            ) from err
