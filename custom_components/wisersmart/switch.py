"""
Switch Platform Device for Wiser Smart System

https://github.com/tomtomfx/wiserSmartForHA
thomas.fayoux@gmail.com

"""

import asyncio
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

import homeassistant.components.input_select as input_select

from .const import _LOGGER, DOMAIN, MANUFACTURER, WISER_SMART_SERVICES

ATTR_APPLIANCE_STATE = "appliance_state"
SET_APPLIANCE_MODE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_APPLIANCE_STATE, default=False): vol.Coerce(str),
    }
)

ATTR_HOME_MODE = "mode"
ATTR_COME_BACK_TIME = "come_back_time"
SET_HOME_MODE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_HOME_MODE): vol.Coerce(str),
        vol.Required(ATTR_COME_BACK_TIME, default=0): vol.Coerce(int),
    }
)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the Wiser Smart System Switch entities"""
    data = hass.data[DOMAIN]

    # Add appliances (if any)
    if data.wiserSmart.getWiserAppliances() is not None:
        wiserSmart_appliances = [
            WiserSmartAppliance(data, appliance.get("applianceName"), "WiserSmart - Plug - {}".format(appliance.get("applianceName")))
            for appliance in data.wiserSmart.getWiserAppliances()
        ]
        async_add_entities(wiserSmart_appliances)

    @callback
    def set_appliance_state(service):
        entity_id = service.data[ATTR_ENTITY_ID]
        appliance_mode = service.data[ATTR_APPLIANCE_STATE]
        print("data = {} {}".format(entity_id, appliance_mode))

        for appliance in wiserSmart_appliances:

            if appliance.entity_id == entity_id:
                hass.async_create_task(appliance.set_appliance_mode(appliance_mode))
            appliance.schedule_update_ha_state(True)
            break

    @callback
    def set_home_mode(service):
        home_mode = service.data[ATTR_HOME_MODE]
        come_back_time = service.data[ATTR_COME_BACK_TIME]
        hass.async_create_task(data.set_home_mode(home_mode, come_back_time))

    """ Register Services """
    hass.services.async_register(
        DOMAIN,
        WISER_SMART_SERVICES["SERVICE_SET_APPLIANCE_STATE"],
        set_appliance_state,
        schema=SET_APPLIANCE_MODE_SCHEMA,
    )
    """ Register Service """
    hass.services.async_register(
        DOMAIN,
        WISER_SMART_SERVICES["SERVICE_SET_HOME_MODE"],
        set_home_mode,
        schema=SET_HOME_MODE_SCHEMA,
    )
    return True

class WiserSmartAppliance(SwitchEntity):
    def __init__(self, data, applianceId, name):
        """Initialize the sensor."""
        _LOGGER.info("{} Appliance Init".format(name))
        self.appliance_name = name
        self.appliance_id = applianceId
        self.data = data
        self._is_on = False

    @property
    def unique_id(self):
        return "WiserSmart - {}".format(self.appliance_id)

    @property
    def icon(self):
        return "mdi:power-socket-fr"

    @property
    def device_info(self):
        """Return device specific attributes."""
        model = self.data.wiserSmart.getWiserDeviceInfo(self.appliance_id).get("modelId")

        return {
            "name": self.appliance_name,
            "identifiers": {(DOMAIN, self.unique_id)},
            "manufacturer": MANUFACTURER,
            "model": model,
        }

    @property
    def name(self):
        """Return the name of the appliance """
        return self.appliance_name

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def is_on(self):
        """Return true if device is on."""
        self._is_on = self.data.wiserSmart.getWiserApplianceInfo(self.appliance_id).get("state")
        _LOGGER.debug(
            "Appliance {} is currently {}".format(self.appliance_id, self._is_on)
        )
        return self._is_on

    @property
    def device_state_attributes(self):
        attrs = {}
        device_data = self.data.wiserSmart.getWiserApplianceInfo(self.appliance_id)
        attrs["power_consumption"] = device_data.get("powerConsump")
        return attrs

    async def async_turn_on(self, **kwargs):
        """Turn the device on."""
        await self.data.set_appliance_state(self.appliance_id, True)
        return True

    async def async_turn_off(self, **kwargs):
        """Turn the device off."""
        await self.data.set_appliance_state(self.appliance_id, False)
        return True

    async def async_added_to_hass(self):
        """Subscribe for update from the Controller"""

        async def async_update_state():
            """Update sensor state."""
            await self.async_update_ha_state(False)

        async_dispatcher_connect(self.hass, "WiserSmartUpdateMessage", async_update_state)
