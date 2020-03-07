#!/usr/bin/env python3

import json
import time
import os
import sys
import psutil
import platform
import logging
import socket
import errno
import signal 
import atexit
import argparse
import asyncio


async def run(loop, config):
    log=logging.getLogger("runLoop")
    tasks=[]
    if config.get('input', True):
        timeout=config.get('input_timeout',180)
        if 'Darwin' in platform.platform():
            mouse_default=False
        else:
            mouse_default=True
        te=AsyncInputPresence(config.get('keyboard', True), config.get('mouse', mouse_default), timeout=timeout)
        tasks+=[te.presence()]
    else:
        te=None
    if config.get('ble', False):
        ble=AsyncBLEPresence(timeout=10)
        tasks+=[ble.discover()]
    else:
        ble=None
    if config.get('ha_mqtt', False):
        hamq=AsyncHABinarySensorPresence(loop, config['mqtt_server'],config['ha_presence_devname'])
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
            if res['cmd']=='ble':
                devs=res['devs']
                for dev in devs:
                    print(f"{dev} - {devs[dev]}")
                print()
                # log.debug(f"BLE: {len(res['devs'])}")
                notdone=notdone.union((ble.discover(),))

sock=None
SOCKET_ADDRESS='./presmon.lock'

def close_socket():
    global sock
    global SOCKET_ADDRESS
    sock.close()
    os.unlink(SOCKET_ADDRESS)

def signal_handler(sig, frame):
    sys.exit(0)  # this will implicitly call close_socket()

def check_register_socket(address):
    global sock 
    sock = socket.socket(family=socket.AF_UNIX)
    try:
        sock.bind(address)
    except socket.error as e:
        if getattr(e, 'errno', None) == errno.EADDRINUSE:
            return False
        raise
    atexit.register(close_socket)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    return True

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

parser = argparse.ArgumentParser()
parser.add_argument('-q', action='store_true', dest='quiet', help='Check for existing instance without error output.')
args = parser.parse_args()

if check_register_socket(SOCKET_ADDRESS) is False:
    if args.quiet is False:
        print('PresMon is already running, exiting...')
    sys.exit(-1)

logging.basicConfig(
       format='%(asctime)s %(levelname)s %(name)s %(message)s', level=logging.DEBUG, filename='presmon.log', filemode='w')


config_file='presmon.json'
try:
    with open(config_file,'r') as f:
        config=json.load(f)
except Exception as e:
    logging.warning(f"Couldn't read {config_file}, {e}")
if config.get('input', False):
    from async_input import AsyncInputPresence
if config.get('ble', False):
    from async_ble import AsyncBLEPresence
if config.get('ha_mqtt', False):
    from async_ha_mqtt import AsyncHABinarySensorPresence

esc=False
try:
    asyncio.run(run(asyncio.get_event_loop(), config), debug=True)
except KeyboardInterrupt:
    esc=True
