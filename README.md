# PresMon [WIP]
Computer presence monitoring and home assistant integration

``Work in Progress``

`PresMon` is a python daemon (installable as systemd service) that monitors a computer for input activity, and generates a presence signal. The presence information is publish via MQTT.

[Home Assistant](https://www.home-assistant.io/)'s mqtt auto-discovery for mqtt is supported, a presence sensor (with name defined in presmon.json, `ha_presence_devname`).

## Configuration

Adapt `presmon.service` for your installation, copy `presmon.json.default` to `presmon.json` and customize.

### `presmon.json`

t.b.d.

## Installation

Requirements: `paho-mqtt`, `keyboard`, `bluepy` [optional].
