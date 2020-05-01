"""
Sensor Platform Device for Wiser Smart System


https://github.com/tomtomfx/wiserSmartForHA
thomas.fayoux@gmail.com

"""
import asyncio
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_BATTERY_LEVEL,
    CONF_ENTITY_NAMESPACE,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_POWER,
    STATE_UNKNOWN,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.icon import icon_for_battery_level

from .const import (
    _LOGGER,
    DOMAIN,
    MANUFACTURER,
    DEVICE_STATUS_ICONS,
    WISER_SMART_HOME_MODE_ICONS,
    THERMOSTAT_MIN_BATTERY_LEVEL,
    THERMOSTAT_FULL_BATTERY_LEVEL,
)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup the sensor platform."""
    data = hass.data[DOMAIN]  # Get Handler
    wiserSmart_devices = []

    # Add device sensors, only if there are some
    if data.wiserSmart.getWiserDevices() is not None:
        for device in data.wiserSmart.getWiserDevices():
            wiserSmart_devices.append(
                WiserSmartDeviceSensor(data, device.get("name"), device.get("modelId"))
            )

            # Add battery sensors
            if device.get("powerType") == "Battery":
                wiserSmart_devices.append(
                    WiserSmartBatterySensor(data, device.get("name"), sensor_type="Battery")
                )
            
            # Add power sensors
            if device.get("modelId") == "EH-ZB-SPD":
                wiserSmart_devices.append(
                    WiserSmartPowerSensor(data, device.get("name"), sensor_type="Power")
                )
            
    # Add cloud status sensor
    wiserSmart_devices.append(WiserSystemCloudSensor(data, sensor_type="Cloud Sensor"))

    # Add operation sensor
    wiserSmart_devices.append(
        WiserSystemOperationModeSensor(data, sensor_type="Operation Mode")
    )

    async_add_entities(wiserSmart_devices, True)

class WiserSmartSensor(Entity):
    """Definition of a Wiser sensor"""

    def __init__(self, config_entry, device_id=0, sensor_type=""):
        """Initialize the sensor."""
        self.data = config_entry
        self._deviceId = device_id
        self._sensor_type = sensor_type
        self._state = None

    async def async_update(self):
        _LOGGER.debug("{} device update requested".format(self._device_name))
        # await self.data.async_update()

    @property
    def name(self):
        """Return the name of the sensor"""
        return self._device_name

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def state(self):
        """Return the state of the sensor."""
        _LOGGER.debug("{} device state requested".format(self.name))
        return self._state

    @property
    def unique_id(self):
        return "{}-{}".format(self._sensor_type, self._deviceId)

    async def async_added_to_hass(self):
        """Subscribe for update from the Controller"""

        async def async_update_state():
            """Update sensor state."""
            await self.async_update_ha_state(True)

        async_dispatcher_connect(self.hass, "WiserSmartUpdateMessage", async_update_state)


class WiserSmartBatterySensor(WiserSmartSensor):
    """Definition of a battery sensor for Wiser Smart"""

    def __init__(self, data, device_id=0, sensor_type=""):
        super().__init__(data, device_id, sensor_type)
        self._device_name = self.get_device_name()
        # Set default state to unknown to show this value if battery info
        # cannot be read.
        self._state = "Unknown"
        _LOGGER.info("{} device init".format(self._device_name))

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()

        device = self.data.wiserSmart.getWiserDeviceInfo(self._deviceId)

        # Set battery info
        self._state = device.get("batteryLevel") * 10

    @property
    def device_class(self):
        """Return the class of the sensor."""
        return DEVICE_CLASS_BATTERY

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity."""
        return "%"

    @property
    def device_state_attributes(self):
        """Return the state attributes of the battery."""
        attrs = {}

        attrs[ATTR_BATTERY_LEVEL] = (
            self.data.wiserSmart.getWiserDeviceInfo(self._deviceId).get("batteryLevel") * 10 or None
        )
        return attrs

    def get_device_name(self):
        """Return the name of the Device"""
        # Multiple ones get automagically number _n by HA
        return (
            "WiserSmart - "
            + self._deviceId
            + " - Battery Level"
        )

    @property
    def device_info(self):
        """Return device specific attributes."""
        model = self.data.wiserSmart.getWiserDeviceInfo(self._deviceId).get("modelId")
        identifier = "WiserSmart - {}".format(self._deviceId)
        if model == "EH-ZB-RTS":
            identifier = "WiserSmartRoom - {}".format(self.data.wiserSmart.getWiserDeviceInfo(self._deviceId).get("location"))
            model = "Wiser Smart Room"

        return {
            "identifiers": {(DOMAIN, identifier)},
            "manufacturer": MANUFACTURER,
            "model": model,
        }

class WiserSmartPowerSensor(WiserSmartSensor):
    """Definition of a power sensor for Wiser Smart"""

    def __init__(self, data, device_id=0, sensor_type=""):
        super().__init__(data, device_id, sensor_type)
        self._device_name = self.get_device_name()
        # Set default state to unknown to show this value if battery info
        # cannot be read.
        self._state = "Unknown"
        _LOGGER.info("{} device init".format(self._device_name))

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        appliance = self.data.wiserSmart.getWiserApplianceInfo(self._deviceId)
        # Set power info
        self._state = appliance.get("powerConsump")

    @property
    def device_class(self):
        """Return the class of the sensor."""
        return DEVICE_CLASS_POWER

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity."""
        return "W"

    @property
    def device_state_attributes(self):
        """Return the state attributes of the battery."""
        attrs = {}
        attrs["power"] = (
            self.data.wiserSmart.getWiserApplianceInfo(self._deviceId).get("powerConsump") or None
        )
        return attrs

    def get_device_name(self):
        """Return the name of the Device"""
        # Multiple ones get automagically number _n by HA
        return (
            "WiserSmart - "
            + self._deviceId
            + " - Power"
        )

    @property
    def device_info(self):
        """Return device specific attributes."""
        model = self.data.wiserSmart.getWiserDeviceInfo(self._deviceId).get("modelId")
        identifier = "WiserSmart - {}".format(self._deviceId)
        return {
            "identifiers": {(DOMAIN, identifier)},
            "manufacturer": MANUFACTURER,
            "model": model,
        }

class WiserSmartDeviceSensor(WiserSmartSensor):
    """Definition of Wiser Smart Device Sensor"""

    def __init__(self, data, device_id=0, sensor_type=""):
        super().__init__(data, device_id, sensor_type)
        self._device_name = self.get_device_name()
        self._battery_level = None
        self._battery_percent = 0
        self._power_consump = None
        _LOGGER.info("{} device init".format(self._device_name))

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state = self.data.wiserSmart.getWiserDeviceInfo(self._deviceId).get(
            "status"
        )

    @property
    def device_info(self):
        """Return device specific attributes."""
        model = self.data.wiserSmart.getWiserDeviceInfo(self._deviceId).get("modelId")
        identifier = "WiserSmart - {}".format(self._deviceId)

        # Thermostats and heaters
        if (self.data.wiserSmart.getWiserDeviceInfo(self._deviceId).get("modelId") in ["EH-ZB-RTS", "EH-ZB-HACT"]):
            identifier = "WiserSmartRoom - {}".format(self.data.wiserSmart.getWiserDeviceInfo(self._deviceId).get("location"))
            model = "Wiser Smart Room"

        if (identifier != None):
            return {
                "identifiers": {(DOMAIN, identifier)},
                "manufacturer": MANUFACTURER,
                "model": model,
            }
        return None

    def get_device_name(self):
        """Return the name of the Device"""
        # Multiple ones get automagically number _n by HA
        return (
            "WiserSmart - "
            + self._deviceId
        )

    @property
    def icon(self):
        """Return icon for connection status"""
        try:
            return DEVICE_STATUS_ICONS[
                self.data.wiserSmart.getWiserDeviceInfo(self._deviceId).get("status")
            ]
        except KeyError:
            # Handle anything else as no signal
            return DEVICE_STATUS_ICONS["OFFLINE"]

    @property
    def device_state_attributes(self):
        _LOGGER.debug(
            "State attributes for {} {}".format(self._deviceId, self._sensor_type)
        )
        attrs = {}
        device_data = self.data.wiserSmart.getWiserDeviceInfo(self._deviceId)

        """ Generic attributes """
        attrs["vendor"] = "Schneider Electric"
        attrs["model_identifier"] = device_data.get("modelId")

        if self._sensor_type in ["EH-ZB-RTS"]:
            attrs["battery_level"] = device_data.get("batteryLevel") * 10
            
        elif self._sensor_type in ["EH-ZB-SPD", "EH-ZB-LMACT"]:
            appliance = self.data.wiserSmart.getWiserApplianceInfo(self._deviceId)
            attrs["power_consumption"] = appliance.get("powerConsump")
        
        return attrs

class WiserSystemCloudSensor(WiserSmartSensor):
    """Sensor to display the status of the Wiser Cloud"""

    def __init__(self, data, device_id=0, sensor_type=""):
        super().__init__(data, device_id, sensor_type)
        self._device_name = self.get_device_name()
        _LOGGER.info("{} device init".format(self._device_name))

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state = self.data.wiserSmart.getWiserControllerCloudConnection()

    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
            "identifiers": {(DOMAIN, self.data.unique_id)},
        }

    def get_device_name(self):
        """Return the name of the Device """
        return "Wiser Smart Cloud Status"

    @property
    def icon(self):
        if self._state == "up":
            return "mdi:cloud-check"
        else:
            return "mdi:cloud-alert"


class WiserSystemOperationModeSensor(WiserSmartSensor):
    """Sensor for the Wiser Smart Home Mode (manual, schedule, holiday, energysaver)"""

    def __init__(self, data, device_id=0, sensor_type=""):
        super().__init__(data, device_id, sensor_type)
        self._device_name = self.get_device_name()
        _LOGGER.info("{} device init".format(self._device_name))

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()
        self._state = self._state = self.data.wiserSmart.getWiserHomeMode()

    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
            "identifiers": {(DOMAIN, self.data.unique_id)},
        }

    def get_device_name(self):
        """Return the name of the Device """
        return "Wiser Operation Mode"

    @property
    def icon(self):
        return WISER_SMART_HOME_MODE_ICONS[self._state]
