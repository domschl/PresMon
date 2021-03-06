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
    def __init__(self, loop, mqtt_server, reconnect_delay=1):
        self.log = logging.getLogger("AsyncMqtt")
        self.loop = loop
        self.mqtt_server = mqtt_server
        self.reconnect_delay=reconnect_delay

        self.got_message = None

        self.client_id = hex(uuid.getnode()) + "-" + str(uuid.uuid4())
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        self.aioh = AsyncMqttHelper(self.log, self.loop, self.client)

    def last_will(self, last_will_topic, last_will_message, qos=0, retain=True):
            self.client.will_set(last_will_topic, last_will_message, qos, retain)

    async def initial_connect(self, max_wait=30):
        connect_start=time.time()
        connected=False
        while connected is False:
            connected=self.connect()
            if connected is False:
                if time.time()-connect_start<max_wait:
                    self.log.debug("Trying to connect again...")
                    await asyncio.sleep(2)
                else:
                    break
        if connected is False:
            self.log.error("Initial connection to MQTT failed, stopping retries.")
        return connected

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
