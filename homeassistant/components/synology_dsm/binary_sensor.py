"""Support for Synology DSM binary sensors."""

from __future__ import annotations

from dataclasses import dataclass

from synology_dsm.api.core.security import SynoCoreSecurity
from synology_dsm.api.hyperbackup import SynoHyperBackup
from synology_dsm.api.storage.storage import SynoStorage

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DISKS, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SynoApi
from .const import CONF_TASKS, DOMAIN
from .coordinator import SynologyDSMCentralUpdateCoordinator
from .entity import (
    SynologyDSMBackupTaskEntity,
    SynologyDSMBaseEntity,
    SynologyDSMDeviceEntity,
    SynologyDSMEntityDescription,
)
from .models import SynologyDSMData


@dataclass(frozen=True, kw_only=True)
class SynologyDSMBinarySensorEntityDescription(
    BinarySensorEntityDescription, SynologyDSMEntityDescription
):
    """Describes Synology DSM binary sensor entity."""


SECURITY_BINARY_SENSORS: tuple[SynologyDSMBinarySensorEntityDescription, ...] = (
    SynologyDSMBinarySensorEntityDescription(
        api_key=SynoCoreSecurity.API_KEY,
        key="status",
        translation_key="status",
        device_class=BinarySensorDeviceClass.SAFETY,
    ),
)

STORAGE_DISK_BINARY_SENSORS: tuple[SynologyDSMBinarySensorEntityDescription, ...] = (
    SynologyDSMBinarySensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="disk_exceed_bad_sector_thr",
        translation_key="disk_exceed_bad_sector_thr",
        device_class=BinarySensorDeviceClass.SAFETY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SynologyDSMBinarySensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="disk_below_remain_life_thr",
        translation_key="disk_below_remain_life_thr",
        device_class=BinarySensorDeviceClass.SAFETY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

HYPER_BACKUP_BINARY_SENSORS: tuple[SynologyDSMBinarySensorEntityDescription, ...] = (
    SynologyDSMBinarySensorEntityDescription(
        api_key=SynoHyperBackup.API_KEY,
        key="has_schedule",
        translation_key="task_has_schedule",
    ),
    SynologyDSMBinarySensorEntityDescription(
        api_key=SynoHyperBackup.API_KEY,
        key="is_backing_up",
        translation_key="task_is_backing_up",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    SynologyDSMBinarySensorEntityDescription(
        api_key=SynoHyperBackup.API_KEY,
        key="target_online",
        translation_key="task_target_online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Synology NAS binary sensor."""
    data: SynologyDSMData = hass.data[DOMAIN][entry.unique_id]
    api = data.api
    coordinator = data.coordinator_central
    assert api.storage is not None

    entities: list[
        SynoDSMHyperBackupBinarySensor
        | SynoDSMSecurityBinarySensor
        | SynoDSMStorageBinarySensor
    ] = [
        SynoDSMSecurityBinarySensor(api, coordinator, description)
        for description in SECURITY_BINARY_SENSORS
    ]

    # Handle all disks
    if api.storage.disks_ids:
        entities.extend(
            [
                SynoDSMStorageBinarySensor(api, coordinator, description, disk)
                for disk in entry.data.get(CONF_DISKS, api.storage.disks_ids)
                for description in STORAGE_DISK_BINARY_SENSORS
            ]
        )

    # Handle all HyperBackup tasks
    if api.hyperbackup is not None and api.hyperbackup.task_ids:
        entities.extend(
            [
                SynoDSMHyperBackupBinarySensor(api, coordinator, description, task)
                for task in entry.data.get(CONF_TASKS, api.hyperbackup.task_ids)
                for description in HYPER_BACKUP_BINARY_SENSORS
            ]
        )

    async_add_entities(entities)


class SynoDSMBinarySensor(
    SynologyDSMBaseEntity[SynologyDSMCentralUpdateCoordinator], BinarySensorEntity
):
    """Mixin for binary sensor specific attributes."""

    entity_description: SynologyDSMBinarySensorEntityDescription

    def __init__(
        self,
        api: SynoApi,
        coordinator: SynologyDSMCentralUpdateCoordinator,
        description: SynologyDSMBinarySensorEntityDescription,
    ) -> None:
        """Initialize the Synology DSM binary_sensor entity."""
        super().__init__(api, coordinator, description)


class SynoDSMSecurityBinarySensor(SynoDSMBinarySensor):
    """Representation a Synology Security binary sensor."""

    @property
    def is_on(self) -> bool:
        """Return the state."""
        return getattr(self._api.security, self.entity_description.key) != "safe"  # type: ignore[no-any-return]

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return bool(self._api.security) and super().available

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return security checks details."""
        assert self._api.security is not None
        return self._api.security.status_by_check


class SynoDSMStorageBinarySensor(SynologyDSMDeviceEntity, SynoDSMBinarySensor):
    """Representation a Synology Storage binary sensor."""

    entity_description: SynologyDSMBinarySensorEntityDescription

    def __init__(
        self,
        api: SynoApi,
        coordinator: SynologyDSMCentralUpdateCoordinator,
        description: SynologyDSMBinarySensorEntityDescription,
        device_id: str | None = None,
    ) -> None:
        """Initialize the Synology DSM storage binary_sensor entity."""
        super().__init__(api, coordinator, description, device_id)

    @property
    def is_on(self) -> bool:
        """Return the state."""
        return bool(
            getattr(self._api.storage, self.entity_description.key)(self._device_id)
        )


class SynoDSMHyperBackupBinarySensor(SynologyDSMBackupTaskEntity, SynoDSMBinarySensor):
    """Representation a Synology HuperBackup binary sensor."""

    entity_description: SynologyDSMBinarySensorEntityDescription

    def __init__(
        self,
        api: SynoApi,
        coordinator: SynologyDSMCentralUpdateCoordinator,
        description: SynologyDSMBinarySensorEntityDescription,
        device_id: int | None = None,
    ) -> None:
        """Initialize the Synology DSM HyperBackup binary_sensor entity."""
        super().__init__(api, coordinator, description, device_id)

    @property
    def is_on(self) -> bool:
        """Return the state."""
        assert self._api.hyperbackup is not None
        assert self._device_id is not None
        return bool(
            getattr(
                self._api.hyperbackup.get_task(self._device_id),
                self.entity_description.key,
            )
        )
