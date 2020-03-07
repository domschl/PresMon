# PresMon [WIP]
Computer presence monitoring via keyboard events and [Home Assistant](https://www.home-assistant.io/) binary_sensor presence integration.

**Work in Progress**

`PresMon` is a python daemon (installable as systemd service) that monitors a computer for input activity, and generates a presence signal. The presence information is publish via MQTT and is then available as binary_sensor within Home Assistant.

Home Assistant's mqtt auto-discovery is supported, a presence sensor (type binary_sensor, device_class presence)`binary_sensor.<ha_presence_devname>` is automatically generated in Home Assistant. The name can be configured in the config file `presmon.json`, s.b.

## Configuration

* Copy `presmon.json.default` to `presmon.json` and customize.
* For systemd service installations, adapt `presmon.service`

### Configuration file `presmon.json`

| Field        | Remark |
| ------------ | ------- |
| `"input"` | `true`: Monitor for mouse and/or keyboard input events. On `false`, all input event monitoring is disabled.
| `"keyboard"` | `true` or `false`. On `true` the python module `keyboard` is required, and a global keyboard hook is installed to generate presence information. |
| `"mouse"` | `true` or `false`. On `true` the python module `mouse` is required, and a global keyboard hook is installed to generate presence information. The `mouse` module currently doesn't support macOS. Linux and Windows are supported. Doesn't work with systemd services, TBD. |
| `"input_timeout"` | Default `180`, number of seconds after the last keyboard/mouse event when presence information is switched to 'absent'. |
| `"ble"` | Default `false`, on `true` python moduel `bluepy` is required. Functionality NOT YET COMPLETED AND LINUX ONLY. |
| `"ha_mqtt"` | Default `true`. On `true` python module `paho-mqtt` is required, and presence information is published via mqtt. |
| `"ha_presence_devname"` | A name for this computer. The name is used (1) to generate an mqtt topic for publishing the presence information, topic: `<name>/presence/state`, payload: `on` (string, presence detected) or `off`. (2) to derive the name of a new Home Assistant binary sensor: `binary_sensor.<ha_presence_devname>`. |
| `"mqtt_server"` | Hostname of mqtt server |


## Installation

Requirements: [`paho-mqtt`](https://pypi.org/project/paho-mqtt/), [`keyboard`](https://pypi.org/project/keyboard/), [`bluepy`](https://github.com/IanHarvey/bluepy) [optional, Linux only]. [`mouse`](https://github.com/boppreh/mouse) [optional, Linux, Windows, problems with systemd] Since `presmon` needs to run as root, the dependencies must be installed for the root user.

`presmon` needs to be run as root, either as systemd service, or via

```bash
sudo python presmon.py
```

Mac: the terminal that runs this script needs Mac OS Catalina 'Accessibility' right, otherwise this will just crash.

Once the script runs, a new binary_sensor can be found in Home Assistant (name: `binary_sensor.<ha_presence_devname>` as configured in `presmon.json`).

## Notes

* Windows has not been tested, but might work.
* The `keyboard` library on Linux sometimes registers mouse clicks, depending on context.
* The mouse lib causes a SEGV crash, if run as service. Cause not yet investigated.

