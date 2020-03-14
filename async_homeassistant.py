import json
import time
import logging
import re
import socket
import asyncio
import uuid


class AsyncHABinarySensorPresence():
    def __init__(self, loop, mqtt, name=None, homeassistant_discovery=True, homeassistant_discovery_prefix='homeassistant'):  
        self.log = logging.getLogger("HABinarySensor")
        self.loop = loop

        if name is None:
            name=socket.gethostname()
            name=name[0].upper()+name[1:]
            name+="_presence"
        cname=""
        val_name=re.compile(r"[A-Za-z_-]")
        for c in name:
            if val_name.match(c) is None:
                cname+="_"
            else:
                cname+=c
        self.name=cname
        nd=hex(uuid.getnode())[2:]
        self.uuid=f"{nd[0:2]}:{nd[2:4]}:{nd[4:6]}:{nd[6:8]}:{nd[8:10]}:{nd[10:12]}-{name}"

        self.mqtt=mqtt
        self.homeassistant_discovery=homeassistant_discovery
        self.homeassistant_discovery_prefix=homeassistant_discovery_prefix

        self.state_topic=f"{name}/presence/state"
        if homeassistant_discovery is True:
            self.discovery_topic=f"{homeassistant_discovery_prefix}/binary_sensor/presence-{name}/config"
            # avail_topic=f"{name}/presence/available"
            self.discovery_payload=json.dumps({
                "name": name,
                "unique_id": self.uuid,
                "device_class": "presence",
                "payload_off": "off",
                "payload_on": "on",
                "state_topic": self.state_topic
                # "availablility_topic": avail_topic,
            })
        self.last_will_topic=self.state_topic
        self.last_will_message="off"
        # mqtt.last_will(self.last_will_topic, self.last_will_message)
        
    def register_auto_discovery(self):
        if self.homeassistant_discovery is True:
            self.mqtt.publish(self.discovery_topic, self.discovery_payload, retain=True)

    def set_state(self, state):
        if state is True:
            self.log.debug('Publishing `on` state.')
            self.mqtt.publish(self.state_topic, "on", retain=True)
        else:
            self.log.debug('Publishing `off` state.')
            self.mqtt.publish(self.state_topic, "off", retain=True)
