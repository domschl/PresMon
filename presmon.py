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
import ruamel.yaml   # pip install ruamel.yaml, preserves comments!
import re
import uuid


async def main_runner(config, args):
    loop = asyncio.get_running_loop()
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
        tasks+=[asyncio.create_task(ass.get_command())]
        
    if input_config['active'] is True:
        from async_input import AsyncInputPresence
        timeout=input_config['timeout']
        if 'Darwin' in platform.platform():
            mouse_active=False
        else:
            mouse_active=input_config['mouse']
        te=AsyncInputPresence(input_config['keyboard'], mouse_active, input_config['hotkeys'], timeout=timeout)
        tasks+=[asyncio.create_task(te.presence())]
    else:
        te=None
    if btle_config['active'] is True:
        from async_ble import AsyncBLEPresence
        ble=AsyncBLEPresence(timeout=10)
        tasks+=[asyncio.create_task(ble.discover())]
    else:
        ble=None
    if mqtt_config['active'] is True:
        from async_mqtt import AsyncMqtt
        mqtt = AsyncMqtt(loop, mqtt_config['broker'])
        if ha_config['active'] is True:
            from async_homeassistant import AsyncHABinarySensor
            hamq=AsyncHABinarySensor(loop, mqtt, "presence", ha_config['entity_name'], ha_config['UUID'], ha_config['discovery_prefix'])
            hotkeys=input_config['hotkeys']
            hakeys={}
            if hotkeys is not None:
                for hotkey in hotkeys:
                    key_name=hotkey
                    try:
                        key_type=hotkeys[hotkey]
                    except:
                        log.error("A hotkey must have either type 'button' or 'flipflop'")
                        key_type='button'
                    if key_type not in ['button', 'flipflop']:
                        log.error("A hotkey must have either type 'button' or 'flipflop'")
                        key_type='button'
                    cname=""
                    val_name=re.compile(r"[A-Za-z0-9_-]")
                    for c in key_name:
                        if val_name.match(c) is None:
                            cname+="_"
                        else:
                            cname+=c
                    key_name=cname
                    hakeys[hotkey]=AsyncHABinarySensor(loop, mqtt, key_type, key_name, ha_config['UUID'], ha_config['discovery_prefix'])
            mqtt.last_will(hamq.last_will_topic, hamq.last_will_message)
        await mqtt.initial_connect()  # Needs to happen after last_will is set.
        if ha_config['active'] is True:
            hamq.register_auto_discovery()
            if hotkeys is not None:
                for hotkey in hotkeys:
                    hakeys[hotkey].register_auto_discovery()
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
                notdone=notdone.union((asyncio.create_task(te.presence()),))
                if res['state']:
                    log.debug("Presence state: present!")
                    hamq.set_state(True)
                else:
                    log.debug("Presence state: absent!")
                    hamq.set_state(False)
            if res['cmd']=='hotkey':
                notdone=notdone.union((asyncio.create_task(te.presence()),))
                if res['state'] is True:
                    log.debug(f"Hot: {res['hotkey']} ON")
                    hakeys[res['hotkey']].set_state(True)
                else:
                    log.debug(f"Hot: {res['hotkey']} OFF")
                    hakeys[res['hotkey']].set_state(False)
            if res['cmd']=='ble':
                devs=res['devs']
                for dev in devs:
                    print(f"{dev} - {devs[dev]}")
                print()
                # log.debug(f"BLE: {len(res['devs'])}")
                notdone=notdone.union((asyncio.create_task(ble.discover()),))
            if res['cmd']=='quit':
                log.warning('Received quit command.')
                esc=True

def read_config_arguments():
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)

    parser = argparse.ArgumentParser()
    parser.add_argument('-k', action='store_true', dest='kill_daemon', help='Kill existing instance and terminate.')
    parser.add_argument('-f', action='store_true', dest='obsolete option', help='Does nothing anymore, since replacing existing daemons is now automatic.')
    args = parser.parse_args()

    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s %(message)s', level=logging.DEBUG, filename='presmon.log', filemode='w')

    yaml=ruamel.yaml.YAML()
    yaml_file='presmon.yaml'
    try:
        with open(yaml_file,'r') as f:
            config=yaml.load(f)
    except Exception as e:
        logging.warning(f"Couldn't read {yaml_file}, {e}")
        print(f"Start failed, invalid YAML config file {yaml_file}: {e}")
        exit(0)
    if 'homeassistant' in config:
        if 'UUID' not in config['homeassistant'] or config['homeassistant']['UUID']==None or len(config['homeassistant']['UUID'])<4:
            print("one-time UUID generation...")
            nd=hex(uuid.getnode())[2:]
            mac_address=f"{nd[0:2]}:{nd[2:4]}:{nd[4:6]}:{nd[6:8]}:{nd[8:10]}:{nd[10:12]}"
            config['homeassistant']['UUID']=mac_address
            try:
                with open(yaml_file,'w') as f:
                    yaml.dump(config, f)
            except:
                print("Updating config UUID failed, may cause duplicate HA devices!")
    return config, args
    
config, args = read_config_arguments()
esc=False
try:
    asyncio.run(main_runner(config, args), debug=True)
except KeyboardInterrupt:
    esc=True

