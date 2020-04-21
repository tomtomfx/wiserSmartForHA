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
    STATE_UNKNOWN,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.icon import icon_for_battery_level

from .const import (
    _LOGGER,
    DOMAIN,
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
            # Add based on device type due to battery values sometimes not showing
            # until sometime after a hub restart
            if device.get("powerType") == "Battery":
                wiserSmart_devices.append(
                    WiserSmartBatterySensor(data, device.get("name"), sensor_type="Battery")
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
        self._battery_level = None
        _LOGGER.info("{} device init".format(self._device_name))

    async def async_update(self):
        """Fetch new state data for the sensor."""
        await super().async_update()

        device = self.data.wiserSmart.getWiserDeviceInfo(self._deviceId)

        # Set battery info
        self._battery_level = device.get("batteryLevel")

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
            self.data.wiserhub.getWiserDeviceInfo(self._deviceId).get("batteryLevel") or None
        )
        return attrs

    def get_device_name(self):
        """Return the name of the Device"""
        deviceName = str(
            self.data.wiserhub.getWiserDeviceInfo(self._deviceId).get("name") or ""
        )

        # Multiple ones get automagically number _n by HA
        return (
            "WiserSmart "
            + self._deviceId
            + "-"
            + self.data.wiserhub.getWiserDeviceInfo(self._deviceId).get("location")
            + " Battery Level"
        )

    @property
    def device_info(self):
        """Return device specific attributes."""
        deviceName = self.data.wiserSmart.getWiserDeviceInfo(self._deviceId).get("name")
        return {"identifiers": {(DOMAIN, "{}-{}".format(deviceName, self._deviceId))}}


class WiserSmartDeviceSensor(WiserSmartSensor):
    """Definition of Wiser Smart Device Sensor"""

    def __init__(self, data, device_id=0, sensor_type=""):
        super().__init__(data, device_id, sensor_type)
        self._device_name = self.get_device_name()
        self._battery_level = None
        self.__powerConsump = None
        self._battery_percent = 0
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
        identifier = None

        # Thermostat
        if (self.data.wiserSmart.getWiserDeviceInfo(self._deviceId).get("modelId") == "EH-ZB-RTS"):
            identifier = "Thermostat-{}".format(self._device_name)
        # Appliance
        elif (self.data.wiserSmart.getWiserDeviceInfo(self._deviceId).get("modelId") == "EH-ZB-SPD"):
            identifier = "Plug-{}".format(self._device_name)
        # Heater
        elif (self.data.wiserSmart.getWiserDeviceInfo(self._deviceId).get("modelId") == "EH-ZB-HACT"):
            identifier = "Heater-{}".format(self._device_name)
        # Water Heater
        elif (self.data.wiserSmart.getWiserDeviceInfo(self._deviceId).get("modelId") == "EH-ZB-LMACT"):
            identifier = "WaterHeater-{}".format(self._device_name)

        if (identifier != None):
            return {"identifiers": {(DOMAIN, identifier)}}
        return None

    def get_device_name(self):
        """Return the name of the Device"""
        modelId = str(
            self.data.wiserSmart.getWiserDeviceInfo(self._deviceId).get("modelId") or ""
        )

        if modelId == "EH-ZB-SPD":
            return "WiserSmart " + self.data.wiserSmart.getWiserDeviceInfo(self._deviceId).get("name")
        else
            # Multiple ones get automagically number _n by HA
            return (
                "WiserSmart "
                + self._deviceId
                + "-"
                + self.data.wiserSmart.getWiserDeviceInfo(self._deviceId).get("location")
            )

    @property
    def icon(self):
        """Return icon for signal strength"""
        try:
            return SIGNAL_STRENGTH_ICONS[
                self.data.wiserSmart.getWiserDeviceInfo(self._deviceId).get("status")
            ]
        except KeyError:
            # Handle anything else as no signal
            return SIGNAL_STRENGTH_ICONS["OFFLINE"]

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

        if self._sensor_type in ["Battery"] and device_data.get("BatteryLevel"):
            self._battery_level = device_data.get("BatteryLevel")
            self._battery_percent = 10 * self._battery_level

            attrs["battery_percent"] = self._battery_percent
            attrs["battery_level"] = device_data.get("BatteryLevel")
            
        elif self._sensor_type in ["EH-ZB-SPD", "EH-ZB-LMACT"]:
            self._powerConsump = device_data.get("powerConsump")
        
        return attrs

class WiserSystemCloudSensor(WiserSensor):
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


class WiserSystemOperationModeSensor(WiserSensor):
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
