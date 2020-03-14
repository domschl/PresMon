# PresMon

***Project status: alpha.*** Structure, configuration and functionality will change and is far from final.

Computer presence monitoring via keyboard events and [Home Assistant](https://www.home-assistant.io/) binary_sensor presence integration.

`PresMon` is a python daemon (installable as systemd service) that monitors a computer for input activity, and generates a presence signal. The presence information is publish via MQTT and is then available as binary_sensor within Home Assistant.

Home Assistant's mqtt auto-discovery is supported, a presence sensor (type binary_sensor, device_class presence)`binary_sensor.<ha_presence_devname>` is automatically generated in Home Assistant. The name can be configured in the config file `presmon.yaml`, s.b.

## Configuration

* Copy `presmon-default.yaml` to `presmon.yaml` and customize.
* For systemd service installations, adapt `presmon.service`

### Configuration file `presmon.yaml`

* At mininmum, configure `mqtt: broker` and `homeassistant: presence_name`. 
* Check which services should be active
* After testing, increase `input: timeout` to a higher value (e.g. 300)

## Installation

Requirements: [`paho-mqtt`](https://pypi.org/project/paho-mqtt/), [`keyboard`](https://pypi.org/project/keyboard/), [`bluepy`](https://github.com/IanHarvey/bluepy) [optional, Linux only]. [`mouse`](https://github.com/boppreh/mouse) [optional, Linux, Windows, problems with systemd] Since `presmon` needs to run as root, the dependencies must be installed for the root user.

`presmon` needs to be run as root, either as systemd service, or via

```bash
sudo python presmon.py [--help] [-k]
```

Mac: the terminal that runs this script needs Mac OS Catalina 'Accessibility' right, otherwise this will just crash.

Once the script runs, a new binary_sensor can be found in Home Assistant (name: `binary_sensor.<ha_presence_devname>` as configured in `presmon.json`).

### Hints for automatic start

* There seems to be a problem with the `mouse` module and running `presmon.py` as systemd service. The process crashes on mouse events. So only use this with systemd, if the mouse option is set to `false` in `presmon.json`.
* For Linux, Mac it might be useful to allow `presmon.py` to run with `sudo` without password. That can be achieved by using `visudo` and adding a line: 

```
<your-username> ALL = NOPASSWD: <full-path-to-script>/presmon.py
```

`presmon.py` needs to be executable (`chmod a+x presmon.py`).
* Create an autostart script (requires the `visudo` entry in order to run without passwordl-prompt):

```bash
#!/bin/bash
sudo <full-path-to-script>/presmon.py -f &
```

and use your desktop environments autostart-feature to start this script on login.

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
* Paste and adapt: `sudo /<full-path-to-script>/presmon.py -f &>/dev/null &`. The redirection of the output suppresses the eternally spinning gear of Automator.

<img src="https://github.com/domschl/PresMon/blob/master/Resources/Automator.png" width="480" />

* Save your application
* Use Control Panel Security / Privacy to add your newly created Automator application to 'Accessibility' (which allows the input monitoring).
* Use Control Panel user administration to add a new startup item, and add the application that was created with automator. 

## Notes

* Windows has not been tested, but might work.
* The `keyboard` library on Linux sometimes registers mouse clicks, depending on context.
* The mouse lib causes a SEGV crash, if run as systemd service. Cause not yet investigated. Works fine, if started via autostart.

