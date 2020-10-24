# wiserSmartForHA

Home assistant component for the Wiser Smart Controller (White cross)

![](https://github.com/tomtomfx/wiserSmartForHA/blob/master/docs/visuel-wiser.jpg)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Please use HACS for installation.

## Functionalities

This Home assistant component allows monitoring and controlling the Schneider Wiser Smart system.
It contains:

- Support for [Home Assistant Component Store](https://community.home-assistant.io/t/custom-component-hacs/121727)

- Use the Home Assistant config flow to be setup directly through the integrations panel

- Monitoring for Rooms (Thermostats + heaters), Smart plugs and water heater

- **Wiser Smart Controller**

    - Monitor the current mode
    - Monitor the correct cloud connection
    - Set the global working mode

- **Wiser Smart Rooms**

    - Status online/offline of each the devices in a Room
    - Monitor the current temperature
    - Read and set the target temperature
    - Status online/offline of each of the devices

- **Wiser Smart plugs and water heater**

    - Get the current state of the plug/water heater
    - Switch the state of the plug/water heater
    - Retrieve the power consumption
    - Status online/offline of each of the devices

## Display example

![](https://github.com/tomtomfx/wiserSmartForHA/blob/master/docs/ha_display.png)

## Restrictions

- Works only with the electrical heaters and not the TRVs as I do not have them in my system
- Get and set schedule for all or one room not available yet

# Integration installation & setup

It is highly recommended to use HACS to install the integration. Please see HACS website for more information at https://hacs.xyz/

## Installation

- Add the Github repository to HACS as an integration 
- In the integration page look for Wiser Smart Component for Home Assissant

![](https://github.com/tomtomfx/wiserSmartForHA/blob/master/docs/ha_hacs_wiser.png)

- Install it
- You will be asked to restart HA

## Setup integration

This component is using the config flow to avoid having to populate the configuration yaml file

- Go to integration and click on "+"
- Search "Wiser Smart"

![](https://github.com/tomtomfx/wiserSmartForHA/blob/master/docs/ha_integration.png)

- You will be asked for 4 parameters

```IP address``` is the IP address of the Wiser Smart Controller on your network

```Username``` is the username used to login on your local system (should be "admin")

```Password``` is the password that goes along the username (by default "admin")

```Scan Interval``` is the duration between two calls towards the Controller (A value too small may overlaod the controller)

## Mode select and automations

To set the working mode (manual, schedule, holiday, energysaver) add:

- An input_select to select the mode you want WiserSmart to be in

```
input_select:
  wisersmart_mode_select:
    name: WiserSmart mode
    options:
      - manual
      - schedule
      - energysaver
      - holiday
    initial: schedule
    icon: mdi:target
```
- Automations to ensure that the input_select is in the current mode by default and if changed sets WiserSmart in the selected mode

```
# Home mode input.select default value
- id: '1'
  alias: Set home mode to input select
  trigger:
  - platform: state
    entity_id: sensor.wiser_operation_mode
  action:
   - service: input_select.select_option
     data_template:
       entity_id: input_select.wisersmart_mode_select
       option: "{{ states('sensor.wiser_operation_mode') }}"

# Set home mode using the input select
- id: '2'
  alias: Set home mode from input select
  trigger:
  - platform: state
    entity_id: input_select.wisersmart_mode_select
  action:
   - service: wisersmart.set_home_mode
     data_template:
       mode: "{{ states('input_select.wisersmart_mode_select') }}"
       come_back_time: "{{ state_attr('input_datetime.back_from_vacation', 'timestamp') | int }}"

```

## Please play with this integration and provide feedback, bugs and enhancements 

# Change log

- 0.9.4
    * Add valve support
    
- 0.9.3
    * ClimateDevice to ClimateEntity
    * SwitchDevice to SwitchEntity
    
- 0.9.2
    * Add power consumption entity for plugs and water heater devices
    * Add service to set Wiser Smart mode
    * Fix I/O in event loop

- 0.9.1
    * Update readme
    * Fix batterry value (factor 10 was missing)
    * Add power consumption to sensor for plugs

- 0.9.0
    * First release
    * Retrieving all the Wiser Smart information
    * Changing target temperature on the thermostats
    * Changing plugs and water heater state

# Thanks

Inspired from https://github.com/asantaga/wiserHomeAssistantPlatform designed by asantaga initially done for Drayton Wiser.
Thanks to him as his code is really good and helped understand the needs
