"""
Climate Platform Device for Wiser Smart

https://github.com/tomtomfx/wiserSmartForHA
thomas.fayoux@gmail.com

"""
import asyncio
import logging

import voluptuous as vol

from homeassistant.components.climate import ClimateDevice
from homeassistant.core import callback

from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    ATTR_CURRENT_TEMPERATURE,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    TEMP_CELSIUS,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.util import ruamel_yaml as yaml

from .const import (
    _LOGGER,
    DOMAIN,
    MANUFACTURER,
    ROOM,
    WISER_SMART_SERVICES,
)

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Wiser climate device"""
    data = hass.data[DOMAIN]

    wiser_rooms = [
        WiserSmartRoom(hass, data, room) for room in data.wiserSmart.getWiserRoomsThermostat()
    ]
    async_add_entities(wiser_rooms, True)


""" Definition of WiserSmartRoom """
class WiserSmartRoom(ClimateDevice):
    def __init__(self, hass, data, room_id):
        """Initialize the sensor."""
        self.data = data
        self.hass = hass
        self.current_temp = None
        self.target_temp = None
        self.room_id = room_id
        self._force_update = False
        self._hvac_modes_list = [HVAC_MODE_HEAT, HVAC_MODE_OFF]
        _LOGGER.info(
            "WiserSmart Room: Initialisation for {}".format(self.room_id)
        )

    async def async_update(self):
        _LOGGER.debug("WiserSmartRoom: Update requested for {}".format(self.name))
        if self._force_update:
            await self.data.async_update(no_throttle=True)
            self._force_update = False
        room = self.data.wiserSmart.getWiserRoomInfo(self.room_id)
        self.current_temp = room.get("currentValue")
        self.target_temp = room.get("targetValue")

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def should_poll(self):
        return False

    @property
    def state(self):
        room = self.data.wiserSmart.getWiserRoomInfo(self.room_id)
        self.current_temp = room.get("currentValue")
        self.target_temp = room.get("targetValue")

        if self.current_temp < self.target_temp:
            state = HVAC_MODE_HEAT
        else:
            state = HVAC_MODE_OFF
        return state

    @property
    def name(self):
        return "WiserSmart - Thermostat - " + self.room_id

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def min_temp(self):
        return self.data.minimum_temp

    @property
    def max_temp(self):
        return self.data.maximum_temp

    @property
    def current_temperature(self):
        temp = self.data.wiserSmart.getWiserRoomInfo(self.room_id).get("currentValue")
        return temp

    @property
    def icon(self):
        # Change icon to show if radiator is heating, not heating or set to off.
        room = self.data.wiserSmart.getWiserRoomInfo(self.room_id)
        self.current_temp = room.get("currentValue")
        self.target_temp = room.get("targetValue")

        if self.current_temp < self.target_temp:
            return "mdi:radiator"
        else:
            return "mdi:radiator-off"
        
    @property
    def unique_id(self):
        return "WiserSmartRoom - {}".format(self.room_id)

    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
            "name": self.name,
            "identifiers": {(DOMAIN, self.unique_id)},
            "manufacturer": MANUFACTURER,
            "model": "Wiser Smart Room",
        }

    @property
    def hvac_mode(self):
        state = self.state()
        return state

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return self._hvac_modes_list

    @property
    def target_temperature(self):
        return self.data.wiserSmart.getWiserRoomInfo(self.room_id).get("targetValue")        

    async def async_set_temperature(self, **kwargs):
        """Set new target temperatures."""
        target_temperature = kwargs.get(ATTR_TEMPERATURE)
        if target_temperature is None:
            _LOGGER.debug(
                "No target temperature set for {}".format(self.name)
            )
            return False

        _LOGGER.debug(
            "Setting temperature for {} to {}".format(self.name, target_temperature)
        )
        self.data.wiserSmart.setWiserRoomTemp(self.room_id, target_temperature)
        self._force_update = True
        await self.async_update_ha_state(True)

        return True

    async def async_added_to_hass(self):
        """Subscribe for update from the Controller"""

        async def async_update_state():
            """Update sensor state."""
            await self.async_update_ha_state(True)

        async_dispatcher_connect(self.hass, "WiserSmartUpdateMessage", async_update_state)
