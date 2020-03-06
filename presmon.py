import json
import time
import logging
import asyncio


async def run(loop, config):
    log=logging.getLogger("runLoop")
    tasks=[]
    if config.get('keyboard', False):
        timeout=config.get('keyboard_timeout',180)
        te=AsyncKeyboardPresence(timeout=timeout)
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
                    if dev=='8c:dc:d0:37:1a':
                        name=devs[dev].get('Complete Local Name', 'None')
                        rssi=devs[dev].get('rssi', -999.0)
                        print(f"{dev} - {rssi} - {name} - {devs[dev]}")
                    else:
                        print(dev)
                print()
                # log.debug(f"BLE: {len(res['devs'])}")
                notdone=notdone.union((ble.discover(),))

logging.basicConfig(
       format='%(asctime)s %(levelname)s %(name)s %(message)s', level=logging.DEBUG)
config_file='presmon.json'
try:
    with open(config_file,'r') as f:
        config=json.load(f)
except Exception as e:
    logging.warning(f"Couldn't read {config_file}, {e}")
if config.get('keyboard', False):
    from async_keyboard import AsyncKeyboardPresence
if config.get('ble', False):
    from async_ble import AsyncBLEPresence
if config.get('ha_mqtt', False):
    from async_ha_mqtt import AsyncHABinarySensorPresence

esc=False
try:
    asyncio.run(run(asyncio.get_event_loop(), config), debug=True)
except KeyboardInterrupt:
    esc=True
