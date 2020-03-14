import json
import time
import logging
import re
import socket
import asyncio
import uuid


class AsyncHABinarySensor():
    def __init__(self, loop, mqtt, name, devtype, homeassistant_discovery_prefix='homeassistant'):  
        self.log = logging.getLogger("HABinarySensor")
        self.loop = loop
        if devtype not in ['presence', 'key']:
            self.log.error(f'Invalid devtype {devtype}')

        if name is None:
            name=socket.gethostname()
            name=name[0].upper()+name[1:]
            name+="_"+type
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
        self.homeassistant_discovery_prefix=homeassistant_discovery_prefix

        self.state_topic=f"{name}/"+devtype+"/state"
        self.discovery_topic=f"{homeassistant_discovery_prefix}/binary_sensor/presence-{name}/config"
        # avail_topic=f"{name}/presence/available"
        if devtype=='key':
            device_class=None
        else:
            device_class=devtype

        disco={
            "name": name,
            "unique_id": self.uuid,
            "device_class": device_class,
            "payload_off": "off",
            "payload_on": "on",
            "state_topic": self.state_topic
            # "availablility_topic": avail_topic,
        }
        self.discovery_payload=json.dumps(disco)
        self.last_will_topic=self.state_topic
        self.last_will_message="off"
        
    def register_auto_discovery(self):
        self.mqtt.publish(self.discovery_topic, self.discovery_payload, retain=True)

    def set_state(self, state):
        if state is True:
            self.log.debug('Publishing `on` state.')
            self.mqtt.publish(self.state_topic, "on", retain=True)
        else:
            self.log.debug('Publishing `off` state.')
            self.mqtt.publish(self.state_topic, "off", retain=True)
