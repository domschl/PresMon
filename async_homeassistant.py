import json
import time
import logging
import re
import socket
import asyncio
import uuid
import platform

HA_VERSION="0.2.1"

class AsyncHABinarySensor():
    def __init__(self, loop, mqtt, devtype, name=None, homeassistant_discovery_prefix='homeassistant'):  
        self.creation_time=time.time()
        self.log = logging.getLogger("HABinarySensor")
        self.loop = loop
        if devtype not in ['presence', 'key']:
            self.log.error(f'Invalid devtype {devtype}')
            print(f'Invalid devtype {devtype} used, check yaml config.')
            exit(-1)
        hostname=socket.gethostname()
        ind=hostname.find('.')
        if ind != -1:
            hostname=hostname[:ind]
        hostname=hostname[0].upper()+hostname[1:]
        if name is None:
            name=hostname+'_'+devtype
            topic_root=hostname+'/'+devtype
        else:
            cname=""
            val_name=re.compile(r"[A-Za-z0-9_-]")
            for c in name:
                if val_name.match(c) is None:
                    cname+="_"
                else:
                    cname+=c
            name=cname
            name=hostname+'_'+devtype+'_'+name
            topic_root=name+'/'+devtype+'/'+name
        nd=hex(uuid.getnode())[2:]
        self.mac_address=f"{nd[0:2]}:{nd[2:4]}:{nd[4:6]}:{nd[6:8]}:{nd[8:10]}:{nd[10:12]}"
        self.ip_address=self.get_ip()
        self.uuid=f"{self.mac_address}-{name}"

        self.mqtt=mqtt
        self.homeassistant_discovery_prefix=homeassistant_discovery_prefix

        self.state_topic=f"{topic_root}/state"
        self.discovery_topic=f"{homeassistant_discovery_prefix}/binary_sensor/{name}/config"
        self.avail_topic=f"{hostname}/presmon/availability"
        self.attributes_topic=f"{topic_root}/attributes"
        
        if devtype=='key':
            device_class=None
        else:
            device_class=devtype

        disco={
            "name": name,
            "unique_id": self.uuid,
            "payload_off": "off",
            "payload_on": "on",
            "payload_not_available": "off",
            "payload_available": "on",
            "state_topic": self.state_topic,
            "device": {
                "name": hostname+"_presmon",
                "connections": [("mac", self.mac_address),],
                "identifiers": [self.mac_address],
                "manufacturer": "muWerk",
                "model": "Advanced presence sensor",
                "sw_version": HA_VERSION
            },
            "availability_topic": self.avail_topic,
            "json_attributes_topic": self.attributes_topic
        }
        if device_class is not None:
            disco['device_class'] = device_class
        self.discovery_payload=json.dumps(disco)
        self.last_will_topic=self.avail_topic
        self.last_will_message="off"

    def get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def update_attributes(self):
        system, release, version = platform.system_alias(platform.system(), platform.release(), platform.version())
        uptime=self.creation_time-time.time()
        uphours=int(uptime/3600)
        updays=int(uphours/24)
        uphours=uphours-updays*24
        uptime=f"{updays}d, {uphours}h"
        attributes={
            'System': system,
            'Release': release,
            'Version': version,
            'Host': socket.gethostname(),
            'MAC': self.mac_address,
            'IP': self.ip_address,
            'Sensor uptime': uptime,
            'Sensor version': HA_VERSION
        }
        attribs_payload=json.dumps(attributes)
        self.mqtt.publish(self.attributes_topic, attribs_payload)

    def register_auto_discovery(self):
        self.mqtt.publish(self.discovery_topic, self.discovery_payload, retain=True)
        self.mqtt.publish(self.avail_topic, "on")
        self.update_attributes()

    def set_state(self, state):
        if state is True:
            self.log.debug('Publishing `on` state.')
            self.mqtt.publish(self.avail_topic, "on")
            self.update_attributes()
            self.mqtt.publish(self.state_topic, "on", retain=True)
        else:
            self.log.debug('Publishing `off` state.')
            self.mqtt.publish(self.avail_topic, "on")
            self.update_attributes()
            self.mqtt.publish(self.state_topic, "off", retain=True)
