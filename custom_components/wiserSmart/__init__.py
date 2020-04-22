"""
Wiser Smart Compoment for Wiser Smart System (White Cross)

Includes Climate, Sensor Devices and switches

https://github.com/tomtomfx/wiserSmartForHA
thomas.fayoux@gmail.com
"""
import asyncio
import json

# import time
from datetime import datetime, timedelta
import voluptuous as vol
from wiserSmartAPI.wiserSmart import (
    wiserSmart,
    TEMP_MINIMUM,
    TEMP_MAXIMUM,
    WiserControllerTimeoutException,
    WiserControllerAuthenticationException,
    WiserRESTException,
)
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_USER,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC

from .const import (
    _LOGGER,
    DATA_WISER_SMART_CONFIG,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    CONTROLLERNAME,
    MANUFACTURER,
    NOTIFICATION_ID,
    NOTIFICATION_TITLE,
    VERSION,
    WISER_SMART_PLATFORMS,
    WISER_SMART_SERVICES,
)


# Set config values to default
# These get set to config later
SCAN_INTERVAL = DEFAULT_SCAN_INTERVAL

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_USER): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int)
        ),
    }
)


async def async_setup(hass, config):
    """
    Wiser smart uses config flow for configuration.
    But, a "wiserSmart:" entry in configuration.yaml will trigger an import flow
    if a config entry doesn't already exist. If it exists, the import
    flow will attempt to import it and create a config entry, to assist users
    migrating from the old wiser smart component. Otherwise, the user will have to
    continue setting up the integration via the config flow.
    """
    hass.data[DATA_WISER_SMART_CONFIG] = config.get(DOMAIN, {})

    if not hass.config_entries.async_entries(DOMAIN) and hass.data[DATA_WISER_SMART_CONFIG]:
        # No config entry exists and configuration.yaml config exists, trigger the import flow.
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=hass.data[DATA_WISER_SMART_CONFIG],
            )
        )

    return True


async def async_setup_entry(hass, config_entry):

    global SCAN_INTERVAL

    """Set up the Wiser Smart component."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    SCAN_INTERVAL = int(
        config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )

    _LOGGER.info(
        "Wiser Smart setup with Controller IP =  {} and scan interval of {} seconds".format(
            config_entry.data[CONF_HOST], SCAN_INTERVAL
        )
    )
    config_entry.add_update_listener(config_update_listener)

    data = WiserSmartControllerHandle(
        hass,
        config_entry,
        config_entry.data[CONF_HOST],
        config_entry.data[CONF_USER],
        config_entry.data[CONF_PASSWORD],
    )

    @callback
    def retryWiserSmartControllerSetup():
        hass.async_create_task(wiserSmartControllerSetup())

    async def wiserSmartControllerSetup():
        _LOGGER.info("Initiating wiserSmart Controller connection")
        try:
            if await data.async_update():
                if data.wiserSmart.getWiserDevices is None:
                    _LOGGER.error("No Wiser devices found to set up")
                    return False

                hass.data[DOMAIN] = data

                for platform in WISER_SMART_PLATFORMS:
                    hass.async_create_task(
                        hass.config_entries.async_forward_entry_setup(
                            config_entry, platform
                        )
                    )

                _LOGGER.info("Wiser Smart Component Setup Completed")
                return True
            else:
                await scheduleWiserSmartSetup()
                return True
        except (asyncio.TimeoutError):
            await scheduleWiserSmartSetup()
            return True
        except WiserControllerTimeoutException:
            await scheduleWiserSmartSetup()
            return True

    async def scheduleWiserSmartSetup(interval=30):
        _LOGGER.error(
            "Unable to connect to the Wiser Controller, retrying in {} seconds".format(
                interval
            )
        )
        hass.loop.call_later(interval, retryWiserSmartControllerSetup)
        return

    hass.async_create_task(wiserSmartControllerSetup())
    await data.async_update_device_registry()
    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""

    # Deregister services
    _LOGGER.debug("Unregister Wiser Smart Services")
    for service in WISER_SMART_SERVICES:
        hass.services.async_remove(DOMAIN, WISER_SMART_SERVICES[service])

    _LOGGER.debug("Unloading Wiser Smart Component")
    tasks = []
    for platform in WISER_SMART_PLATFORMS:
        tasks.append(
            hass.config_entries.async_forward_entry_unload(config_entry, platform)
        )

    unload_status = all(await asyncio.gather(*tasks))
    if unload_status:
        hass.data.pop(DOMAIN)
    return unload_status


async def config_update_listener(hass, config_entry):
    """Handle config update update."""
    global SCAN_INTERVAL

    SCAN_INTERVAL = int(config_entry.data.get(CONF_SCAN_INTERVAL))
    _LOGGER.info(
        "Wiser config parameters changed, scan interval = {}".format(
            SCAN_INTERVAL,
        )
    )


class WiserSmartControllerHandle:
    def __init__(self, hass, config_entry, ip, user, password):
        self._hass = hass
        self._config_entry = config_entry
        self._name = config_entry.data[CONF_NAME]
        self.ip = ip
        self.user = user
        self.password = password
        self.wiserSmart = wiserSmart(ip, user, password)
        self.minimum_temp = TEMP_MINIMUM
        self.maximum_temp = TEMP_MAXIMUM
        self.timer_handle = None

    @callback
    def do_controller_update(self):
        self._hass.async_create_task(self.async_update())

    async def async_update(self, no_throttle: bool = False):
        # Update uses event loop scheduler for scan interval
        if no_throttle:
            # Forced update
            _LOGGER.info("**Update of Wiser Smart data requested via On Demand**")
            # Cancel next scheduled update and schedule for next interval
            if self.timer_handle:
                self.timer_handle.cancel()
        else:
            # Updated on schedule
            _LOGGER.info(
                "**Update of Wiser Smart data requested on {} seconds interval**".format(
                    SCAN_INTERVAL
                )
            )
        # Schedule next update
        self.timer_handle = self._hass.loop.call_later(
            SCAN_INTERVAL, self.do_controller_update
        )

        try:
            # Update from Wiser Controller
            result = await self._hass.async_add_executor_job(self.wiserSmart.refreshData)
            if result is not None:
                _LOGGER.info("**Wiser Smart data updated**")
                # Send update notice to all components to update
                dispatcher_send(self._hass, "WiserSmartUpdateMessage")
                return True
            else:
                _LOGGER.error("**Unable to update from Wiser Controller**")
                return False
        except json.decoder.JSONDecodeError as JSONex:
            _LOGGER.error(
                "Data not in JSON format when getting data from the Wiser Controller, "
                + "did you enter the right URL? error {}".format(str(JSONex))
            )
            return False
        except WiserControllerTimeoutException as ex:
            _LOGGER.error(
                "***Failed to get update from Wiser Smart due to timeout error***"
            )
            _LOGGER.debug("Error is {}".format(ex))
            return False
        except Exception as ex:
            _LOGGER.error(
                "***Failed to get update from Wiser Smart due to unknown error***"
            )
            _LOGGER.debug("Error is {}".format(ex))
            return False

    @property
    def unique_id(self):
        return self._name

    async def async_update_device_registry(self):
        """Update device registry."""
        device_registry = await self._hass.helpers.device_registry.async_get_registry()
        device_registry.async_get_or_create(
            config_entry_id=self._config_entry.entry_id,
            identifiers={(DOMAIN, self.unique_id)},
            manufacturer=MANUFACTURER,
            name=CONTROLLERNAME,
            model="Wiser Smart Controller",
        )

    async def set_home_mode(self, mode, comeBackTime):
        hcMode = "manual" if mode in ["manual"] else "schedule"
        if self.wiserSmart is None:
            self.wiserSmart = wiserSmart(self.ip, self.user, self.password)
        _LOGGER.debug(
            "Setting home mode to {}.".format(mode)
        )
        try:
            self.wiserhub.setWiserHomeMode(self, hcMode, mode, comeBackTime)
            await self.async_update(no_throttle=True)
        except BaseException as e:
            _LOGGER.debug("Error setting home mode! {}".format(str(e)))

    async def set_appliance_state(self, applianceName, state):
        """
        Set the state of the smart plug,
        :param applianceName:
        :param state: Can be True or False
        :return:
        """
        if self.wiserSmart is None:
            self.wiserSmart = wiserSmart(self.ip, self.user, self.password)
        _LOGGER.info("Setting appliance {} to {} ".format(applianceName, state))

        try:
            self.wiserSmart.setWiserApplianceState(self, applianceName, state)
            # Add small delay to allow hub to update status before refreshing
            await asyncio.sleep(0.5)
            await self.async_update(no_throttle=True)

        except BaseException as e:
            _LOGGER.debug(
                "Error setting Appliance {} to {}, error {}".format(
                    applianceName, state, str(e)
                )
            )

