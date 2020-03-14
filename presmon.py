#!/usr/bin/env python3

import json
import time
import os
import sys
import platform
import logging
import socket
import errno
import signal 
import atexit
import argparse
import asyncio
import yaml


async def run(loop, config, args):
    log=logging.getLogger("runLoop")
    tasks=[]
    try:
        input_config=config['input']
    except:
        input_config={'active': False}
    try:
        btle_config=config['bluetooth_le']
    except:
        btle_config={'active': False}
    try:
        mqtt_config=config['mqtt']
    except:
        mqtt_config={'active': False}
    try:
        ha_config=config['homeassistant']
    except:
        ha_config={'active': False}
    try:
        server_config=config['server']
    except:
        server_config={'active': False}

    if server_config['active'] is True:
        from async_server import AsyncSignalServer
        ass=AsyncSignalServer(loop, config, args)
        await ass.check_register_socket()
        
    if input_config['active'] is True:
        from async_input import AsyncInputPresence
        timeout=input_config['timeout']
        if 'Darwin' in platform.platform():
            mouse_active=False
        else:
            mouse_active=input_config['mouse']
        te=AsyncInputPresence(input_config['keyboard'], mouse_active, input_config['hotkeys'], timeout=timeout)
        tasks+=[te.presence()]
    else:
        te=None
    if btle_config['active'] is True:
        from async_ble import AsyncBLEPresence
        ble=AsyncBLEPresence(timeout=10)
        tasks+=[ble.discover()]
    else:
        ble=None
    if mqtt_config['active'] is True:
        from async_mqtt import AsyncMqtt
        mqtt = AsyncMqtt(loop, mqtt_config['broker'])
        if ha_config['active'] is True:
            from async_homeassistant import AsyncHABinarySensorPresence
            hamq=AsyncHABinarySensorPresence(loop, mqtt, ha_config['presence_name'], True, ha_config['discovery_prefix'])
            mqtt.last_will(hamq.last_will_topic, hamq.last_will_message)
        await mqtt.initial_connect()  # Needs to happen after last_will is set.
        if ha_config['active'] is True:
            hamq.register_auto_discovery()
    else:
        hamq=None

    global esc
    esc=False

    notdone=tasks
    while esc is False:
        done, notdone = await asyncio.wait(notdone,return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            res=task.result()
            if res['cmd']=='presence':
                notdone=notdone.union((te.presence(),))
                if res['state']:
                    log.debug("Present!")
                    hamq.set_state(True)
                else:
                    log.debug("Absent!")
                    hamq.set_state(False)
            if res['cmd']=='hotkey':
                notdone=notdone.union((te.presence(),))
                log.debug(f"Hot: {res['hotkey']}")
            if res['cmd']=='ble':
                devs=res['devs']
                for dev in devs:
                    print(f"{dev} - {devs[dev]}")
                print()
                # log.debug(f"BLE: {len(res['devs'])}")
                notdone=notdone.union((ble.discover(),))

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

parser = argparse.ArgumentParser()
parser.add_argument('-k', action='store_true', dest='kill_daemon', help='Kill existing instance and terminate.')
parser.add_argument('-f', action='store_true', dest='obsolete option', help='Does nothing anymore, since replacing existing daemons is now automatic.')
args = parser.parse_args()

logging.basicConfig(
       format='%(asctime)s %(levelname)s %(name)s %(message)s', level=logging.DEBUG, filename='presmon.log', filemode='w')

config_file='presmon.json'
yaml_file='presmon.yaml'
try:
    with open(yaml_file,'r') as f:
        config=yaml.load(f, Loader=yaml.SafeLoader)
except Exception as e:
    logging.warning(f"Couldn't read {config_file}, {e}")
    print(f"Start failed, invalid YAML config file {e}")
    exit(0)



esc=False
try:
    asyncio.run(run(asyncio.get_event_loop(), config, args), debug=True)
except KeyboardInterrupt:
    esc=True
