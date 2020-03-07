import json
import time
import logging
import re
import socket
import asyncio
import uuid

import paho.mqtt.client as mqtt


class AsyncMqttHelper:
    '''Helper module for async wrapper for paho mqtt'''
    def __init__(self, log, loop, client):
        self.log = log
        self.loop = loop
        self.client = client
        self.client.on_socket_open = self.on_socket_open
        self.client.on_socket_close = self.on_socket_close
        self.client.on_socket_register_write = self.on_socket_register_write
        self.client.on_socket_unregister_write = self.on_socket_unregister_write

    def on_socket_open(self, client, userdata, sock):
        self.log.debug("Socket opened")

        def cb():
            self.log.debug("Socket is readable, calling loop_read")
            client.loop_read()
        self.log.debug("add_reader:")
        self.loop.add_reader(sock, cb)
        self.log.debug("create helper task:")
        # self.misc = self.loop.create_task(self.misc_loop())
        self.misc = asyncio.create_task(self.misc_loop())

    def on_socket_close(self, client, userdata, sock):
        self.log.debug("Socket closed")
        self.loop.remove_reader(sock)
        self.misc.cancel()

    def on_socket_register_write(self, client, userdata, sock):
        self.log.debug("Watching socket for writability.")

        def cb():
            self.log.debug("Socket is writable, calling loop_write")
            client.loop_write()

        self.loop.add_writer(sock, cb)

    def on_socket_unregister_write(self, client, userdata, sock):
        self.log.debug("Stop watching socket for writability.")
        self.loop.remove_writer(sock)

    async def misc_loop(self):
        self.log.debug("misc_loop started")
        state=True
        while state is True: 
            if self.client.loop_misc() != mqtt.MQTT_ERR_SUCCESS:
                state=False
            if self.client.loop_read() != mqtt.MQTT_ERR_SUCCESS:
                state=False
            if self.client.loop_write() != mqtt.MQTT_ERR_SUCCESS:
                state=False
            try:
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                self.log.debug("Misc_loop cancelled")
                break
        self.log.debug("misc_loop finished")


class AsyncMqtt:
    '''Async wrapper for paho_mqtt'''
    def __init__(self, loop, mqtt_server, last_will_topic=None, last_will_message=None, reconnect_delay=1):
        self.log = logging.getLogger("AsyncMqtt")
        self.loop = loop
        self.mqtt_server = mqtt_server
        self.reconnect_delay=reconnect_delay
        self.initial_connect_maxtime=30

        self.got_message = None

        self.client_id = hex(uuid.getnode()) + "-" + str(uuid.uuid4())
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        self.aioh = AsyncMqttHelper(self.log, self.loop, self.client)

        if last_will_topic is not None:
            if last_will_message is None:
                last_will_message=""
            self.client.will_set(last_will_topic, last_will_message, 0, True)

        connect_start=time.time()
        connected=False
        while connected is False:
            connected=self.connect()
            if connected is False:
                if time.time()-connect_start<self.initial_connect_maxtime:
                    self.log.debug("Trying to connect again...")
                    time.sleep(2)
                else:
                    break
        if connected is False:
            self.log.error("Initial connection to MQTT failed, stopping retries.")


    def connect(self):
        self.active_disconnect=False
        try:
            self.client.connect(self.mqtt_server, 1883, 45)
            self.client.socket().setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)
            self.log.debug("mqtt socket connected.")
            return True
        except Exception as e:
            self.log.debug(f"Connection to {self.mqtt_server} failed: {e}")
            return False

    async def reconnect(self):
        is_connected=False
        while is_connected==False:
            await asyncio.sleep(self.reconnect_delay)
            is_connected=self.connect()

    def on_connect(self, client, userdata, flags, rc):
        self.disconnected = self.loop.create_future()
        self.log.debug("on_connect")

    def subscribe(self, topic):
        self.client.subscribe(topic)

    def publish(self, topic, payload,  retain=False, qos=0):
        self.log.debug(f"PUB: topic: [{topic}] payload: [{payload}]")
        self.client.publish(topic, payload, retain=retain, qos=qos)

    def on_message(self, client, userdata, msg):
        self.log.debug(f"Received: {msg.topic} - {msg.payload}")
        if not self.got_message:
            self.log.debug(f"Got unexpected message: {msg.decode()}")
        else:
            self.got_message.set_result((msg.topic, msg.payload))

    async def message(self):
            self.got_message = self.loop.create_future()
            topic, payload = await self.got_message
            self.got_message = None
            return topic, payload

    def on_disconnect(self, client, userdata, rc):
        self.log.debug("on_disconnect")
        self.disconnected.set_result(rc)
        if self.active_disconnect is not True and self.reconnect_delay and self.reconnect_delay>0:
            self.log.debug("Trying to reconnect...")
            asyncio.create_task(self.reconnect())

    async def disconnect(self):
        self.active_disconnect=True
        self.client.disconnect()
        self.log.debug(f"Disconnected: {await self.disconnected}")
        self.active_disconnect=False


class AsyncHABinarySensorPresence():
    def __init__(self, loop, mqtt_host, name=None, homeassistant_discovery=True, homeassistant_discovery_prefix='homeassistant'):  
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

        self.mqtt_host=mqtt_host
        self.homeassistant_discovery=homeassistant_discovery
        self.homeassistant_discovery_prefix=homeassistant_discovery_prefix

        self.state_topic=f"{name}/presence/state"
        if homeassistant_discovery is True:
            discovery_topic=f"{homeassistant_discovery_prefix}/binary_sensor/presence-{name}/config"
            # avail_topic=f"{name}/presence/available"
            discovery_payload=json.dumps({
                "name": name,
                "unique_id": self.uuid,
                "device_class": "presence",
                "payload_off": "off",
                "payload_on": "on",
                "state_topic": self.state_topic
                # "availablility_topic": avail_topic,
            })

        self.mqtt = AsyncMqtt(loop, mqtt_host, last_will_topic=self.state_topic, last_will_message="off")

        if homeassistant_discovery is True:
            self.mqtt.publish(discovery_topic, discovery_payload, retain=True)

    def set_state(self, state):
        if state is True:
            self.log.debug('Publishing `on` state.')
            self.mqtt.publish(self.state_topic, "on", retain=True)
        else:
            self.log.debug('Publishing `off` state.')
            self.mqtt.publish(self.state_topic, "off", retain=True)
