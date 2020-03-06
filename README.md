# PresMon [WIP]
Computer presence monitoring via keyboard events and [Home Assistant](https://www.home-assistant.io/) binary_sensor presence integration.

``Work in Progress``

`PresMon` is a python daemon (installable as systemd service) that monitors a computer for input activity, and generates a presence signal. The presence information is publish via MQTT and is then available as binary_sensor within Home Assitant

Home Assistant's mqtt auto-discovery for mqtt is supported, a presence sensor (type binary_sensor, device_class presence), with name defined in presmon.json, `ha_presence_devname`, s.b.

## Configuration

* Copy `presmon.json.default` to `presmon.json` and customize. (s.b.)
* For systemd service installations, adapt `presmon.service`

### `presmon.json`

| Field        | Remark |
| ------------ | ------- |
| `"keyboard"` | `true` or `false`. On `true` the python module `keyboard` is required, and a global keyboard hook is installed to generate presence information. |
| `"keyboard_timeout"` | Default `180`, number of seconds after the last keyboard event when precence information is switched to absent. |
| `"ble"` | Default `false`, on `true` python moduel `bluepy` is required. Functionality NOT YET COMPLETED. |
| `"ha_mqtt"` | Default `true`. On `true` python module `paho-mqtt` is required, and presence information is published via mqtt. |
| `"ha_presence_devname"` | A name for this computer. The name is used to generate an mqtt topic for publishing the presence information, topic: `<name>/presence/state`, payload: `on` (string, presence detected) or `off`.  |
| `"mqtt_server"` | Hostname of mqtt server |


## Installation

Requirements: `paho-mqtt`, `keyboard`, `bluepy` [optional].
Needs to be run as root, either as systemd service, or via

```bash
sudo python presmon.py
```

Mac: the terminal that runs this script needs Mac OS Catalina 'Accessibility' right, otherwise this will just crash.

## Notes

* Windows has not been tested, but might work.
* The `keyboard` library on Mac does not generate events for mouse clicks, while the Linux implementation also reacts on mouse clicks, so presence for Mac is only derived from keyboard and for Linux is derived from both keyboard and mouse clicks (but not from mouse movements or scroll-wheel)
