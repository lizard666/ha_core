"""EHEIM Digital lights."""

from typing import Any

from eheimdigital.classic_led_ctrl import EheimDigitalClassicLEDControl
from eheimdigital.device import EheimDigitalDevice
from eheimdigital.types import LightMode

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    EFFECT_OFF,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.color import brightness_to_value, value_to_brightness

from .const import EFFECT_DAYCL_MODE, EFFECT_TO_LIGHT_MODE
from .coordinator import EheimDigitalConfigEntry, EheimDigitalUpdateCoordinator
from .entity import EheimDigitalEntity, exception_handler

BRIGHTNESS_SCALE = (1, 100)

# Coordinator is used to centralize the data updates
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EheimDigitalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the callbacks for the coordinator so lights can be added as devices are found."""
    coordinator = entry.runtime_data

    def async_setup_device_entities(
        device_address: dict[str, EheimDigitalDevice],
    ) -> None:
        """Set up the light entities for one or multiple devices."""
        entities: list[EheimDigitalClassicLEDControlLight] = []
        for device in device_address.values():
            if isinstance(device, EheimDigitalClassicLEDControl):
                for channel in range(2):
                    if len(device.tankconfig[channel]) > 0:
                        entities.append(
                            EheimDigitalClassicLEDControlLight(
                                coordinator, device, channel
                            )
                        )
                        coordinator.known_devices.add(device.mac_address)

        async_add_entities(entities)

    coordinator.add_platform_callback(async_setup_device_entities)
    async_setup_device_entities(coordinator.hub.devices)


class EheimDigitalClassicLEDControlLight(
    EheimDigitalEntity[EheimDigitalClassicLEDControl], LightEntity
):
    """Represent a EHEIM Digital classicLEDcontrol light."""

    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_effect_list = [EFFECT_DAYCL_MODE]
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_translation_key = "channel"

    def __init__(
        self,
        coordinator: EheimDigitalUpdateCoordinator,
        device: EheimDigitalClassicLEDControl,
        channel: int,
    ) -> None:
        """Initialize an EHEIM Digital classicLEDcontrol light entity."""
        super().__init__(coordinator, device)
        self._channel = channel
        self._attr_translation_placeholders = {"channel_id": str(channel)}
        self._attr_unique_id = f"{self._device_address}_{channel}"
        self._async_update_attrs()

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return super().available and self._device.light_level[self._channel] is not None

    @exception_handler
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        if ATTR_EFFECT in kwargs:
            await self._device.set_light_mode(EFFECT_TO_LIGHT_MODE[kwargs[ATTR_EFFECT]])
            return
        if ATTR_BRIGHTNESS in kwargs:
            await self._device.turn_on(
                int(brightness_to_value(BRIGHTNESS_SCALE, kwargs[ATTR_BRIGHTNESS])),
                self._channel,
            )

    @exception_handler
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self._device.turn_off(self._channel)

    def _async_update_attrs(self) -> None:
        light_level = self._device.light_level[self._channel]

        self._attr_is_on = light_level > 0 if light_level is not None else None
        self._attr_brightness = (
            value_to_brightness(BRIGHTNESS_SCALE, light_level)
            if light_level is not None
            else None
        )
        self._attr_effect = (
            EFFECT_DAYCL_MODE
            if self._device.light_mode == LightMode.DAYCL_MODE
            else EFFECT_OFF
        )
