"""
Input select for Wiser Smart Home Mode

https://github.com/tomtomfx/wiserSmartForHA
thomas.fayoux@gmail.com

"""
import asyncio
import logging

import voluptuous as vol

from homeassistant.components.input_select import InputSelect
from homeassistant.core import callback

from homeassistant.const import (
    ATTR_EDITABLE,
    CONF_ICON,
    CONF_ID,
    CONF_NAME,
    SERVICE_RELOAD,
)
from homeassistant.helpers import collection
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.restore_state import RestoreEntity
import homeassistant.helpers.service
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType, HomeAssistantType, ServiceCallType

from .const import (
    _LOGGER,
    DOMAIN,
    MANUFACTURER,
    WISER_SMART_SERVICES,
    WISER_SMART_HOME_MODES,
)

async def async_setup(hass, config):
    """Set up Wiser Smart mode select device (Always only one)"""
    component = EntityComponent(_LOGGER, DOMAIN, hass)
    data = hass.data[DOMAIN]
    
    wisersmart_mode_select = [WiserSmartModeSelect(hass, data)]

    component.async_register_entity_service(
        SERVICE_SELECT_OPTION, SERVICE_SELECT_OPTION_SCHEMA,
        'async_select_option'
    )

    await component.async_add_entities(wisersmart_mode_select)
    return True

""" Definition of Wiser Smart mode select"""
class WiserSmartModeSelect(InputSelect):
    def __init__(self, hass, data, config):
        """Initialize the sensor."""
        self.data = data
        self.hass = hass
        self.name = "Operation Mode Select"
        self._config = config
        self._current_option = None
        self.editable = True
        self._force_update = False
        _LOGGER.info(
            "WiserSmart Mode Select: Initialisation for {}".format(self.name)
        )

    async def async_update(self):
        _LOGGER.debug("WiserSmart Mode Select: Update requested for {}".format(self.name))
        if self._force_update:
            await self.data.async_update(no_throttle=True)
            self._force_update = False
        self._current_option = self.data.wiserSmart.getWiserHomeMode()
    
    @property
    def should_poll(self):
        """If entity should be polled."""
        return False
    
    @property
    def name(self):
        """Return the name of the select input."""
        return self.name
    
    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return "mdi:form-select"
    
    @property
    def _options(self) -> typing.List[str]:
        """Return a list of selection options."""
        return WISER_SMART_HOME_MODES
    
    @property
    def state(self):
        """Return the state of the component."""
        return self._current_option
    
    @property
    def state_attributes(self):
        """Return the state attributes."""
        return {ATTR_OPTIONS: self._options, ATTR_EDITABLE: self.editable}

    @property
    def unique_id(self) -> typing.Optional[str]:
        """Return unique id for the entity."""
        return "{}-0".format(self.name)
    
    def async_select_option(self, option):
        """Select new option."""
        if option not in self._options:
            _LOGGER.warning(
                "Invalid option: %s (possible options: %s)",
                option,
                ", ".join(self._options),
            )
            return
        self._current_option = option
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Subscribe for update from the Controller"""

        async def async_update_state():
            """Update sensor state."""
            await self.async_update_ha_state(True)

        async_dispatcher_connect(self.hass, "WiserSmartUpdateMessage", async_update_state)
        