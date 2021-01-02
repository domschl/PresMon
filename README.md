# PresMon

***Project status: beta.*** 

Computer presence monitoring via keyboard events and [Home Assistant](https://www.home-assistant.io/) binary_sensor presence and hotkey integration.

`PresMon` is a python daemon (installable as systemd service) that monitors a computer for input activity, and generates a presence signal. The presence information is publish via MQTT and is then available as binary_sensor within Home Assistant.

Home Assistant's mqtt auto-discovery is supported, a presence sensor (type binary_sensor, device_class presence)`binary_sensor.<homeassistant: <entity_name>_presence` is automatically generated in Home Assistant. The name can be configured in the config file `presmon.yaml`, and is the computer's hostname by default.

Additionally keyboard-hotkeys can be exported as Home Assistant binary sensors of name `binary_sensor.<homeassistant: <entity_name>_key_<keyname>`. Use your keyboard to control your Home Assistant setup. Buttons can be used in `button` mode (HA binary
sensor is on while keyboard hotkey is pressed), or `flipflop` mode (first time hotkey is pressed, HA binary sensor switches on, next time hotkey is pressed, binary sensor switches off). See `presmon_default.yaml` for examples and more information.

## Configuration

* Copy `presmon-default.yaml` to `presmon.yaml` and customize.
* For systemd service installations, adapt `presmon.service`

### Configuration file `presmon.yaml`

* At mininmum, configure `mqtt: broker`. 
* Check which services should be active
* After testing, increase `input: timeout` to a higher value (e.g. 300)

## Installation

Requirements: [ruamel.yaml](https://pypi.org/project/ruamel.yaml/), [`paho-mqtt`](https://pypi.org/project/paho-mqtt/), [`keyboard`](https://pypi.org/project/keyboard/), [`bluepy`](https://github.com/IanHarvey/bluepy) [optional, Linux only]. [`mouse`](https://github.com/boppreh/mouse) [optional, Linux, Windows, problems with systemd] Since `presmon` needs to run as root, the dependencies must be installed for the root user.

`presmon` needs to be run as root, either as systemd service, or via

```bash
sudo python presmon.py [--help] [-k]
```

Mac: the terminal that runs this script needs Mac OS Catalina 'Accessibility' right, otherwise this will just crash.

### Hints for automatic start

* There seems to be a problem with the `mouse` module and running `presmon.py` as systemd service. The process crashes on mouse events. So only use this with systemd, if the mouse option is set to `false` in `presmon.yaml`.
* For Linux, Mac it might be useful to allow `presmon.py` to run with `sudo` without password. That can be achieved by using `visudo` and adding a line: 

```
<your-username> ALL = NOPASSWD: <full-path-to-script>/presmon.py
```

`presmon.py` needs to be executable (`chmod a+x presmon.py`).
* Create an autostart script (requires the `visudo` entry in order to run without passwordl-prompt), you can modify and rename `start.default.sh`; edit it and rename it to `start.sh`:

```bash
#!/bin/bash
sudo <full-path-to-script>/presmon.py &
```

and use your desktop environments autostart-feature to start this script on login. Some desktops (e.g. Gnome) need a `.desktop` file for autostart to recognize the script. You can modify and rename the template `PresMon.default.desktop`. Rename it to `PresMon.desktop` and copy it to an applications directory, e.g. `~/.local/share/applications/`. Then update the database with `update-desktop-database ~/.local/share/applications/`.

### macOS autostart

For Macs, a few extra things are required:

* Use `sudo visudo` to insert (replace username and path) after line `%admin      ALL = (ALL) ALL`:

```
<your-username> ALL=(ALL)  NOPASSWD: /<full-path-to-script>/presmon.py
```

* Make sure `presmon.py` is executable (`chmod a+x presmon.py`)
* Automator will use Catalina's system `/usr/bin/python3`. So the dependencies (`paho-mqtt`, `keyboard`) need
to be installed for the system python (using `sudo /usr/bin/pip3 install paho-mqtt keyboard`)
* Use the macOS automator app to create a new 'Application'.
* Add 'shell script'
* Paste and adapt: `sudo /<full-path-to-script>/presmon.py &>/dev/null &`. The redirection of the output suppresses the eternally spinning gear of Automator.

<img src="https://github.com/domschl/PresMon/blob/master/Resources/Automator.png" width="480" />

* Save your application
* Use Control Panel Security / Privacy to add your newly created Automator application to 'Accessibility' (which allows the input monitoring).
* Use Control Panel user administration to add a new startup item, and add the application that was created with automator. 

## History
* 2021-01-02: switched from pyyaml to ruamel.yaml (preserves comments on load/dump cycle), make first-time MAC into UUID to prevent MAC
  randomization to mess up device-ids.

## Notes

* Windows has not been tested, but might work.
* The `keyboard` library on Linux sometimes registers mouse clicks, depending on context. Currently, the key-release hotkey handling is broken (workaround via timer implemented)
* The mouse lib causes a SEGV crash, if run as systemd service. Cause not yet investigated. Works fine, if started via autostart.
