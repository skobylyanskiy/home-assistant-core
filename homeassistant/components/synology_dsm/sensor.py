"""Support for Synology DSM sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo
from typing import cast

from synology_dsm.api.core.utilization import SynoCoreUtilization
from synology_dsm.api.dsm.information import SynoDSMInformation
from synology_dsm.api.hyperbackup import SynoHyperBackup
from synology_dsm.api.storage.storage import SynoStorage

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DISKS,
    PERCENTAGE,
    EntityCategory,
    UnitOfDataRate,
    UnitOfInformation,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt as dt_util

from . import SynoApi
from .const import (
    CONF_TASKS,
    CONF_VOLUMES,
    DOMAIN,
    ENTITY_UNIT_LOAD,
    TASK_HEALTH_TO_TRANSLATION,
    TASK_STATUS_TO_TRANSLATION,
)
from .coordinator import SynologyDSMCentralUpdateCoordinator
from .entity import (
    SynologyDSMBackupTaskEntity,
    SynologyDSMBaseEntity,
    SynologyDSMDeviceEntity,
    SynologyDSMEntityDescription,
)
from .models import SynologyDSMData


@dataclass(frozen=True, kw_only=True)
class SynologyDSMSensorEntityDescription(
    SensorEntityDescription, SynologyDSMEntityDescription
):
    """Describes Synology DSM sensor entity."""

    native_value: Callable[[str], StateType] | None = None


UTILISATION_SENSORS: tuple[SynologyDSMSensorEntityDescription, ...] = (
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="cpu_other_load",
        translation_key="cpu_other_load",
        native_unit_of_measurement=PERCENTAGE,
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="cpu_user_load",
        translation_key="cpu_user_load",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="cpu_system_load",
        translation_key="cpu_system_load",
        native_unit_of_measurement=PERCENTAGE,
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="cpu_total_load",
        translation_key="cpu_total_load",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="cpu_1min_load",
        translation_key="cpu_1min_load",
        native_unit_of_measurement=ENTITY_UNIT_LOAD,
        entity_registry_enabled_default=False,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="cpu_5min_load",
        translation_key="cpu_5min_load",
        native_unit_of_measurement=ENTITY_UNIT_LOAD,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="cpu_15min_load",
        translation_key="cpu_15min_load",
        native_unit_of_measurement=ENTITY_UNIT_LOAD,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="memory_real_usage",
        translation_key="memory_real_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="memory_size",
        translation_key="memory_size",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="memory_cached",
        translation_key="memory_cached",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="memory_available_swap",
        translation_key="memory_available_swap",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="memory_available_real",
        translation_key="memory_available_real",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="memory_total_swap",
        translation_key="memory_total_swap",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="memory_total_real",
        translation_key="memory_total_real",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="network_up",
        translation_key="network_up",
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.KILOBYTES_PER_SECOND,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoCoreUtilization.API_KEY,
        key="network_down",
        translation_key="network_down",
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.KILOBYTES_PER_SECOND,
        suggested_display_precision=1,
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)
STORAGE_VOL_SENSORS: tuple[SynologyDSMSensorEntityDescription, ...] = (
    SynologyDSMSensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="volume_status",
        translation_key="volume_status",
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="volume_size_total",
        translation_key="volume_size_total",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.TERABYTES,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.DATA_SIZE,
        entity_registry_enabled_default=False,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="volume_size_used",
        translation_key="volume_size_used",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.TERABYTES,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="volume_percentage_used",
        translation_key="volume_percentage_used",
        native_unit_of_measurement=PERCENTAGE,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="volume_disk_temp_avg",
        translation_key="volume_disk_temp_avg",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="volume_disk_temp_max",
        translation_key="volume_disk_temp_max",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)
STORAGE_DISK_SENSORS: tuple[SynologyDSMSensorEntityDescription, ...] = (
    SynologyDSMSensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="disk_smart_status",
        translation_key="disk_smart_status",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="disk_status",
        translation_key="disk_status",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoStorage.API_KEY,
        key="disk_temp",
        translation_key="disk_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

INFORMATION_SENSORS: tuple[SynologyDSMSensorEntityDescription, ...] = (
    SynologyDSMSensorEntityDescription(
        api_key=SynoDSMInformation.API_KEY,
        key="temperature",
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoDSMInformation.API_KEY,
        key="uptime",
        translation_key="uptime",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

HYPER_BACKUP_SENSORS: tuple[SynologyDSMSensorEntityDescription, ...] = (
    SynologyDSMSensorEntityDescription(
        api_key=SynoHyperBackup.API_KEY,
        key="health",
        translation_key="task_health",
        # options=list(TASK_HEALTH_TO_TRANSLATION.values()),
        options=["error", "good", "warning"],
        device_class=SensorDeviceClass.ENUM,
        native_value=lambda value: TASK_HEALTH_TO_TRANSLATION.get(value, value),
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoHyperBackup.API_KEY,
        key="next_backup_time",
        translation_key="task_next_backup_time",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoHyperBackup.API_KEY,
        key="previous_backup_end_time",
        translation_key="task_previous_backup_end_time",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoHyperBackup.API_KEY,
        key="previous_backup_time",
        translation_key="task_previous_backup_time",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoHyperBackup.API_KEY,
        key="previous_error",
        translation_key="task_previous_error",
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoHyperBackup.API_KEY,
        key="previous_result",
        translation_key="task_previous_result",
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoHyperBackup.API_KEY,
        key="previous_success_time",
        translation_key="task_previous_success_time",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoHyperBackup.API_KEY,
        key="status",
        translation_key="task_status",
        device_class=SensorDeviceClass.ENUM,
        options=list(TASK_STATUS_TO_TRANSLATION.values()),
        native_value=lambda value: TASK_STATUS_TO_TRANSLATION.get(value, value),
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoHyperBackup.API_KEY,
        key="used_size",
        translation_key="task_used_size",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIGABYTES,
        suggested_display_precision=2,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoHyperBackup.API_KEY,
        key="backup_progress",
        translation_key="task_backup_progress",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoHyperBackup.API_KEY,
        key="raw_status",
        translation_key="task_raw_status",
        entity_registry_enabled_default=False,
    ),
    SynologyDSMSensorEntityDescription(
        api_key=SynoHyperBackup.API_KEY,
        key="state",
        translation_key="task_state",
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Synology NAS Sensor."""
    data: SynologyDSMData = hass.data[DOMAIN][entry.unique_id]
    api = data.api
    coordinator = data.coordinator_central
    storage = api.storage
    assert storage is not None

    entities: list[
        SynoDSMUtilSensor
        | SynoDSMStorageSensor
        | SynoDSMInfoSensor
        | SynoDSMHyperBackupSensor
    ] = [
        SynoDSMUtilSensor(api, coordinator, description)
        for description in UTILISATION_SENSORS
    ]

    # Handle all volumes
    if storage.volumes_ids:
        entities.extend(
            [
                SynoDSMStorageSensor(api, coordinator, description, volume)
                for volume in entry.data.get(CONF_VOLUMES, storage.volumes_ids)
                for description in STORAGE_VOL_SENSORS
            ]
        )

    # Handle all disks
    if storage.disks_ids:
        entities.extend(
            [
                SynoDSMStorageSensor(api, coordinator, description, disk)
                for disk in entry.data.get(CONF_DISKS, storage.disks_ids)
                for description in STORAGE_DISK_SENSORS
            ]
        )

    # Handle all hyperBackup tasks
    if api.hyperbackup is not None and api.hyperbackup.task_ids:
        entities.extend(
            [
                SynoDSMHyperBackupSensor(api, coordinator, description, task)
                for task in entry.data.get(CONF_TASKS, api.hyperbackup.task_ids)
                for description in HYPER_BACKUP_SENSORS
            ]
        )

    entities.extend(
        [
            SynoDSMInfoSensor(api, coordinator, description)
            for description in INFORMATION_SENSORS
        ]
    )

    async_add_entities(entities)


class SynoDSMSensor(
    SynologyDSMBaseEntity[SynologyDSMCentralUpdateCoordinator], SensorEntity
):
    """Mixin for sensor specific attributes."""

    entity_description: SynologyDSMSensorEntityDescription

    def __init__(
        self,
        api: SynoApi,
        coordinator: SynologyDSMCentralUpdateCoordinator,
        description: SynologyDSMSensorEntityDescription,
    ) -> None:
        """Initialize the Synology DSM sensor entity."""
        super().__init__(api, coordinator, description)


class SynoDSMUtilSensor(SynoDSMSensor):
    """Representation a Synology Utilisation sensor."""

    @property
    def native_value(self) -> StateType:
        """Return the state."""
        attr = getattr(self._api.utilisation, self.entity_description.key)
        if callable(attr):
            attr = attr()

        # CPU load average
        if (
            isinstance(attr, int)
            and self.native_unit_of_measurement == ENTITY_UNIT_LOAD
        ):
            return round(attr / 100, 2)

        return attr  # type: ignore[no-any-return]

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return bool(self._api.utilisation) and super().available


class SynoDSMStorageSensor(SynologyDSMDeviceEntity, SynoDSMSensor):
    """Representation a Synology Storage sensor."""

    entity_description: SynologyDSMSensorEntityDescription

    def __init__(
        self,
        api: SynoApi,
        coordinator: SynologyDSMCentralUpdateCoordinator,
        description: SynologyDSMSensorEntityDescription,
        device_id: str | None = None,
    ) -> None:
        """Initialize the Synology DSM storage sensor entity."""
        super().__init__(api, coordinator, description, device_id)

    @property
    def native_value(self) -> StateType:
        """Return the state."""
        return cast(
            StateType,
            getattr(self._api.storage, self.entity_description.key)(self._device_id),
        )


class SynoDSMHyperBackupSensor(SynologyDSMBackupTaskEntity, SynoDSMSensor):
    """Representation a Synology HyperBackup sensor."""

    entity_description: SynologyDSMSensorEntityDescription

    def __init__(
        self,
        api: SynoApi,
        coordinator: SynologyDSMCentralUpdateCoordinator,
        description: SynologyDSMSensorEntityDescription,
        device_id: int | None = None,
    ) -> None:
        """Initialize the Synology DSM HyperBackup sensor entity."""
        super().__init__(api, coordinator, description, device_id)

    @property
    def native_value(self) -> StateType | datetime:
        """Return the state."""
        assert self._api.hyperbackup is not None
        assert self._device_id is not None
        attr = getattr(
            self._api.hyperbackup.get_task(self._device_id), self.entity_description.key
        )
        if attr is None:
            return None
        if callable(attr):
            attr = attr()

        if self.entity_description.native_value:
            return self.entity_description.native_value(attr)

        if self.device_class == SensorDeviceClass.TIMESTAMP:
            if isinstance(attr, datetime) and attr.tzinfo is None:
                return attr.replace(tzinfo=self._get_timezone())

        return cast(StateType, attr)

    def _get_timezone(self) -> tzinfo:
        # time_zone_desc is a string like "(GMT-07:00) Arizona"
        if (
            self._api.system
            and (tz_desc := self._api.system.time_zone_desc) is not None
        ):
            # tz_str: -07:00
            tz_str = tz_desc[4:][:6]
            hours, minutes = map(int, tz_str.split(":"))
            offset_delta = timedelta(hours=hours, minutes=minutes)
            return timezone(offset_delta)
        return dt_util.get_default_time_zone()


class SynoDSMInfoSensor(SynoDSMSensor):
    """Representation a Synology information sensor."""

    def __init__(
        self,
        api: SynoApi,
        coordinator: SynologyDSMCentralUpdateCoordinator,
        description: SynologyDSMSensorEntityDescription,
    ) -> None:
        """Initialize the Synology SynoDSMInfoSensor entity."""
        super().__init__(api, coordinator, description)
        self._previous_uptime: str | None = None
        self._last_boot: datetime | None = None

    @property
    def native_value(self) -> StateType | datetime:
        """Return the state."""
        attr = getattr(self._api.information, self.entity_description.key)
        if attr is None:
            return None

        if self.entity_description.key == "uptime":
            # reboot happened or entity creation
            if self._previous_uptime is None or self._previous_uptime > attr:
                self._last_boot = dt_util.utcnow() - timedelta(seconds=attr)

            self._previous_uptime = attr
            return self._last_boot
        return attr  # type: ignore[no-any-return]
